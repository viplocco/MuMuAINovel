"""物品管理API路由"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json

from app.database import get_db
from app.api.common import verify_project_access
from app.services.item_service import item_service
from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
    ItemResponse,
    ItemListResponse,
    ItemStatsResponse,
    ItemTransferCreate,
    ItemTransferResponse,
    ItemQuantityChangeCreate,
    ItemQuantityChangeResponse,
    ItemStatusChangeResponse,
    ItemCategoryCreate,
    ItemCategoryUpdate,
    ItemCategoryResponse,
    ItemHistoryResponse,
    ItemContextRequest,
    ItemContextResponse,
    ItemSyncFromAnalysisRequest,
    ItemSyncFromAnalysisResponse,
)
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/items", tags=["items"])


# ==================== 物品 CRUD ====================

@router.get("/projects/{project_id}", response_model=ItemListResponse)
async def get_project_items(
    project_id: str,
    request: Request,
    status: Optional[str] = Query(None, description="状态筛选"),
    category_id: Optional[str] = Query(None, description="分类ID筛选"),
    owner_id: Optional[str] = Query(None, description="持有者ID筛选"),
    rarity: Optional[str] = Query(None, description="稀有度筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    is_plot_critical: Optional[bool] = Query(None, description="是否剧情关键物品"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """获取项目物品列表"""
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(project_id, user_id, db)

        result = await item_service.get_project_items(
            db=db,
            project_id=project_id,
            status=status,
            category_id=category_id,
            owner_id=owner_id,
            rarity=rarity,
            search=search,
            is_plot_critical=is_plot_critical,
            page=page,
            limit=limit
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取物品列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取物品列表失败: {str(e)}")


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取单个物品详情"""
    try:
        item = await item_service.get_item_by_id(db, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(item.project_id, user_id, db)

        return item.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取物品失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取物品失败: {str(e)}")


@router.post("", response_model=ItemResponse)
async def create_item(
    data: ItemCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建物品"""
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(data.project_id, user_id, db)

        item = await item_service.create_item(db, data)
        return item.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建物品失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建物品失败: {str(e)}")


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    data: ItemUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """更新物品"""
    try:
        # 🔍 调试：打印收到的数据
        logger.info(f"📥 收到更新请求: item_id={item_id}")
        logger.info(f"📥 Pydantic 解析后的 data: {data}")
        logger.info(f"📥 data.category_id: {data.category_id}")

        item = await item_service.get_item_by_id(db, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(item.project_id, user_id, db)

        updated_item = await item_service.update_item(db, item_id, data)
        return updated_item.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新物品失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新物品失败: {str(e)}")


@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """删除物品"""
    try:
        item = await item_service.get_item_by_id(db, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(item.project_id, user_id, db)

        success = await item_service.delete_item(db, item_id)

        return {"success": success, "message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除物品失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除物品失败: {str(e)}")


# ==================== 物品流转 ====================

@router.post("/{item_id}/transfer", response_model=ItemTransferResponse)
async def transfer_item(
    item_id: str,
    data: ItemTransferCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """物品流转（转让持有权）"""
    try:
        item = await item_service.get_item_by_id(db, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(item.project_id, user_id, db)

        result = await item_service.transfer_item(db, item_id, data)
        return result["transfer"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 物品流转失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"物品流转失败: {str(e)}")


# ==================== 数量变更 ====================

@router.post("/{item_id}/quantity", response_model=ItemQuantityChangeResponse)
async def change_item_quantity(
    item_id: str,
    data: ItemQuantityChangeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """变更物品数量"""
    try:
        item = await item_service.get_item_by_id(db, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(item.project_id, user_id, db)

        result = await item_service.change_quantity(db, item_id, data)
        return result["change"]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 数量变更失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数量变更失败: {str(e)}")


# ==================== 物品历史 ====================

@router.get("/{item_id}/history", response_model=ItemHistoryResponse)
async def get_item_history(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取物品完整历史（流转、状态变更、数量变更）"""
    try:
        item = await item_service.get_item_by_id(db, item_id)
        if not item:
            raise HTTPException(status_code=404, detail="物品不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(item.project_id, user_id, db)

        history = await item_service.get_item_history(db, item_id)
        return history

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取物品历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取物品历史失败: {str(e)}")


# ==================== 分类管理 ====================

@router.get("/categories/{project_id}", response_model=List[ItemCategoryResponse])
async def get_category_tree(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取项目分类树"""
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(project_id, user_id, db)

        # 获取项目题材用于初始化合适的分类
        from app.models.project import Project
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()
        project_genre = project.genre if project else None

        categories = await item_service.get_category_tree(db, project_id, project_genre)
        return categories

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取分类树失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取分类树失败: {str(e)}")


@router.post("/categories", response_model=ItemCategoryResponse)
async def create_category(
    data: ItemCategoryCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """创建分类"""
    try:
        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(data.project_id, user_id, db)

        category = await item_service.create_category(db, data)
        return category.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建分类失败: {str(e)}")


@router.put("/categories/{category_id}", response_model=ItemCategoryResponse)
async def update_category(
    category_id: str,
    data: ItemCategoryUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """更新分类"""
    try:
        category = await item_service.update_category(db, category_id, data)
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

        return category.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新分类失败: {str(e)}")


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """删除分类（子分类自动移到父分类下）"""
    try:
        success = await item_service.delete_category(db, category_id)
        if not success:
            raise HTTPException(status_code=404, detail="分类不存在")

        return {"success": True, "message": "删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除分类失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除分类失败: {str(e)}")


# ==================== AI分析集成 ====================

@router.post("/sync-from-analysis", response_model=ItemSyncFromAnalysisResponse)
async def sync_items_from_analysis(
    data: ItemSyncFromAnalysisRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """从AI分析结果同步物品"""
    try:
        # 获取章节所属项目
        from app.models.chapter import Chapter
        from sqlalchemy import select

        chapter_query = select(Chapter).where(Chapter.id == data.chapter_id)
        result = await db.execute(chapter_query)
        chapter = result.scalar_one_or_none()

        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(chapter.project_id, user_id, db)

        sync_result = await item_service.sync_from_analysis(
            db=db,
            project_id=chapter.project_id,
            chapter_id=data.chapter_id,
            chapter_number=data.chapter_number,
            analysis_items=data.items,
            existing_items=data.existing_items
        )

        return sync_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 同步物品失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"同步物品失败: {str(e)}")


# ==================== 章节上下文 ====================

@router.post("/context", response_model=ItemContextResponse)
async def get_chapter_item_context(
    data: ItemContextRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """获取章节生成的物品上下文"""
    try:
        # 需要项目ID，从请求体或参数获取
        # 这里简化处理，实际可能需要调整
        context_text = await item_service.build_chapter_context(
            db=db,
            project_id="",  # 需要传入
            chapter_number=data.chapter_number,
            character_names=None,  # 需要转换character_ids为names
            max_items=data.max_items
        )

        return {
            "chapter_number": data.chapter_number,
            "context_text": context_text,
            "items_count": 0,
            "owned_items": [],
            "plot_critical_items": [],
            "recent_changes": []
        }

    except Exception as e:
        logger.error(f"❌ 获取物品上下文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取物品上下文失败: {str(e)}")


# ==================== 物品分析 ====================


class ItemAnalyzeRequest(BaseModel):
    """物品分析请求"""
    chapter_id: str = Field(..., description="章节ID")
    analysis_requirements: Optional[str] = Field(None, description="分析要求/重点")


class ItemAnalyzeResponse(BaseModel):
    """物品分析响应"""
    chapter_id: str
    chapter_number: int
    chapter_title: str
    analysis_result: Dict[str, Any]
    sync_result: Optional[Dict[str, Any]] = None
    created_items: List[Dict[str, Any]] = []
    updated_items: List[Dict[str, Any]] = []


@router.post("/analyze", response_model=ItemAnalyzeResponse)
async def analyze_chapter_items(
    data: ItemAnalyzeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    分析指定章节中的物品信息

    该API会对指定章节进行物品分析，识别物品的出现、流转和状态变化，
    并自动同步到物品数据库中。
    """
    try:
        from app.services.prompt_service import PromptService
        from app.models.chapter import Chapter
        from app.models.settings import Settings
        from app.services.ai_service import AIService
        from app.models.mcp_plugin import MCPPlugin

        user_id = getattr(request.state, 'user_id', None)

        # 1. 获取章节信息
        chapter_result = await db.execute(
            select(Chapter).where(Chapter.id == data.chapter_id)
        )
        chapter = chapter_result.scalar_one_or_none()

        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        if not chapter.content:
            raise HTTPException(status_code=400, detail="章节内容为空，无法分析")

        # 验证项目访问权限
        await verify_project_access(chapter.project_id, user_id, db)

        # 2. 获取用户的AI服务配置
        settings_result = await db.execute(
            select(Settings).where(Settings.user_id == user_id)
        )
        user_settings = settings_result.scalar_one_or_none()

        if not user_settings:
            # 使用默认配置
            from app.config import settings as app_settings
            api_provider = app_settings.default_ai_provider
            api_key = app_settings.openai_api_key
            api_base_url = app_settings.openai_base_url
            model_name = app_settings.default_model
            temperature = app_settings.default_temperature
            max_tokens = app_settings.default_max_tokens
        else:
            api_provider = user_settings.api_provider
            api_key = user_settings.api_key
            api_base_url = user_settings.api_base_url
            model_name = user_settings.llm_model
            temperature = user_settings.temperature
            max_tokens = user_settings.max_tokens

        # 检查MCP插件状态
        mcp_result = await db.execute(
            select(MCPPlugin).where(MCPPlugin.user_id == user_id)
        )
        mcp_plugins = mcp_result.scalars().all()
        enable_mcp = any(plugin.enabled for plugin in mcp_plugins) if mcp_plugins else False

        # 创建AI服务
        ai_service = AIService(
            api_provider=api_provider,
            api_key=api_key,
            api_base_url=api_base_url or "",
            default_model=model_name,
            default_temperature=temperature,
            default_max_tokens=max_tokens,
            user_id=user_id,
            db_session=db,
            enable_mcp=enable_mcp
        )

        # 3. 获取已有物品列表（用于匹配）
        existing_items = await item_service._get_existing_items_for_matching(db, chapter.project_id)

        # 格式化已有物品信息
        existing_items_text = ""
        if existing_items:
            for item in existing_items:
                existing_items_text += f"- ID: {item.get('id')}, 名称: {item.get('name')}"
                if item.get('alias'):
                    existing_items_text += f", 别名: {','.join(item.get('alias', []))}"
                if item.get('owner_character_name'):
                    existing_items_text += f", 持有者: {item.get('owner_character_name')}"
                existing_items_text += f", 状态: {item.get('status')}\n"
        else:
            existing_items_text = "（暂无已有物品）"

        # 4. 获取项目信息（用于分类初始化时确定题材）
        from app.models.project import Project
        project_result = await db.execute(
            select(Project).where(Project.id == chapter.project_id)
        )
        project = project_result.scalar_one_or_none()
        project_genre = project.genre if project else None

        # 5. 获取分类信息（使用 get_category_tree 确保自动初始化分类）
        categories_tree = await item_service.get_category_tree(db, chapter.project_id, project_genre)

        # 扁平化分类树，提取所有分类名称
        def flatten_categories(tree, result=None):
            if result is None:
                result = []
            for cat in tree:
                result.append(cat)
                if cat.get('children'):
                    flatten_categories(cat.get('children', []), result)
            return result

        all_categories = flatten_categories(categories_tree)

        categories_text = ""
        if all_categories:
            for cat in all_categories:
                categories_text += f"- {cat.get('name', '')}"
                if cat.get('parent_id'):
                    categories_text += f"（子分类）"
                categories_text += "\n"
        else:
            categories_text = "（暂无分类）"

        # 6. 构建分析提示词
        analysis_requirements = data.analysis_requirements or "全面分析本章节中的所有物品相关信息"

        # 限制内容长度以加快响应
        content_limit = 6000  # 减少到6000字符以加快AI响应
        chapter_content = chapter.content[:content_limit]
        if len(chapter.content) > content_limit:
            chapter_content += "\n...[内容已截断]..."

        prompt = PromptService.ITEM_ANALYSIS.format(
            chapter_number=chapter.chapter_number,
            title=chapter.title or f"第{chapter.chapter_number}章",
            content=chapter_content,
            existing_items=existing_items_text[:2000] if existing_items_text else "（暂无已有物品）",  # 限制已有物品文本
            analysis_requirements=analysis_requirements,
            categories_info=categories_text[:1000] if categories_text else "（暂无分类）"  # 限制分类文本
        )

        # 7. 执行AI分析
        logger.info(f"🔍 开始分析章节物品: 第{chapter.chapter_number}章")
        logger.info(f"📄 提示词长度: {len(prompt)} 字符")

        try:
            # 增加max_tokens，智谱AI需要较大的输出空间
            analysis_response = await ai_service.generate_text(
                prompt=prompt,
                temperature=0.3,
                max_tokens=8000  # 增加到8000以避免被截断
            )
            logger.info(f"📄 AI响应类型: {type(analysis_response)}")
            logger.info(f"📄 AI响应键: {analysis_response.keys() if isinstance(analysis_response, dict) else 'N/A'}")

            # 检查finish_reason
            finish_reason = analysis_response.get('finish_reason') if isinstance(analysis_response, dict) else None
            if finish_reason:
                logger.info(f"📄 AI finish_reason: {finish_reason}")

        except Exception as ai_error:
            logger.error(f"❌ AI调用失败: {ai_error}")
            raise HTTPException(status_code=500, detail=f"AI调用失败: {str(ai_error)}")

        # 8. 解析分析结果
        analysis_content = analysis_response.get('content', '') if isinstance(analysis_response, dict) else ''

        # 记录原始响应用于调试
        logger.info(f"📄 AI原始响应长度: {len(analysis_content) if analysis_content else 0}")
        if analysis_content:
            logger.info(f"📄 AI原始响应前200字符: {analysis_content[:200]}")
        else:
            # 如果内容为空，记录完整响应
            logger.warning(f"⚠️ AI返回空内容")
            logger.warning(f"📄 完整响应: {analysis_response}")

            # 如果finish_reason是length，尝试增加max_tokens重试
            if finish_reason == 'length':
                logger.warning("⚠️ AI响应被截断，尝试增加max_tokens重试...")
                try:
                    analysis_response = await ai_service.generate_text(
                        prompt=prompt,
                        temperature=0.3,
                        max_tokens=16000  # 再次增加
                    )
                    analysis_content = analysis_response.get('content', '')
                    logger.info(f"📄 重试后响应长度: {len(analysis_content) if analysis_content else 0}")
                except Exception as retry_error:
                    logger.error(f"❌ 重试失败: {retry_error}")

        if not analysis_content or not analysis_content.strip():
            raise HTTPException(
                status_code=500,
                detail="AI返回空响应。可能原因：1. 章节内容过长 2. AI服务繁忙 3. 模型配置问题。请尝试分析其他章节或稍后重试。"
            )

        # 使用统一的JSON清理方法
        from app.services.json_helper import clean_json_response, parse_json

        try:
            # 先清理响应
            cleaned_content = clean_json_response(analysis_content)
            logger.debug(f"📄 清理后内容前200字符: {cleaned_content[:200] if cleaned_content else '空'}")

            # 尝试解析JSON
            analysis_result = parse_json(cleaned_content)

            if analysis_result is None:
                # 如果解析失败，尝试直接解析
                analysis_result = json.loads(cleaned_content)
        except Exception as parse_error:
            logger.error(f"❌ JSON解析失败: {parse_error}")
            logger.error(f"📄 清理后内容: {cleaned_content[:500] if 'cleaned_content' in dir() else analysis_content[:500]}")
            raise HTTPException(status_code=500, detail=f"AI响应格式解析失败: {str(parse_error)}")

        logger.info(f"📋 物品分析完成: 识别到 {len(analysis_result.get('items', []))} 个物品事件")

        # 9. 同步物品到数据库
        sync_result = None
        created_items = []
        updated_items = []

        if analysis_result.get('items'):
            from app.schemas.item import ItemAnalysisResult

            # 转换为Schema格式
            analysis_items = []
            for item_data in analysis_result.get('items', []):
                analysis_items.append(ItemAnalysisResult(
                    item_name=item_data.get('item_name', ''),
                    item_type=item_data.get('item_type'),
                    event_type=item_data.get('event_type', 'appear'),
                    reference_item_id=item_data.get('reference_item_id'),
                    from_character=item_data.get('from_character'),
                    to_character=item_data.get('to_character'),
                    quantity_change=item_data.get('quantity_change'),
                    quantity_after=item_data.get('quantity_after'),
                    description=item_data.get('description'),
                    keyword=item_data.get('keyword'),
                    rarity=item_data.get('rarity'),
                    special_effects=item_data.get('special_effects'),
                    quality=item_data.get('quality'),
                    lore=item_data.get('lore'),
                    value=item_data.get('value'),
                    aliases=item_data.get('aliases'),
                    attributes=item_data.get('attributes'),
                    is_plot_critical=item_data.get('is_plot_critical'),
                    unit=item_data.get('unit'),
                    suggested_category=item_data.get('suggested_category')
                ))

            # 执行同步
            sync_result = await item_service.sync_from_analysis(
                db=db,
                project_id=chapter.project_id,
                chapter_id=data.chapter_id,
                chapter_number=chapter.chapter_number,
                analysis_items=analysis_items,
                existing_items=existing_items
            )

            # 提取创建和更新的物品，确保转换为字典
            for item in sync_result.get('new_items', []):
                if hasattr(item, 'to_dict'):
                    created_items.append(item.to_dict())
                elif isinstance(item, dict):
                    created_items.append(item)
                else:
                    # 尝试转换为字典
                    try:
                        created_items.append(dict(item))
                    except:
                        logger.warning(f"无法转换物品为字典: {type(item)}")

            for item in sync_result.get('updated_items', []):
                if hasattr(item, 'to_dict'):
                    updated_items.append(item.to_dict())
                elif isinstance(item, dict):
                    updated_items.append(item)
                else:
                    try:
                        updated_items.append(dict(item))
                    except:
                        logger.warning(f"无法转换物品为字典: {type(item)}")

            logger.info(
                f"✅ 物品同步完成: 新建{sync_result['created_count']}个, "
                f"更新{sync_result['updated_count']}个"
            )

        return {
            "chapter_id": data.chapter_id,
            "chapter_number": chapter.chapter_number,
            "chapter_title": chapter.title or f"第{chapter.chapter_number}章",
            "analysis_result": analysis_result,
            "sync_result": sync_result,
            "created_items": created_items,
            "updated_items": updated_items
        }

    except json.JSONDecodeError as e:
        logger.error(f"❌ 解析AI响应失败: {str(e)}")
        raise HTTPException(status_code=500, detail="AI响应格式解析失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 物品分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"物品分析失败: {str(e)}")


# ==================== 数据清理 ====================

class FixInconsistentItemsResponse(BaseModel):
    """修复不一致物品响应"""
    success: bool = Field(..., description="是否成功")
    fixed_count: int = Field(..., description="修复数量")
    message: str = Field(..., description="消息")


@router.post("/fix-inconsistent", response_model=FixInconsistentItemsResponse)
async def fix_inconsistent_items(
    project_id: Optional[str] = Query(None, description="项目ID，不指定则修复所有项目"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """
    修复不一致的物品数据

    自动修复持有者不为空但状态为'未归属'(appeared)的物品，
    将状态更新为'持有'(owned)。
    """
    try:
        user_id = getattr(request.state, 'user_id', None) if request else None

        # 如果指定了项目ID，验证访问权限
        if project_id:
            await verify_project_access(project_id, user_id, db)

        result = await item_service.fix_inconsistent_items(db, project_id)
        return result

    except Exception as e:
        logger.error(f"❌ 修复不一致物品失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"修复失败: {str(e)}")


# ==================== 章节相关物品 ====================

@router.get("/chapters/{chapter_id}/items")
async def get_chapter_items(
    chapter_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    获取与指定章节相关的所有物品

    包括：
    1. 在本章节首次出现的物品（source_chapter_number）
    2. 在本章节发生流转的物品
    3. 在本章节数量发生变化的物品
    """
    try:
        from app.models.chapter import Chapter

        # 获取章节信息
        chapter_result = await db.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        chapter = chapter_result.scalar_one_or_none()

        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")

        user_id = getattr(request.state, 'user_id', None)
        await verify_project_access(chapter.project_id, user_id, db)

        # 调用服务获取章节相关物品
        result = await item_service.get_items_by_chapter(
            db=db,
            project_id=chapter.project_id,
            chapter_number=chapter.chapter_number
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取章节物品失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取章节物品失败: {str(e)}")