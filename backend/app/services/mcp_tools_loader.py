"""MCP工具加载器 - 统一的工具获取入口

在AI请求之前，自动检查用户MCP配置并加载可用工具。
"""
import traceback
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.models.mcp_plugin import MCPPlugin
from app.mcp import mcp_client

logger = get_logger(__name__)

# 最大缓存条目限制
MAX_CACHE_SIZE = 100


@dataclass
class UserToolsCache:
    """用户工具缓存条目"""
    tools: Optional[List[Dict[str, Any]]]
    expire_time: datetime
    hit_count: int = 0


class MCPToolsLoader:
    """
    MCP工具加载器
    
    负责：
    1. 检查用户是否配置并启用了MCP插件
    2. 从各个启用的插件加载工具列表
    3. 将工具转换为OpenAI Function Calling格式
    4. 缓存结果以提升性能
    """
    
    _instance: Optional['MCPToolsLoader'] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return

        # 用户工具缓存: user_id -> UserToolsCache
        self._cache: Dict[str, UserToolsCache] = {}

        # 缓存TTL（5分钟）
        self._cache_ttl = timedelta(minutes=5)

        # 最大缓存条目限制
        self._max_cache_size = MAX_CACHE_SIZE

        self._initialized = True
        logger.info("✅ MCPToolsLoader 初始化完成")

    def _evict_if_needed(self):
        """清理过期缓存，防止内存无限增长"""
        now = datetime.now()

        # 1. 清理过期条目
        expired_keys = [k for k, v in self._cache.items() if v.expire_time < now]
        for k in expired_keys:
            del self._cache[k]
            logger.debug(f"🧹 清理过期缓存: {k}")

        # 2. 如果还是太多，清理最老的
        if len(self._cache) > self._max_cache_size:
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].expire_time
            )
            evict_count = len(self._cache) - self._max_cache_size
            for k in sorted_keys[:evict_count]:
                del self._cache[k]
                logger.debug(f"🧹 清理最老缓存: {k}")
    
    async def has_enabled_plugins(
        self, 
        user_id: str, 
        db_session: AsyncSession
    ) -> bool:
        """
        检查用户是否有启用的MCP插件
        
        Args:
            user_id: 用户ID
            db_session: 数据库会话
            
        Returns:
            是否有启用的插件
        """
        try:
            query = select(MCPPlugin.id).where(
                MCPPlugin.user_id == user_id,
                MCPPlugin.enabled == True,
                MCPPlugin.plugin_type.in_(["http", "streamable_http", "sse"])
            ).limit(1)
            
            result = await db_session.execute(query)
            return result.scalar() is not None
            
        except Exception as e:
            logger.warning(f"检查用户MCP插件失败: {e}")
            return False
    
    async def get_user_tools(
        self,
        user_id: str,
        db_session: AsyncSession,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取用户的MCP工具列表（OpenAI格式）
        
        Args:
            user_id: 用户ID
            db_session: 数据库会话
            use_cache: 是否使用缓存
            force_refresh: 是否强制刷新
            
        Returns:
            - None: 用户未配置或未启用任何MCP插件
            - []: 有配置但没有可用工具
            - List[Dict]: OpenAI Function Calling格式的工具列表
        """
        now = datetime.now()

        # 清理过期缓存，防止内存无限增长
        self._evict_if_needed()

        # 检查缓存
        if use_cache and not force_refresh and user_id in self._cache:
            cache_entry = self._cache[user_id]
            if now < cache_entry.expire_time:
                cache_entry.hit_count += 1
                logger.debug(f"🎯 用户工具缓存命中: {user_id} (命中次数: {cache_entry.hit_count})")
                return cache_entry.tools
            else:
                del self._cache[user_id]
                logger.debug(f"⏰ 用户工具缓存过期: {user_id}")
        
        # 从数据库加载
        try:
            tools = await self._load_user_tools(user_id, db_session)
            
            # 更新缓存
            self._cache[user_id] = UserToolsCache(
                tools=tools,
                expire_time=now + self._cache_ttl
            )
            
            if tools:
                logger.info(f"🔧 用户 {user_id} 加载了 {len(tools)} 个MCP工具")
            else:
                logger.debug(f"📭 用户 {user_id} 没有可用的MCP工具")
            
            return tools
            
        except Exception as e:
            logger.error(f"❌ 加载用户MCP工具失败: {e}")
            return None
    
    async def _load_user_tools(
        self,
        user_id: str,
        db_session: AsyncSession
    ) -> Optional[List[Dict[str, Any]]]:
        """
        从数据库加载用户启用的MCP插件并获取工具
        """
        # 查询启用的插件
        query = select(MCPPlugin).where(
            MCPPlugin.user_id == user_id,
            MCPPlugin.enabled == True,
            MCPPlugin.plugin_type.in_(["http", "streamable_http", "sse"])
        ).order_by(MCPPlugin.sort_order)
        
        result = await db_session.execute(query)
        plugins = result.scalars().all()
        
        if not plugins:
            return None
        
        all_tools = []
        
        for plugin in plugins:
            try:
                # 确定插件类型
                plugin_type = plugin.plugin_type
                if plugin_type == "http":
                    plugin_type = "streamable_http"  # 默认使用streamable_http
                
                # 确保插件已注册到MCP客户端
                await mcp_client.ensure_registered(
                    user_id=user_id,
                    plugin_name=plugin.plugin_name,
                    url=plugin.server_url,
                    plugin_type=plugin_type,
                    headers=plugin.headers
                )
                
                # 获取工具列表
                plugin_tools = await mcp_client.get_tools(user_id, plugin.plugin_name)
                
                # 转换为OpenAI格式
                formatted = mcp_client.format_tools_for_openai(plugin_tools, plugin.plugin_name)
                all_tools.extend(formatted)
                
                logger.debug(f"✅ 从插件 {plugin.plugin_name} 加载了 {len(formatted)} 个工具")
                
            except Exception as e:
                # 获取详细错误信息
                error_details = traceback.format_exc()
                logger.warning(
                    f"⚠️ 加载插件 {plugin.plugin_name} 工具失败: {type(e).__name__}: {e}\n"
                    f"   插件URL: {plugin.server_url}\n"
                    f"   插件类型: {plugin.plugin_type}\n"
                    f"   堆栈: {error_details[:500] if error_details else '无'}"
                )
                continue
        
        return all_tools if all_tools else None
    
    def invalidate_cache(self, user_id: Optional[str] = None):
        """
        使缓存失效

        Args:
            user_id: 用户ID，为None时清空所有缓存
        """
        # 1. 清理本地缓存 (MCPToolsLoader)
        if user_id:
            if user_id in self._cache:
                del self._cache[user_id]
                logger.debug(f"🧹 清理用户工具缓存(MCPToolsLoader): {user_id}")
        else:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"🧹 清理所有用户工具缓存(MCPToolsLoader) ({count}个)")

        # 2. 同时清理 MCPClientFacade 的工具缓存
        from app.mcp import mcp_client
        try:
            mcp_client.clear_cache(user_id=user_id)
        except Exception as e:
            logger.warning(f"清理MCPClientFacade缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        now = datetime.now()
        return {
            "total_entries": len(self._cache),
            "total_hits": sum(e.hit_count for e in self._cache.values()),
            "cache_ttl_minutes": self._cache_ttl.total_seconds() / 60,
            "entries": [
                {
                    "user_id": uid,
                    "tools_count": len(e.tools) if e.tools else 0,
                    "hit_count": e.hit_count,
                    "expired": now >= e.expire_time,
                    "expire_time": e.expire_time.isoformat()
                }
                for uid, e in self._cache.items()
            ]
        }


# 全局单例
mcp_tools_loader = MCPToolsLoader()