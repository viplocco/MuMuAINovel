"""物品管理服务 - 处理物品的CRUD和业务逻辑"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, delete, update, asc
from sqlalchemy.orm import selectinload
from datetime import datetime
import uuid
import math

from app.database import Base
from app.logger import get_logger

logger = get_logger(__name__)


# ==================== 权重配置常量 ====================

# 持有者重要性权重（与角色 role_type 绑定）
CHARACTER_IMPORTANCE_WEIGHTS = {
    "主角": 1.0,       # 核心角色，物品最关键
    "重要配角": 0.7,   # 常出场，有剧情影响
    "反派": 0.8,       # 与主角对抗，装备值得关注
    "普通配角": 0.4,   # 偶尔出场
    "路人NPC": 0.2,    # 几乎不重要
    "组织势力": 0.5,   # 组织持有的公共物品
    "default": 0.3,    # 无持有者/未知
}

# 物品类别基础权重（物品本身的价值）
ITEM_CATEGORY_WEIGHTS = {
    "武器": 1.0,       # 战斗核心
    "法宝": 1.0,       # 修炼/战斗核心
    "攻击法宝": 1.0,
    "防御法宝": 0.9,
    "辅助法宝": 0.85,
    "神器": 1.0,       # 最高价值
    "装备": 0.9,       # 持续使用
    "剧情物品": 1.0,   # 钥匙、信物、任务物
    "特殊物品": 0.85,
    "丹药": 0.6,       # 消耗类，有使用价值
    "疗伤丹药": 0.65,
    "突破丹药": 0.7,   # 更重要
    "辅助丹药": 0.5,
    "材料": 0.4,       # 库存类
    "货币": 0.3,       # 数量变化意义小
    "典籍": 0.7,       # 可能蕴含秘密
    "符箓": 0.6,
    "灵兽": 0.8,       # 战斗伙伴
    "道具": 0.5,       # 默认道具类
    "default": 0.5,    # 默认权重
}

# 稀有度权重（叠加因子）- 提高权重让稀有度有更大影响
RARITY_WEIGHTS = {
    "artifact": 1.5,   # 神器，权重大幅提升
    "legendary": 1.3,  # 传说
    "epic": 1.2,       # 史诗
    "rare": 1.0,       # 稀有（基准）
    "uncommon": 0.9,   # 优秀
    "common": 0.8,     # 普通
    "default": 1.0,    # 无稀有度
}

# 稀有度保底优先级（稀有度高的物品应该有更高的基础优先级）
RARITY_MIN_PRIORITY = {
    "artifact": 0.60,   # 神器保底提高到 0.60
    "legendary": 0.50,  # 传说保底提高到 0.50
    "epic": 0.40,       # 史诗保底提高到 0.40
    "rare": 0.30,       # 稀有保底提高到 0.30
    "uncommon": 0.20,   # 优秀保底 0.20
    "common": 0.15,     # 普通保底 0.15（出现在剧情中就不应完全忽略）
    "default": 0.15,    # 无稀有度保底 0.15
}

# 物品分类保底优先级（重要分类不应该被完全忽略）
CATEGORY_MIN_PRIORITY = {
    "武器": 0.30,       # 武器保底提高到 0.30
    "法宝": 0.30,       # 法宝保底提高到 0.30
    "神器": 0.40,       # 神器分类保底 0.40
    "攻击法宝": 0.30,
    "防御法宝": 0.25,
    "辅助法宝": 0.20,
    "剧情物品": 0.40,   # 剧情物品保底提高到 0.40
    "特殊物品": 0.25,
    "装备": 0.25,
    "灵兽": 0.30,
    "典籍": 0.20,
    "default": 0.15,    # 默认保底提高到 0.15
}


# ==================== 上下文优先级计算 V2 ====================

def get_character_importance_weight(role_type: Optional[str]) -> float:
    """获取持有者重要性权重"""
    if not role_type:
        return CHARACTER_IMPORTANCE_WEIGHTS["default"]
    return CHARACTER_IMPORTANCE_WEIGHTS.get(role_type, CHARACTER_IMPORTANCE_WEIGHTS["default"])


def get_item_category_weight(category_name: Optional[str], tags: Optional[List[str]] = None) -> float:
    """获取物品类别权重"""
    # 优先使用分类名称匹配
    if category_name:
        # 精确匹配
        if category_name in ITEM_CATEGORY_WEIGHTS:
            return ITEM_CATEGORY_WEIGHTS[category_name]
        # 模糊匹配（包含关键词）
        for key, weight in ITEM_CATEGORY_WEIGHTS.items():
            if key in category_name or category_name in key:
                return weight

    # 从标签推断
    if tags:
        for tag in tags:
            if tag in ITEM_CATEGORY_WEIGHTS:
                return ITEM_CATEGORY_WEIGHTS[tag]
            tag_lower = tag.lower()
            for key, weight in ITEM_CATEGORY_WEIGHTS.items():
                if key.lower() in tag_lower or tag_lower in key.lower():
                    return weight

    return ITEM_CATEGORY_WEIGHTS["default"]


def get_rarity_weight(rarity: Optional[str]) -> float:
    """获取稀有度权重"""
    if not rarity:
        return RARITY_WEIGHTS["default"]
    return RARITY_WEIGHTS.get(rarity, RARITY_WEIGHTS["default"])


def get_rarity_min_priority(rarity: Optional[str]) -> float:
    """获取稀有度保底优先级"""
    if not rarity:
        return RARITY_MIN_PRIORITY["default"]
    return RARITY_MIN_PRIORITY.get(rarity, RARITY_MIN_PRIORITY["default"])


def get_category_min_priority(category_name: Optional[str], tags: Optional[List[str]] = None) -> float:
    """获取分类保底优先级"""
    # 优先使用分类名称匹配
    if category_name:
        if category_name in CATEGORY_MIN_PRIORITY:
            return CATEGORY_MIN_PRIORITY[category_name]
        # 模糊匹配
        for key, min_p in CATEGORY_MIN_PRIORITY.items():
            if key in category_name or category_name in key:
                return min_p

    # 从标签推断
    if tags:
        for tag in tags:
            if tag in CATEGORY_MIN_PRIORITY:
                return CATEGORY_MIN_PRIORITY[tag]

    return CATEGORY_MIN_PRIORITY["default"]


def calculate_context_priority_v2(
    distance: int,
    character_importance: float,
    item_category_weight: float,
    rarity_weight: float,
    mention_count: int = 1,
    is_plot_critical: bool = False,
    status: str = 'appeared',
    rarity_min: float = 0.0,
    category_min: float = 0.0
) -> float:
    """
    计算物品的上下文优先级 V2 - 多维度权重融合

    优先级范围：0.0 - 1.0
    - 1.0: 最高优先级，主角的核心装备且当章提及
    - 0.0: 已完成使命（消耗/销毁），完全排除

    保底机制（按优先级从高到低）：
    1. 剧情关键物品保底: 0.60
    2. 刚提及保底: 当章(distance=0) → 0.50, 近期(distance≤3) → 0.40
    3. 稀有度保底: 神器0.60, 传说0.50, 史诗0.40, 稀有0.30
    4. 分类保底: 神器/剧情物品0.40, 武器/法宝/灵兽0.30
    5. 状态保底: equipped0.30, owned0.25, appeared0.20
    6. 基础保底: 任何物品最低0.15

    Args:
        distance: 距离上次提及的章节数
        character_importance: 持有者重要性权重 (0.0-1.0)
        item_category_weight: 物品类别基础权重 (0.0-1.0)
        rarity_weight: 稀有度权重因子
        rarity_min: 稀有度保底优先级
        category_min: 分类保底优先级
        mention_count: 累计提及次数
        is_plot_critical: 是否剧情关键物品
        status: 物品状态

    Returns:
        计算后的优先级值
    """
    # 状态覆盖：已完成使命的物品直接排除（优先级为0）
    if status in ('consumed', 'destroyed'):
        return 0.0

    # 被封印或丢失的物品，低优先级但保留可能恢复的信息
    if status in ('sealed', 'lost'):
        # 稀有度高的封印物品仍需关注（可能被解封）
        sealed_min = max(0.10, rarity_min * 0.6)
        return sealed_min

    # === 计算实际优先级 ===

    # 基础权重融合（持有者 × 类别 × 稀有度）
    # 注意：稀有度权重现在更高（神器1.5），所以即使持有者不重要，稀有度也能提升优先级
    base_importance = character_importance * item_category_weight * rarity_weight

    # 稀有度加成：高稀有度物品本身就应该重要，不受持有者限制
    # 如果稀有度权重 >= 1.2（史诗及以上），给予额外加成
    if rarity_weight >= 1.5:  # 神器
        rarity_bonus = 0.30
    elif rarity_weight >= 1.3:  # 传说
        rarity_bonus = 0.20
    elif rarity_weight >= 1.2:  # 史诗
        rarity_bonus = 0.10
    else:
        rarity_bonus = 0.0

    # 将稀有度加成加入基础重要性
    base_importance = base_importance + rarity_bonus
    # 限幅到 0.0-1.0
    base_importance = min(1.0, max(0.0, base_importance))

    # 时间衰减（使用更温和的衰减系数）
    decay = math.exp(-0.05 * max(0, distance))

    # 活跃度因子（基于提及次数）
    activity_factor = min(1.0, 0.7 + mention_count * 0.03)

    # 计算优先级
    calculated_priority = base_importance * decay * activity_factor

    # === 多层保底机制 ===

    # 1. 剧情关键物品保底（最高优先级）
    min_priority = 0.60 if is_plot_critical else 0.0

    # 2. 刚提及保底：刚在剧情中出现的物品应该有更高的优先级
    if distance == 0:
        # 当章提及的物品，给予较高保底
        min_priority = max(min_priority, 0.50)
    elif distance <= 3:
        # 近3章内提及，给予中等保底
        min_priority = max(min_priority, 0.40)

    # 3. 稀有度保底（神器/传说不应被忽略）
    min_priority = max(min_priority, rarity_min)

    # 4. 分类保底（武器/法宝等重要分类不应被忽略）
    min_priority = max(min_priority, category_min)

    # 5. 状态保底：根据物品状态设置不同的保底值
    if status == 'equipped':
        state_min = 0.30
    elif status == 'owned':
        state_min = 0.25
    elif status == 'appeared':
        state_min = 0.20
    else:
        state_min = 0.15

    min_priority = max(min_priority, state_min)

    # 6. 被持有的物品额外提升（基于持有者重要性）
    if status in ('owned', 'equipped'):
        min_priority = max(min_priority, base_importance * 0.5)

    # 7. 基础保底：任何物品最低 0.15
    min_priority = max(min_priority, 0.15)

    # 应用保底值（取保底值和计算值的较大者）
    priority = max(min_priority, calculated_priority)

    # 最终限幅
    return min(1.0, max(0.0, priority))


# 保留旧函数作为兼容（内部调用新函数）
def calculate_context_priority(
    last_mentioned_chapter: Optional[int],
    current_chapter: int,
    status: str,
    is_plot_critical: bool
) -> float:
    """
    计算物品的上下文优先级（兼容旧调用）

    已弃用，建议使用 calculate_context_priority_v2
    """
    if last_mentioned_chapter is None:
        distance = 0
    else:
        distance = current_chapter - last_mentioned_chapter

    # 使用默认权重（保守估计）
    return calculate_context_priority_v2(
        distance=distance,
        character_importance=0.5,  # 默认持有者权重
        item_category_weight=0.5,  # 默认类别权重
        rarity_weight=1.0,         # 默认稀有度权重
        rarity_min=0.0,            # 无稀有度保底
        category_min=0.0,          # 无分类保底
        mention_count=0,
        is_plot_critical=is_plot_critical,
        status=status
    )


# 延迟导入模型（避免循环导入）
Item = None
ItemCategory = None
ItemTransfer = None
ItemStatusChange = None
ItemQuantityChange = None
Chapter = None
Character = None
StoryMemory = None


def _ensure_models():
    """确保模型已导入"""
    global Item, ItemCategory, ItemTransfer, ItemStatusChange, ItemQuantityChange, Chapter, Character, StoryMemory
    if Item is None:
        from app.models.item import Item as _Item
        from app.models.item_category import ItemCategory as _ItemCategory
        from app.models.item_transfer import ItemTransfer as _ItemTransfer
        from app.models.item_status_change import ItemStatusChange as _ItemStatusChange
        from app.models.item_quantity_change import ItemQuantityChange as _ItemQuantityChange
        from app.models.chapter import Chapter as _Chapter
        from app.models.character import Character as _Character
        from app.models.memory import StoryMemory as _StoryMemory
        Item = _Item
        ItemCategory = _ItemCategory
        ItemTransfer = _ItemTransfer
        ItemStatusChange = _ItemStatusChange
        ItemQuantityChange = _ItemQuantityChange
        Chapter = _Chapter
        Character = _Character
        StoryMemory = _StoryMemory


# 在模块加载时导入模型
_ensure_models()

# 导入 Schema
from app.schemas.item import (
    ItemCreate, ItemUpdate,
    ItemTransferCreate, ItemQuantityChangeCreate,
    ItemCategoryCreate, ItemCategoryUpdate,
    ItemSyncFromAnalysisRequest, ItemAnalysisResult
)


class ItemService:
    """物品管理服务"""

    # ==================== 物品 CRUD ====================

    async def get_project_items(
        self,
        db: AsyncSession,
        project_id: str,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        rarity: Optional[str] = None,
        search: Optional[str] = None,
        is_plot_critical: Optional[bool] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """获取项目物品列表"""
        try:
            logger.info(f"🔍 开始获取物品列表: project_id={project_id}, page={page}, limit={limit}")

            conditions = [Item.project_id == project_id]

            if status:
                conditions.append(Item.status == status)
            if category_id:
                conditions.append(Item.category_id == category_id)
            if owner_id:
                conditions.append(Item.owner_character_id == owner_id)
            if rarity:
                conditions.append(Item.rarity == rarity)
            if is_plot_critical is not None:
                conditions.append(Item.is_plot_critical == is_plot_critical)
            if search:
                search_pattern = f"%{search}%"
                conditions.append(or_(
                    Item.name.ilike(search_pattern),
                    Item.description.ilike(search_pattern),
                    Item.owner_character_name.ilike(search_pattern)
                ))

            # 查询总数
            count_query = select(func.count(Item.id)).where(and_(*conditions))
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            # 查询列表（关联分类表获取分类名称）
            offset = (page - 1) * limit
            query = (
                select(Item, ItemCategory.name)
                .outerjoin(ItemCategory, Item.category_id == ItemCategory.id)
                .where(and_(*conditions))
                .order_by(desc(Item.updated_at))
                .offset(offset)
                .limit(limit)
            )
            result = await db.execute(query)
            rows = result.all()

            # 组装数据，添加 category_name
            items_with_category = []
            for row in rows:
                item = row[0]
                category_name = row[1]
                item_dict = item.to_dict()
                item_dict['category_name'] = category_name
                # 🔍 日志：显示每个物品的分类情况
                logger.info(f"📦 物品 {item.name}: category_id={item.category_id}, category_name={category_name}")
                items_with_category.append(item_dict)

            # 获取统计
            stats = await self._get_item_stats(db, project_id)

            return {
                "total": total,
                "items": items_with_category,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"获取物品列表失败: {str(e)}")
            raise

    async def _get_item_stats(self, db: AsyncSession, project_id: str) -> Dict[str, Any]:
        """获取物品统计"""
        try:
            # 按状态统计
            status_query = (
                select(Item.status, func.count(Item.id))
                .where(Item.project_id == project_id)
                .group_by(Item.status)
            )
            status_result = await db.execute(status_query)
            by_status = {row[0]: row[1] for row in status_result.all()}

            # 按稀有度统计
            rarity_query = (
                select(Item.rarity, func.count(Item.id))
                .where(Item.project_id == project_id)
                .group_by(Item.rarity)
            )
            rarity_result = await db.execute(rarity_query)
            by_rarity = {row[0]: row[1] for row in rarity_result.all()}

            # 关键物品数量
            critical_query = (
                select(func.count(Item.id))
                .where(and_(
                    Item.project_id == project_id,
                    Item.is_plot_critical == True
                ))
            )
            critical_result = await db.execute(critical_query)
            plot_critical_count = critical_result.scalar() or 0

            # 持有中数量
            owned_query = (
                select(func.count(Item.id))
                .where(and_(
                    Item.project_id == project_id,
                    Item.status == 'owned'
                ))
            )
            owned_result = await db.execute(owned_query)
            owned_count = owned_result.scalar() or 0

            return {
                "total": sum(by_status.values()),
                "by_status": by_status,
                "by_rarity": by_rarity,
                "plot_critical_count": plot_critical_count,
                "owned_count": owned_count
            }
        except Exception as e:
            logger.warning(f"获取物品统计失败: {str(e)}")
            return {}

    async def get_item_by_id(
        self,
        db: AsyncSession,
        item_id: str
    ) -> Optional[Item]:
        """获取单个物品"""
        try:
            query = select(Item).where(Item.id == item_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取物品失败: {str(e)}")
            return None

    async def create_item(
        self,
        db: AsyncSession,
        data: ItemCreate
    ) -> Item:
        """创建物品"""
        try:
            # 获取持有者重要性权重
            character_importance = CHARACTER_IMPORTANCE_WEIGHTS["default"]
            if data.owner_character_name:
                try:
                    char_query = select(Character).where(
                        Character.project_id == data.project_id,
                        Character.name == data.owner_character_name
                    )
                    char_result = await db.execute(char_query)
                    char = char_result.scalar_one_or_none()
                    if char and char.role_type:
                        character_importance = get_character_importance_weight(char.role_type)
                except Exception as e:
                    logger.warning(f"查询持有者角色类型失败: {e}")

            # 获取物品类别权重
            category_name = None
            if data.category_id:
                try:
                    cat_query = select(ItemCategory).where(ItemCategory.id == data.category_id)
                    cat_result = await db.execute(cat_query)
                    cat = cat_result.scalar_one_or_none()
                    if cat:
                        category_name = cat.name
                except Exception as e:
                    logger.warning(f"查询分类名称失败: {e}")

            item_category_weight = get_item_category_weight(category_name, data.tags)

            # 获取稀有度权重和保底
            rarity_str = data.rarity.value if hasattr(data.rarity, 'value') else data.rarity
            rarity_weight = get_rarity_weight(rarity_str)
            rarity_min = get_rarity_min_priority(rarity_str)
            category_min = get_category_min_priority(category_name, data.tags)

            # 获取状态
            status_str = data.status.value if hasattr(data.status, 'value') else data.status

            # 计算初始优先级
            initial_priority = calculate_context_priority_v2(
                distance=0,
                character_importance=character_importance,
                item_category_weight=item_category_weight,
                rarity_weight=rarity_weight,
                rarity_min=rarity_min,
                category_min=category_min,
                mention_count=1,
                is_plot_critical=data.is_plot_critical or False,
                status=status_str
            )

            logger.info(f"📊 创建物品优先级: {data.name} → {initial_priority:.2f} "
                       f"(持有者={character_importance:.1f}, 类别={item_category_weight:.1f}, 稀有度保底={rarity_min:.1f})")

            item = Item(
                id=str(uuid.uuid4()),
                project_id=data.project_id,
                name=data.name,
                alias=data.alias or [],
                category_id=data.category_id,
                description=data.description,
                unit=data.unit,
                quantity=data.quantity,
                initial_quantity=data.initial_quantity or data.quantity,
                max_quantity=data.max_quantity,
                rarity=rarity_str,
                quality=data.quality,
                attributes=data.attributes,
                special_effects=data.special_effects,
                lore=data.lore,
                value=data.value,
                source_type=data.source_type.value if hasattr(data.source_type, 'value') else data.source_type,
                source_chapter_number=data.source_chapter_number,
                status=status_str,
                owner_character_id=data.owner_character_id,
                owner_character_name=data.owner_character_name,
                related_characters=data.related_characters or [],
                related_chapters=data.related_chapters or [],
                tags=data.tags or [],
                notes=data.notes,
                is_plot_critical=data.is_plot_critical or False,
                # 上下文管理字段
                last_mentioned_chapter=data.source_chapter_number,
                mention_count=1,
                context_priority=initial_priority,
                status_changed_at=datetime.now()
            )

            db.add(item)
            await db.commit()
            await db.refresh(item)

            # 更新分类统计
            if item.category_id:
                await self._update_category_count(db, item.category_id)

            logger.info(f"创建物品成功: {item.name}")
            return item
        except Exception as e:
            await db.rollback()
            logger.error(f"创建物品失败: {str(e)}")
            raise

    async def update_item(
        self,
        db: AsyncSession,
        item_id: str,
        data: ItemUpdate
    ) -> Optional[Item]:
        """更新物品"""
        try:
            item = await self.get_item_by_id(db, item_id)
            if not item:
                return None

            old_category_id = item.category_id

            update_data = data.model_dump(exclude_unset=True)

            # 🔍 调试日志
            logger.info(f"📝 更新物品 {item.name}")
            logger.info(f"  - 原分类ID: {old_category_id}")
            logger.info(f"  - 更新数据: {update_data}")

            # 处理枚举值
            if 'rarity' in update_data and hasattr(update_data['rarity'], 'value'):
                update_data['rarity'] = update_data['rarity'].value
            if 'status' in update_data and hasattr(update_data['status'], 'value'):
                update_data['status'] = update_data['status'].value
                update_data['status_changed_at'] = datetime.now()

            for key, value in update_data.items():
                setattr(item, key, value)

            # 重新计算优先级（当状态、稀有度、持有者、分类变更时）
            priority_recalc_fields = {'status', 'rarity', 'owner_character_name', 'category_id', 'tags', 'is_plot_critical'}
            if any(field in update_data for field in priority_recalc_fields):
                # 获取持有者重要性权重
                character_importance = CHARACTER_IMPORTANCE_WEIGHTS["default"]
                if item.owner_character_name:
                    try:
                        char_query = select(Character).where(
                            Character.project_id == item.project_id,
                            Character.name == item.owner_character_name
                        )
                        char_result = await db.execute(char_query)
                        char = char_result.scalar_one_or_none()
                        if char and char.role_type:
                            character_importance = get_character_importance_weight(char.role_type)
                    except Exception as e:
                        logger.warning(f"查询持有者角色类型失败: {e}")

                # 获取物品类别权重
                category_name = None
                if item.category_id:
                    try:
                        cat_query = select(ItemCategory).where(ItemCategory.id == item.category_id)
                        cat_result = await db.execute(cat_query)
                        cat = cat_result.scalar_one_or_none()
                        if cat:
                            category_name = cat.name
                    except Exception as e:
                        logger.warning(f"查询分类名称失败: {e}")

                item_category_weight = get_item_category_weight(category_name, item.tags)
                rarity_weight = get_rarity_weight(item.rarity)
                rarity_min = get_rarity_min_priority(item.rarity)
                category_min = get_category_min_priority(category_name, item.tags)

                new_priority = calculate_context_priority_v2(
                    distance=0,
                    character_importance=character_importance,
                    item_category_weight=item_category_weight,
                    rarity_weight=rarity_weight,
                    rarity_min=rarity_min,
                    category_min=category_min,
                    mention_count=item.mention_count or 1,
                    is_plot_critical=item.is_plot_critical or False,
                    status=item.status
                )
                item.context_priority = new_priority
                logger.info(f"  📊 重新计算优先级: {new_priority:.2f} "
                           f"(持有者={character_importance:.1f}, 类别={item_category_weight:.1f}, 状态={item.status})")

            await db.commit()
            await db.refresh(item)

            # 🔍 调试日志：确认更新后的值
            logger.info(f"更新后物品 {item.name}: category_id={item.category_id}, context_priority={item.context_priority:.2f}")

            # 更新分类统计
            if old_category_id != item.category_id:
                if old_category_id:
                    await self._update_category_count(db, old_category_id)
                if item.category_id:
                    await self._update_category_count(db, item.category_id)

            logger.info(f"更新物品成功: {item.name}")
            return item
        except Exception as e:
            await db.rollback()
            logger.error(f"更新物品失败: {str(e)}")
            raise

    async def delete_item(
        self,
        db: AsyncSession,
        item_id: str
    ) -> bool:
        """删除物品"""
        try:
            item = await self.get_item_by_id(db, item_id)
            if not item:
                return False

            category_id = item.category_id

            await db.delete(item)
            await db.commit()

            # 更新分类统计
            if category_id:
                await self._update_category_count(db, category_id)

            logger.info(f"删除物品成功: {item_id}")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"删除物品失败: {str(e)}")
            raise

    async def _update_category_count(
        self,
        db: AsyncSession,
        category_id: str
    ):
        """更新分类物品数量"""
        try:
            count_query = (
                select(func.count(Item.id))
                .where(Item.category_id == category_id)
            )
            result = await db.execute(count_query)
            count = result.scalar() or 0

            update_query = (
                update(ItemCategory)
                .where(ItemCategory.id == category_id)
                .values(item_count=count)
            )
            await db.execute(update_query)
            await db.commit()
        except Exception as e:
            logger.warning(f"更新分类统计失败: {str(e)}")

    # ==================== 物品流转 ====================

    async def transfer_item(
        self,
        db: AsyncSession,
        item_id: str,
        data: ItemTransferCreate
    ) -> Dict[str, Any]:
        """物品流转"""
        try:
            item = await self.get_item_by_id(db, item_id)
            if not item:
                raise ValueError("物品不存在")

            # 创建流转记录
            transfer = ItemTransfer(
                id=str(uuid.uuid4()),
                project_id=item.project_id,
                item_id=item_id,
                transfer_type=data.transfer_type.value if hasattr(data.transfer_type, 'value') else data.transfer_type,
                from_character_id=data.from_character_id,
                from_character_name=data.from_character_name,
                to_character_id=data.to_character_id,
                to_character_name=data.to_character_name,
                chapter_id=data.chapter_id,
                chapter_number=data.chapter_number,
                location=data.location,
                quantity=data.quantity,
                quantity_after=item.quantity,
                description=data.description,
                reason=data.reason,
                conditions=data.conditions,
                quote_text=data.quote_text,
                source_type='manual'
            )

            # 更新物品持有者
            if data.to_character_id:
                item.owner_character_id = data.to_character_id
                item.owner_character_name = data.to_character_name
                if item.status == 'appeared':
                    item.status = 'owned'
                    item.status_changed_at = datetime.now()

                    # 创建状态变更记录
                    status_change = ItemStatusChange(
                        id=str(uuid.uuid4()),
                        project_id=item.project_id,
                        item_id=item_id,
                        status_before='appeared',
                        status_after='owned',
                        chapter_id=data.chapter_id,
                        chapter_number=data.chapter_number,
                        trigger_event=data.transfer_type,
                        description=data.description,
                        involved_character_id=data.to_character_id,
                        involved_character_name=data.to_character_name,
                        source_type='manual'
                    )
                    db.add(status_change)

            db.add(transfer)
            await db.commit()
            await db.refresh(item)

            logger.info(f"物品流转成功: {item.name} -> {data.to_character_name or '未知'}")
            return {
                "item": item.to_dict(),
                "transfer": transfer.to_dict()
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"物品流转失败: {str(e)}")
            raise

    # ==================== 数量变更 ====================

    async def change_quantity(
        self,
        db: AsyncSession,
        item_id: str,
        data: ItemQuantityChangeCreate
    ) -> Dict[str, Any]:
        """变更物品数量"""
        try:
            item = await self.get_item_by_id(db, item_id)
            if not item:
                raise ValueError("物品不存在")

            quantity_before = item.quantity
            quantity_after = quantity_before + data.quantity_change

            if quantity_after < 0:
                raise ValueError("数量不能为负数")

            # 创建变更记录
            change_record = ItemQuantityChange(
                id=str(uuid.uuid4()),
                project_id=item.project_id,
                item_id=item_id,
                change_type=data.change_type.value if hasattr(data.change_type, 'value') else data.change_type,
                quantity_before=quantity_before,
                quantity_change=data.quantity_change,
                quantity_after=quantity_after,
                chapter_id=data.chapter_id,
                chapter_number=data.chapter_number,
                reason=data.reason,
                description=data.description,
                involved_character_id=data.involved_character_id,
                involved_character_name=data.involved_character_name,
                source_type='manual'
            )

            # 更新物品数量
            item.quantity = quantity_after

            # 如果数量为0，自动更新状态
            if quantity_after == 0 and item.status in ['owned', 'appeared']:
                old_status = item.status
                if data.change_type in ['consume', 'use']:
                    item.status = 'consumed'
                elif data.change_type == 'lose':
                    item.status = 'lost'
                else:
                    item.status = 'destroyed'
                item.status_changed_at = datetime.now()

                # 创建状态变更记录
                status_change = ItemStatusChange(
                    id=str(uuid.uuid4()),
                    project_id=item.project_id,
                    item_id=item_id,
                    status_before=old_status,
                    status_after=item.status,
                    chapter_id=data.chapter_id,
                    chapter_number=data.chapter_number,
                    trigger_event=data.change_type,
                    description=data.description,
                    involved_character_id=data.involved_character_id,
                    involved_character_name=data.involved_character_name,
                    source_type='manual'
                )
                db.add(status_change)

            db.add(change_record)
            await db.commit()
            await db.refresh(item)

            logger.info(f"物品数量变更成功: {item.name} {quantity_before} -> {quantity_after}")
            return {
                "item": item.to_dict(),
                "change": change_record.to_dict()
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"物品数量变更失败: {str(e)}")
            raise

    # ==================== 物品历史 ====================

    async def get_item_history(
        self,
        db: AsyncSession,
        item_id: str
    ) -> Dict[str, Any]:
        """获取物品完整历史"""
        try:
            from app.models.item_attribute_change import ItemAttributeChange

            item = await self.get_item_by_id(db, item_id)
            if not item:
                raise ValueError("物品不存在")

            # 查询流转记录
            transfer_query = (
                select(ItemTransfer)
                .where(ItemTransfer.item_id == item_id)
                .order_by(desc(ItemTransfer.occurred_at))
            )
            transfer_result = await db.execute(transfer_query)
            transfers = transfer_result.scalars().all()

            # 查询状态变更记录
            status_query = (
                select(ItemStatusChange)
                .where(ItemStatusChange.item_id == item_id)
                .order_by(desc(ItemStatusChange.created_at))
            )
            status_result = await db.execute(status_query)
            status_changes = status_result.scalars().all()

            # 查询数量变更记录
            quantity_query = (
                select(ItemQuantityChange)
                .where(ItemQuantityChange.item_id == item_id)
                .order_by(desc(ItemQuantityChange.created_at))
            )
            quantity_result = await db.execute(quantity_query)
            quantity_changes = quantity_result.scalars().all()

            # 查询属性变更记录
            attribute_query = (
                select(ItemAttributeChange)
                .where(ItemAttributeChange.item_id == item_id)
                .order_by(desc(ItemAttributeChange.created_at))
            )
            attribute_result = await db.execute(attribute_query)
            attribute_changes = attribute_result.scalars().all()

            return {
                "item": item.to_dict(),
                "transfers": [t.to_dict() for t in transfers],
                "status_changes": [s.to_dict() for s in status_changes],
                "quantity_changes": [q.to_dict() for q in quantity_changes],
                "attribute_changes": [a.to_dict() for a in attribute_changes]
            }
        except Exception as e:
            logger.error(f"获取物品历史失败: {str(e)}")
            raise

    # ==================== 分类管理 ====================

    async def get_category_tree(
        self,
        db: AsyncSession,
        project_id: str,
        project_genre: str = None
    ) -> List[Dict[str, Any]]:
        """获取分类树（如果无分类则自动初始化默认分类）"""
        try:
            # 查询所有分类
            query = (
                select(ItemCategory)
                .where(ItemCategory.project_id == project_id)
                .order_by(asc(ItemCategory.level), asc(ItemCategory.order_index))
            )
            result = await db.execute(query)
            categories = result.scalars().all()

            # 如果没有分类，自动初始化默认分类
            if not categories:
                from app.services.category_presets import init_project_categories
                logger.info(f"📦 项目 {project_id} 无分类，自动初始化默认分类...")
                categories = await init_project_categories(db, project_id, project_genre)
                logger.info(f"✅ 已创建 {len(categories)} 个默认分类")
            else:
                logger.info(f"📋 项目 {project_id} 已有 {len(categories)} 个分类")
                for cat in categories[:5]:
                    logger.info(f"  - {cat.id[:8]}...: {cat.name}")

            # 构建树形结构
            category_dict = {c.id: c.to_dict(include_children=True) for c in categories}
            root_categories = []

            for cat in categories:
                cat_dict = category_dict[cat.id]
                if cat.parent_id and cat.parent_id in category_dict:
                    category_dict[cat.parent_id]["children"].append(cat_dict)
                else:
                    root_categories.append(cat_dict)

            return root_categories
        except Exception as e:
            logger.error(f"获取分类树失败: {str(e)}")
            raise

    async def create_category(
        self,
        db: AsyncSession,
        data: ItemCategoryCreate
    ) -> ItemCategory:
        """创建分类"""
        try:
            # 计算层级和路径
            level = 1
            path = data.name
            if data.parent_id:
                parent_query = select(ItemCategory).where(ItemCategory.id == data.parent_id)
                parent_result = await db.execute(parent_query)
                parent = parent_result.scalar_one_or_none()
                if parent:
                    level = parent.level + 1
                    path = f"{parent.path},{data.name}"

            category = ItemCategory(
                id=str(uuid.uuid4()),
                project_id=data.project_id,
                name=data.name,
                description=data.description,
                parent_id=data.parent_id,
                level=level,
                path=path,
                order_index=data.order_index,
                attribute_template=data.attribute_template,
                default_unit=data.default_unit,
                default_rarity=data.default_rarity.value if hasattr(data.default_rarity, 'value') else data.default_rarity,
                genre_type=data.genre_type.value if hasattr(data.genre_type, 'value') else data.genre_type,
                is_system=False
            )

            db.add(category)
            await db.commit()
            await db.refresh(category)

            logger.info(f"创建分类成功: {category.name}")
            return category
        except Exception as e:
            await db.rollback()
            logger.error(f"创建分类失败: {str(e)}")
            raise

    async def update_category(
        self,
        db: AsyncSession,
        category_id: str,
        data: ItemCategoryUpdate
    ) -> Optional[ItemCategory]:
        """更新分类"""
        try:
            query = select(ItemCategory).where(ItemCategory.id == category_id)
            result = await db.execute(query)
            category = result.scalar_one_or_none()

            if not category:
                return None

            update_data = data.model_dump(exclude_unset=True)

            if 'default_rarity' in update_data and hasattr(update_data['default_rarity'], 'value'):
                update_data['default_rarity'] = update_data['default_rarity'].value

            for key, value in update_data.items():
                setattr(category, key, value)

            # 如果名称变更，更新路径
            if 'name' in update_data:
                if category.parent_id:
                    parent_query = select(ItemCategory).where(ItemCategory.id == category.parent_id)
                    parent_result = await db.execute(parent_query)
                    parent = parent_result.scalar_one_or_none()
                    if parent:
                        category.path = f"{parent.path},{category.name}"
                else:
                    category.path = category.name

            await db.commit()
            await db.refresh(category)

            logger.info(f"更新分类成功: {category.name}")
            return category
        except Exception as e:
            await db.rollback()
            logger.error(f"更新分类失败: {str(e)}")
            raise

    async def delete_category(
        self,
        db: AsyncSession,
        category_id: str
    ) -> bool:
        """删除分类"""
        try:
            query = select(ItemCategory).where(ItemCategory.id == category_id)
            result = await db.execute(query)
            category = result.scalar_one_or_none()

            if not category:
                return False

            # 子分类移到父分类或成为顶级分类
            if category.parent_id:
                new_parent_id = category.parent_id
                new_level = category.level - 1
            else:
                new_parent_id = None
                new_level = 1

            # 更新子分类
            children_query = (
                update(ItemCategory)
                .where(ItemCategory.parent_id == category_id)
                .values(parent_id=new_parent_id, level=new_level)
            )
            await db.execute(children_query)

            # 更新该分类下的物品
            items_update = (
                update(Item)
                .where(Item.category_id == category_id)
                .values(category_id=new_parent_id)
            )
            await db.execute(items_update)

            # 删除分类
            await db.delete(category)
            await db.commit()

            logger.info(f"删除分类成功: {category_id}")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"删除分类失败: {str(e)}")
            raise

    # ==================== AI分析集成 ====================

    async def sync_from_analysis(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_id: str,
        chapter_number: int,
        analysis_items: List[ItemAnalysisResult],
        existing_items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """从分析结果同步物品"""
        try:
            created_items = []
            updated_items = []
            skipped_reasons = []

            # 获取已有物品列表
            if not existing_items:
                existing_items = await self._get_existing_items_for_matching(db, project_id)

            for item_result in analysis_items:
                try:
                    # 尝试匹配已有物品
                    matched_item = await self._match_existing_item(
                        item_result.item_name,
                        existing_items
                    )

                    if matched_item:
                        # 更新已有物品
                        update_result = await self._update_item_from_analysis(
                            db, matched_item, item_result, chapter_id, chapter_number
                        )
                        if update_result:
                            updated_items.append(update_result)
                    else:
                        # 创建新物品
                        new_item = await self._create_item_from_analysis(
                            db, project_id, item_result, chapter_id, chapter_number
                        )
                        if new_item:
                            created_items.append(new_item)
                            # 更新匹配列表
                            existing_items.append(new_item.to_dict())

                except Exception as item_error:
                    logger.warning(f"处理物品 [{item_result.item_name}] 失败: {str(item_error)}")
                    skipped_reasons.append({
                        "item_name": item_result.item_name,
                        "reason": str(item_error)
                    })

            await db.commit()

            # 将Item对象转换为字典
            created_items_dict = [item.to_dict() if hasattr(item, 'to_dict') else item for item in created_items]
            updated_items_dict = [item.to_dict() if hasattr(item, 'to_dict') else item for item in updated_items]

            return {
                "created_count": len(created_items),
                "updated_count": len(updated_items),
                "matched_count": sum(1 for r in analysis_items if r.reference_item_id),
                "skipped_count": len(skipped_reasons),
                "new_items": created_items_dict,
                "updated_items": updated_items_dict,
                "skipped_reasons": skipped_reasons
            }
        except Exception as e:
            await db.rollback()
            logger.error(f"同步物品失败: {str(e)}")
            raise

    async def _get_existing_items_for_matching(
        self,
        db: AsyncSession,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """获取已有物品列表用于匹配"""
        try:
            query = (
                select(Item)
                .where(Item.project_id == project_id)
                .where(Item.status.in_(['appeared', 'owned', 'equipped', 'sealed']))
            )
            result = await db.execute(query)
            items = result.scalars().all()
            return [item.to_dict() for item in items]
        except Exception as e:
            logger.warning(f"获取已有物品失败: {str(e)}")
            return []

    async def _match_existing_item(
        self,
        item_name: str,
        existing_items: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """匹配已有物品（增强匹配：处理多种名称变体）"""
        import re

        # 深度清理物品名称
        def clean_name_deep(name: str) -> str:
            if not name:
                return ''

            # 1. 移除书名号《》
            name = re.sub(r'[《》]', '', name)

            # 2. 移除各种引号："" '' 「」 『』
            name = re.sub(r'[""「」『』]', '', name)
            name = name.replace('"', '').replace("'", '')

            # 3. 移除方括号标签：【xxx】[xxx]
            name = re.sub(r'[【\[][^\】\]]*[\】\]]', '', name)

            # 4. 移除括号及其内容（别名、说明等）
            name = re.sub(r'[（\(][^）\)]*[）\)]', '', name)

            # 5. 移除破折号和下划线
            name = name.replace('-', '').replace('_', '')

            # 6. 移除多余空格
            name = re.sub(r'\s+', '', name)

            # 7. 移除数量词前缀（数字+量词的组合，如"三颗"、"两块"、"一个"）
            # 注意：不要单独移除"百"，因为"百草"是物品名的一部分
            quantity_patterns = [
                '一颗', '两颗', '三颗', '四颗', '五颗', '六颗', '七颗', '八颗', '九颗', '十颗',
                '一块', '两块', '三块', '四块', '五块', '六块', '七块', '八块', '九块', '十块',
                '一把', '两把', '三把', '四把', '五把',
                '一柄', '两柄', '三柄',
                '一枚', '两枚', '三枚',
                '一件', '两件', '三件',
                '一张', '两张', '三张',
                '一瓶', '两瓶', '三瓶',
                '一个', '两个', '三个',
                '几颗', '几块', '几把', '几柄', '几枚', '几件', '几张',
                '数颗', '数块', '数把', '数枚', '数件',
            ]
            for pattern in quantity_patterns:
                if name.startswith(pattern):
                    name = name[len(pattern):]
                    break

            # 8. 移除指代词+量词组合（如"那把"、"这柄"、"那颗"）
            demonstrative_patterns = [
                '那把', '这把', '那柄', '这柄', '那颗', '这颗', '那块', '这块',
                '那枚', '这枚', '那件', '这件', '那张', '这张',
                '那一把', '这一把', '那一柄', '这一柄',
            ]
            for pattern in demonstrative_patterns:
                if name.startswith(pattern):
                    name = name[len(pattern):]
                    break

            # 9. 移除单纯指代词前缀（不含量词）
            simple_prefixes = ['我的', '他的', '她的', '它的', '某', '那个', '这个']
            for prefix in simple_prefixes:
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break

            # 10. 移除形容词前缀
            adj_prefixes = [
                '古老的', '神秘的', '传说中的', '祖传的', '珍贵的', '稀有的', '普通的', '特殊的', '强大的', '神奇的',
                '古老', '神秘', '祖传', '珍贵', '稀有', '普通', '特殊', '强大', '神奇',
            ]
            for adj in adj_prefixes:
                if name.startswith(adj):
                    name = name[len(adj):]
                    break

            # 11. 移除纯数字前缀（阿拉伯数字）
            name = re.sub(r'^[0-9]+', '', name)

            return name.strip().lower()

        # 简单清理（仅移除标点和空格）
        def clean_name_simple(name: str) -> str:
            if not name:
                return ''
            # 移除各种标点符号
            name = re.sub(r'[《》""''「」『』【】\[\]（）\(\)\-_]', '', name)
            name = re.sub(r'\s+', '', name)
            return name.strip().lower()

        # 清理后的输入名称
        cleaned_deep = clean_name_deep(item_name)
        cleaned_simple = clean_name_simple(item_name)
        # 原始名称（小写，仅去空格）
        raw_input = item_name.lower().strip()

        for item in existing_items:
            item_name_raw = item.get('name', '').lower().strip()
            item_name_deep = clean_name_deep(item.get('name', ''))
            item_name_simple = clean_name_simple(item.get('name', ''))

            # 1. 精确匹配（原始名称）
            if item_name_raw == raw_input:
                return item

            # 2. 深度清理后精确匹配（处理书名号、引号、标签等）
            if item_name_deep == cleaned_deep and item_name_deep:
                return item

            # 3. 简单清理后精确匹配
            if item_name_simple == cleaned_simple and item_name_simple:
                return item

            # 4. 包含匹配（深度清理后的名称互相包含）
            if item_name_deep and cleaned_deep:
                # 完全包含
                if item_name_deep in cleaned_deep or cleaned_deep in item_name_deep:
                    return item
                # 部分包含（核心名称匹配）
                # 如果其中一个名称包含另一个，且长度差距不大
                len_diff = abs(len(item_name_deep) - len(cleaned_deep))
                max_len = max(len(item_name_deep), len(cleaned_deep))
                if max_len > 0 and len_diff / max_len < 0.4:
                    # 检查是否有至少一半字符匹配
                    if item_name_deep in cleaned_deep or cleaned_deep in item_name_deep:
                        return item

            # 5. 别名匹配（多层次）
            aliases = item.get('alias', [])
            if aliases:
                for alias in aliases:
                    alias_raw = alias.lower().strip()
                    alias_deep = clean_name_deep(alias)
                    alias_simple = clean_name_simple(alias)

                    # 别名精确匹配
                    if alias_raw == raw_input:
                        return item

                    # 别名深度清理匹配
                    if alias_deep == cleaned_deep and alias_deep:
                        return item

                    # 别名简单清理匹配
                    if alias_simple == cleaned_simple and alias_simple:
                        return item

                    # 别名包含匹配
                    if alias_deep and cleaned_deep:
                        if alias_deep in cleaned_deep or cleaned_deep in alias_deep:
                            return item

        return None

    async def _create_item_from_analysis(
        self,
        db: AsyncSession,
        project_id: str,
        item_result: ItemAnalysisResult,
        chapter_id: str,
        chapter_number: int
    ) -> Optional[Item]:
        """从分析结果创建物品"""
        try:
            # 确定状态和持有者
            owner_character_name = item_result.to_character

            # 根据 event_type 确定状态
            # 如果有持有者，默认为 owned；否则为 appeared
            if owner_character_name:
                status = 'owned'
            else:
                status = 'appeared'

            # 特殊事件类型调整状态
            if item_result.event_type == 'equip' and owner_character_name:
                status = 'equipped'
            elif item_result.event_type == 'seal':
                status = 'sealed'
            elif item_result.event_type == 'consume':
                # 消耗类物品，检查数量
                if item_result.quantity_after and item_result.quantity_after <= 0:
                    status = 'consumed'
                elif owner_character_name:
                    status = 'owned'  # 还有剩余数量
            elif item_result.event_type == 'destroy':
                status = 'destroyed'
            elif item_result.event_type == 'lose':
                status = 'lost'

            # 尝试匹配分类
            category_id = await self._match_category(db, project_id, item_result.suggested_category, item_result.item_type)

            # 确定数量（注意：or 1.0 会在 quantity_after=0 时错误地返回1.0，所以使用三元运算符）
            initial_quantity = item_result.quantity_after if item_result.quantity_after is not None else 1.0

            # 🔍 详细日志：显示AI返回的物品数据
            logger.info(f"创建物品: {item_result.item_name}")
            logger.info(f"  📊 AI返回数据: event_type={item_result.event_type}, "
                       f"quantity_change={item_result.quantity_change}, "
                       f"quantity_after={item_result.quantity_after}, "
                       f"初始数量={initial_quantity}")

            # 计算初始上下文优先级（V2版本）
            is_plot_critical = item_result.is_plot_critical or False

            # 获取持有者重要性权重
            character_importance = CHARACTER_IMPORTANCE_WEIGHTS["default"]  # 默认值
            if owner_character_name:
                # 查询持有者的 role_type
                try:
                    char_query = select(Character).where(
                        Character.project_id == project_id,
                        Character.name == owner_character_name
                    )
                    char_result = await db.execute(char_query)
                    char = char_result.scalar_one_or_none()
                    if char and char.role_type:
                        character_importance = get_character_importance_weight(char.role_type)
                        logger.debug(f"  持有者 '{owner_character_name}' role_type={char.role_type}, 权重={character_importance}")
                except Exception as e:
                    logger.warning(f"查询持有者角色类型失败: {e}")

            # 获取物品类别权重
            category_name = None
            if category_id:
                try:
                    cat_query = select(ItemCategory).where(ItemCategory.id == category_id)
                    cat_result = await db.execute(cat_query)
                    cat = cat_result.scalar_one_or_none()
                    if cat:
                        category_name = cat.name
                except Exception as e:
                    logger.warning(f"查询分类名称失败: {e}")

            item_category_weight = get_item_category_weight(category_name, [item_result.item_type] if item_result.item_type else None)

            # 获取稀有度权重和保底
            rarity_weight = get_rarity_weight(item_result.rarity)
            rarity_min = get_rarity_min_priority(item_result.rarity)

            # 获取分类保底
            category_min = get_category_min_priority(category_name, [item_result.item_type] if item_result.item_type else None)

            # 计算新版本优先级
            initial_priority = calculate_context_priority_v2(
                distance=0,  # 新创建物品，距离为0
                character_importance=character_importance,
                item_category_weight=item_category_weight,
                rarity_weight=rarity_weight,
                rarity_min=rarity_min,
                category_min=category_min,
                mention_count=1,
                is_plot_critical=is_plot_critical,
                status=status
            )

            logger.info(f"  📊 优先级计算: 持有者权重={character_importance:.2f}, 类别权重={item_category_weight:.2f}, "
                       f"稀有度权重={rarity_weight:.2f}, 稀有度保底={rarity_min:.2f}, 分类保底={category_min:.2f} → 优先级={initial_priority:.2f}")

            item = Item(
                id=str(uuid.uuid4()),
                project_id=project_id,
                name=item_result.item_name,
                alias=item_result.aliases or [],
                category_id=category_id,
                description=item_result.description,
                unit=item_result.unit or '个',
                quantity=initial_quantity,
                initial_quantity=initial_quantity,
                rarity=item_result.rarity,
                quality=item_result.quality,
                attributes=item_result.attributes,
                special_effects=item_result.special_effects,
                lore=item_result.lore,
                value=item_result.value,
                source_type='story',
                source_chapter_id=chapter_id,
                source_chapter_number=chapter_number,
                status=status,
                owner_character_name=owner_character_name,
                tags=[item_result.item_type] if item_result.item_type else [],
                is_plot_critical=is_plot_critical,
                # 上下文管理字段
                last_mentioned_chapter=chapter_number,
                mention_count=1,
                context_priority=initial_priority,
                status_changed_at=datetime.now()
            )

            db.add(item)

            # 创建流转记录
            if item_result.event_type in ['obtain', 'find', 'craft', 'transfer', 'buy']:
                transfer = ItemTransfer(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    item_id=item.id,
                    transfer_type=item_result.event_type,
                    from_character_name=item_result.from_character,
                    to_character_name=item_result.to_character,
                    chapter_id=chapter_id,
                    chapter_number=chapter_number,
                    quantity=item_result.quantity_change or 1.0,
                    description=item_result.description,
                    quote_text=item_result.keyword,
                    source_type='analysis'
                )
                db.add(transfer)

            logger.info(f"创建物品: {item.name}")
            return item
        except Exception as e:
            logger.warning(f"创建物品失败: {str(e)}")
            return None

    async def _match_category(
        self,
        db: AsyncSession,
        project_id: str,
        suggested_category: Optional[str],
        item_type: Optional[str]
    ) -> Optional[str]:
        """匹配物品分类，确保总是返回一个分类ID"""
        try:
            # 构建搜索条件
            search_names = []
            if suggested_category:
                search_names.append(suggested_category)

            # 将 item_type 映射到可能存在的分类名（按优先级排序，越靠前优先级越高）
            # 注意：这些名称必须与 category_presets.py 中的预设分类名称对应
            type_to_categories = {
                # weapon 对应：现代(武器)、历史(兵器)、玄幻(法宝/攻击法宝)
                'weapon': ['武器', '兵器', '法宝', '攻击法宝', '装备'],
                # armor 对应：玄幻有防御法宝子分类，通用有装备
                'armor': ['防御法宝', '装备', '法宝'],
                # consumable 对应：玄幻(丹药)、现代(药品)、通用(道具)
                'consumable': ['丹药', '疗伤丹药', '药品', '道具'],
                # material 对应：通用(材料)、科幻(合金材料)
                'material': ['材料', '合金材料'],
                # artifact 对应：玄幻(法宝)
                'artifact': ['法宝', '攻击法宝', '特殊物品'],
                # treasure 对应：历史(宝物)、通用(特殊物品)
                'treasure': ['宝物', '特殊物品', '法宝'],
                # book 对应：玄幻(典籍)、历史(古籍文书)
                'book': ['典籍', '古籍文书'],
                # currency 对应：通用(货币)
                'currency': ['货币'],
                # beast 对应：玄幻(灵兽)
                'beast': ['灵兽'],
                # talisman 对应：玄幻(符箓)
                'talisman': ['符箓'],
                # other 对应：通用(特殊物品、道具)
                'other': ['特殊物品', '道具'],
            }
            if item_type and item_type in type_to_categories:
                search_names.extend(type_to_categories[item_type])

            # 始终在末尾添加默认分类名作为兜底（这些是通用分类，所有项目都有）
            default_categories = ['道具', '特殊物品', '装备']
            for default_cat in default_categories:
                if default_cat not in search_names:
                    search_names.append(default_cat)

            logger.info(f"🔍 匹配分类: suggested_category={suggested_category}, item_type={item_type}")
            logger.info(f"🔍 搜索列表: {search_names}")

            # 查询匹配的分类
            for name in search_names:
                query = (
                    select(ItemCategory)
                    .where(ItemCategory.project_id == project_id)
                    .where(ItemCategory.name.ilike(f"%{name}%"))
                    .limit(1)
                )
                result = await db.execute(query)
                category = result.scalar_one_or_none()
                if category:
                    logger.info(f"✅ 匹配分类成功: '{name}' -> {category.name} (ID: {category.id[:8]}...)")
                    return category.id
                else:
                    logger.debug(f"❌ 未找到分类: '{name}'")

            # 如果所有匹配都失败，获取项目的任意一个分类作为默认值
            logger.warning(f"⚠️ 所有分类匹配失败，尝试获取任意分类作为兜底")
            fallback_query = (
                select(ItemCategory)
                .where(ItemCategory.project_id == project_id)
                .order_by(ItemCategory.level.asc(), ItemCategory.order_index.asc())
                .limit(1)
            )
            fallback_result = await db.execute(fallback_query)
            fallback_category = fallback_result.scalar_one_or_none()

            if fallback_category:
                logger.info(f"✅ 使用兜底分类: {fallback_category.name} (ID: {fallback_category.id[:8]}...)")
                return fallback_category.id

            logger.warning(f"❌ 项目 {project_id} 没有任何分类，无法设置默认分类")
            return None
        except Exception as e:
            logger.warning(f"匹配分类失败: {str(e)}")
            return None

    async def _update_item_from_analysis(
        self,
        db: AsyncSession,
        matched_item: Dict[str, Any],
        item_result: ItemAnalysisResult,
        chapter_id: str,
        chapter_number: int
    ) -> Optional[Item]:
        """从分析结果更新物品，记录所有变更历史"""
        try:
            item_id = matched_item['id']

            # 查询物品
            query = select(Item).where(Item.id == item_id)
            result = await db.execute(query)
            item = result.scalar_one_or_none()

            if not item:
                return None

            # === 记录变更历史 ===
            changes_logged = []  # 用于日志汇总

            # 🔍 详细日志：显示AI返回的物品数据
            logger.info(f"更新物品: {item.name}")
            logger.info(f"  📊 AI返回数据: event_type={item_result.event_type}, "
                       f"quantity_change={item_result.quantity_change}, "
                       f"quantity_after={item_result.quantity_after}")

            # === 1. 持有者变更 ===
            old_owner = item.owner_character_name
            if item_result.to_character and item_result.to_character != old_owner:
                item.owner_character_name = item_result.to_character

                # 创建流转记录（如果有明确的转移事件）
                if item_result.event_type in ['transfer', 'give', 'trade', 'steal', 'loot', 'inherit', 'find', 'buy']:
                    transfer = ItemTransfer(
                        id=str(uuid.uuid4()),
                        project_id=item.project_id,
                        item_id=item_id,
                        transfer_type=item_result.event_type,
                        from_character_name=item_result.from_character or old_owner,
                        to_character_name=item_result.to_character,
                        chapter_id=chapter_id,
                        chapter_number=chapter_number,
                        quantity=1.0,
                        description=item_result.description,
                        quote_text=item_result.keyword,
                        source_type='analysis'
                    )
                    db.add(transfer)
                    changes_logged.append(f"持有者: {old_owner}→{item_result.to_character}")
                else:
                    # 非流转类型的持有者变更，记录为属性变更
                    await self._log_attribute_change(
                        db, item, 'owner_character_name', '持有者',
                        old_owner, item_result.to_character,
                        chapter_id, chapter_number, item_result.event_type, item_result.description
                    )
                    changes_logged.append(f"持有者: {old_owner}→{item_result.to_character}")

            # === 2. 数量变更 ===
            if item_result.quantity_after is not None:
                old_quantity = item.quantity
                new_quantity = item_result.quantity_after

                if item_result.quantity_change is not None:
                    calculated_change = item_result.quantity_change
                else:
                    calculated_change = new_quantity - old_quantity

                item.quantity = new_quantity

                # 创建数量变更记录（无论是否变化都记录）
                change_record = ItemQuantityChange(
                    id=str(uuid.uuid4()),
                    project_id=item.project_id,
                    item_id=item_id,
                    change_type='obtain' if calculated_change >= 0 else 'consume',
                    quantity_before=old_quantity,
                    quantity_change=calculated_change,
                    quantity_after=new_quantity,
                    chapter_id=chapter_id,
                    chapter_number=chapter_number,
                    reason=item_result.description or f"第{chapter_number}章分析更新",
                    involved_character_name=item_result.to_character,
                    source_type='analysis'
                )
                db.add(change_record)
                if calculated_change != 0:
                    changes_logged.append(f"数量: {old_quantity}→{new_quantity}")

            # === 3. 智能补全属性（仅当原字段为空时填充），并记录变更 ===
            if item_result.quality and not item.quality:
                item.quality = item_result.quality
                await self._log_attribute_change(
                    db, item, 'quality', '品质',
                    None, item_result.quality,
                    chapter_id, chapter_number, 'enhance', item_result.description
                )
                changes_logged.append(f"品质: {item_result.quality}")

            if item_result.special_effects and not item.special_effects:
                item.special_effects = item_result.special_effects
                await self._log_attribute_change(
                    db, item, 'special_effects', '特殊效果',
                    None, item_result.special_effects,
                    chapter_id, chapter_number, 'enhance', item_result.description
                )
                changes_logged.append(f"特效: {item_result.special_effects[:30]}...")

            if item_result.lore and not item.lore:
                item.lore = item_result.lore
                await self._log_attribute_change(
                    db, item, 'lore', '背景故事',
                    None, item_result.lore,
                    chapter_id, chapter_number, 'acquire', item_result.description
                )
                changes_logged.append(f"背景: {item_result.lore[:30]}...")

            if item_result.value and not item.value:
                item.value = item_result.value
                await self._log_attribute_change(
                    db, item, 'value', '价值',
                    None, str(item_result.value),
                    chapter_id, chapter_number, 'update', item_result.description
                )
                changes_logged.append(f"价值: {item_result.value}")

            if item_result.attributes and not item.attributes:
                item.attributes = item_result.attributes
                await self._log_attribute_change(
                    db, item, 'attributes', '属性',
                    None, str(item_result.attributes),
                    chapter_id, chapter_number, 'enhance', item_result.description
                )
                changes_logged.append(f"属性: {item_result.attributes}")

            # 稀有度（覆盖更新，记录变更）
            if item_result.rarity:
                old_rarity = item.rarity
                if old_rarity != item_result.rarity:
                    item.rarity = item_result.rarity
                    await self._log_attribute_change(
                        db, item, 'rarity', '稀有度',
                        old_rarity, item_result.rarity,
                        chapter_id, chapter_number, 'enhance', item_result.description
                    )
                    changes_logged.append(f"稀有度: {old_rarity}→{item_result.rarity}")

            # 别名（合并）
            if item_result.aliases:
                existing_aliases = item.alias or []
                new_aliases = [a for a in item_result.aliases if a not in existing_aliases]
                if new_aliases:
                    item.alias = existing_aliases + new_aliases
                    await self._log_attribute_change(
                        db, item, 'alias', '别名',
                        str(existing_aliases), str(item.alias),
                        chapter_id, chapter_number, 'update', item_result.description
                    )

            # 合并标签
            if item_result.item_type:
                existing_tags = item.tags or []
                if item_result.item_type not in existing_tags:
                    item.tags = existing_tags + [item_result.item_type]

            # 剧情关键物品标记
            if item_result.is_plot_critical is not None and item.is_plot_critical != item_result.is_plot_critical:
                old_critical = item.is_plot_critical
                item.is_plot_critical = item_result.is_plot_critical
                await self._log_attribute_change(
                    db, item, 'is_plot_critical', '剧情关键',
                    str(old_critical), str(item_result.is_plot_critical),
                    chapter_id, chapter_number, 'update', item_result.description
                )

            # === 4. 状态变更 ===
            old_status = item.status

            # 根据持有者和事件类型确定新状态
            if item.owner_character_name and item.status == 'appeared':
                item.status = 'owned'
                item.status_changed_at = datetime.now()

            # 根据事件类型更新状态
            if item_result.event_type == 'equip' and item.owner_character_name:
                item.status = 'equipped'
                item.status_changed_at = datetime.now()
            elif item_result.event_type == 'unequip' and item.status == 'equipped':
                item.status = 'owned' if item.owner_character_name else 'appeared'
                item.status_changed_at = datetime.now()
            elif item_result.event_type == 'consume':
                if item.quantity <= 0:
                    item.status = 'consumed'
                    item.status_changed_at = datetime.now()
            elif item_result.event_type == 'destroy':
                item.status = 'destroyed'
                item.owner_character_name = None
                item.status_changed_at = datetime.now()
            elif item_result.event_type == 'lose':
                item.status = 'lost'
                item.owner_character_name = None
                item.status_changed_at = datetime.now()
            elif item_result.event_type == 'seal':
                item.status = 'sealed'
                item.status_changed_at = datetime.now()

            # 创建状态变更记录
            if old_status != item.status:
                status_change = ItemStatusChange(
                    id=str(uuid.uuid4()),
                    project_id=item.project_id,
                    item_id=item_id,
                    status_before=old_status,
                    status_after=item.status,
                    chapter_id=chapter_id,
                    chapter_number=chapter_number,
                    trigger_event=item_result.event_type,
                    description=item_result.description,
                    involved_character_name=item_result.to_character,
                    source_type='analysis'
                )
                db.add(status_change)
                changes_logged.append(f"状态: {old_status}→{item.status}")

            # === 5. 更新上下文管理字段 ===
            # 更新最后提及章节和提及次数
            item.last_mentioned_chapter = chapter_number
            item.mention_count = (item.mention_count or 0) + 1

            # 计算并更新上下文优先级（V2版本）
            # 获取持有者重要性权重
            character_importance = CHARACTER_IMPORTANCE_WEIGHTS["default"]
            if item.owner_character_name:
                try:
                    char_query = select(Character).where(
                        Character.project_id == item.project_id,
                        Character.name == item.owner_character_name
                    )
                    char_result = await db.execute(char_query)
                    char = char_result.scalar_one_or_none()
                    if char and char.role_type:
                        character_importance = get_character_importance_weight(char.role_type)
                except Exception as e:
                    logger.warning(f"查询持有者角色类型失败: {e}")

            # 获取物品类别权重
            category_name = None
            if item.category_id:
                try:
                    cat_query = select(ItemCategory).where(ItemCategory.id == item.category_id)
                    cat_result = await db.execute(cat_query)
                    cat = cat_result.scalar_one_or_none()
                    if cat:
                        category_name = cat.name
                except Exception as e:
                    logger.warning(f"查询分类名称失败: {e}")

            item_category_weight = get_item_category_weight(category_name, item.tags)
            rarity_weight = get_rarity_weight(item.rarity)
            rarity_min = get_rarity_min_priority(item.rarity)
            category_min = get_category_min_priority(category_name, item.tags)

            # 计算距离（当前章节 - 上次提及）
            distance = 0  # 本次刚提及，距离为0

            new_priority = calculate_context_priority_v2(
                distance=distance,
                character_importance=character_importance,
                item_category_weight=item_category_weight,
                rarity_weight=rarity_weight,
                rarity_min=rarity_min,
                category_min=category_min,
                mention_count=item.mention_count or 1,
                is_plot_critical=item.is_plot_critical or False,
                status=item.status
            )
            item.context_priority = new_priority
            changes_logged.append(f"优先级={new_priority:.2f} (持有者={character_importance:.1f}, 类别={item_category_weight:.1f}, 稀有度保底={rarity_min:.1f})")

            # === 日志汇总 ===
            if changes_logged:
                logger.info(f"  ✅ 物品变更记录: {', '.join(changes_logged)}")
            else:
                logger.info(f"  ℹ️ 物品无变化: {item.name}")

            await db.refresh(item)
            return item
        except Exception as e:
            logger.warning(f"更新物品失败: {str(e)}")
            return None

    async def _log_attribute_change(
        self,
        db: AsyncSession,
        item: Item,
        attribute_name: str,
        attribute_label: str,
        value_before: Optional[str],
        value_after: Optional[str],
        chapter_id: str,
        chapter_number: int,
        change_type: str,
        description: Optional[str]
    ) -> None:
        """记录物品属性变更"""
        from app.models.item_attribute_change import ItemAttributeChange

        change_record = ItemAttributeChange(
            id=str(uuid.uuid4()),
            project_id=item.project_id,
            item_id=item.id,
            attribute_name=attribute_name,
            attribute_label=attribute_label,
            value_before=str(value_before) if value_before else None,
            value_after=str(value_after) if value_after else None,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            change_type=change_type,
            description=description,
            source_type='analysis'
        )
        db.add(change_record)

    async def fix_inconsistent_items(
        self,
        db: AsyncSession,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """修复不一致的物品数据（持有者不为空但状态为 appeared）

        Args:
            db: 数据库会话
            project_id: 项目ID，如果不指定则修复所有项目

        Returns:
            修复结果统计
        """
        try:
            # 查询不一致的物品：有持有者但状态为 appeared
            conditions = [
                Item.owner_character_name.isnot(None),
                Item.owner_character_name != '',
                Item.status == 'appeared'
            ]
            if project_id:
                conditions.append(Item.project_id == project_id)

            query = select(Item).where(and_(*conditions))
            result = await db.execute(query)
            inconsistent_items = result.scalars().all()

            fixed_count = 0
            for item in inconsistent_items:
                item.status = 'owned'
                item.status_changed_at = datetime.now()

                # 创建状态变更记录
                status_change = ItemStatusChange(
                    id=str(uuid.uuid4()),
                    project_id=item.project_id,
                    item_id=item.id,
                    status_before='appeared',
                    status_after='owned',
                    trigger_event='data_cleanup',
                    description='数据一致性修复：持有者不为空时状态应为 owned',
                    source_type='system'
                )
                db.add(status_change)
                fixed_count += 1

            await db.commit()
            logger.info(f"修复了 {fixed_count} 个不一致的物品状态")

            return {
                "success": True,
                "fixed_count": fixed_count,
                "message": f"已修复 {fixed_count} 个持有者不为空但状态为'未归属'的物品"
            }
        except Exception as e:
            logger.error(f"修复不一致物品失败: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "fixed_count": 0,
                "message": f"修复失败: {str(e)}"
            }

    async def fix_item_categories(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """
        修复物品分类：为没有分类的物品自动匹配分类

        Args:
            db: 数据库会话
            project_id: 项目ID

        Returns:
            修复结果统计
        """
        try:
            # 获取项目的分类列表
            categories_query = (
                select(ItemCategory)
                .where(ItemCategory.project_id == project_id)
                .order_by(ItemCategory.level.asc(), ItemCategory.order_index.asc())
            )
            categories_result = await db.execute(categories_query)
            all_categories = categories_result.scalars().all()

            if not all_categories:
                logger.warning(f"项目 {project_id} 没有任何分类，无法修复")
                return {
                    "success": False,
                    "fixed_count": 0,
                    "message": "项目没有分类数据，请先初始化分类"
                }

            # 创建分类 ID 和名称的映射
            category_id_set = {cat.id for cat in all_categories}
            category_name_map = {cat.name: cat.id for cat in all_categories}
            default_category_id = all_categories[0].id

            # 1. 查询没有分类的物品
            query_no_category = (
                select(Item)
                .where(Item.project_id == project_id)
                .where(Item.category_id.is_(None))
            )
            result_no_category = await db.execute(query_no_category)
            items_no_category = result_no_category.scalars().all()

            # 2. 查询分类ID无效的物品（category_id 不在分类表中）
            query_invalid_category = (
                select(Item)
                .where(Item.project_id == project_id)
                .where(Item.category_id.isnot(None))
            )
            result_invalid = await db.execute(query_invalid_category)
            all_items_with_category = result_invalid.scalars().all()

            items_invalid_category = [
                item for item in all_items_with_category
                if item.category_id not in category_id_set
            ]

            logger.info(f"📊 诊断结果:")
            logger.info(f"  - 无分类的物品: {len(items_no_category)} 个")
            logger.info(f"  - 分类ID无效的物品: {len(items_invalid_category)} 个")

            # 合并需要修复的物品
            items_to_fix = list(items_no_category) + items_invalid_category

            if not items_to_fix:
                logger.info(f"项目 {project_id} 所有物品分类正常")
                return {
                    "success": True,
                    "fixed_count": 0,
                    "message": "所有物品分类正常，无需修复"
                }

            # 类型到分类的映射
            type_to_category = {
                'weapon': ['武器', '兵器', '法宝', '装备'],
                'armor': ['防御法宝', '装备', '法宝'],
                'consumable': ['丹药', '药品', '道具'],
                'material': ['材料'],
                'artifact': ['法宝', '特殊物品'],
                'treasure': ['宝物', '特殊物品'],
                'book': ['典籍', '古籍文书'],
                'currency': ['货币'],
                'beast': ['灵兽'],
                'talisman': ['符箓'],
                'other': ['特殊物品', '道具'],
            }

            # 名称关键词到分类的映射
            name_keywords = {
                '货币': ['币', '钱', '金', '银', '灵石', '积分', '点数'],
                '丹药': ['丹', '药', '丸', '散', '液', '剂'],
                '法宝': ['剑', '刀', '枪', '棍', '杖', '扇', '镜', '鼎', '塔', '钟', '印'],
                '典籍': ['经', '书', '典', '籍', '谱', '诀', '法'],
                '符箓': ['符', '箓'],
                '灵兽': ['兽', '宠', '骑'],
            }

            fixed_count = 0

            for item in items_to_fix:
                matched_category_id = None

                # 1. 尝试根据 tags 匹配
                if item.tags:
                    for tag in item.tags:
                        tag_lower = tag.lower() if tag else ''
                        if tag_lower in type_to_category:
                            for cat_name in type_to_category[tag_lower]:
                                if cat_name in category_name_map:
                                    matched_category_id = category_name_map[cat_name]
                                    break
                        if matched_category_id:
                            break

                # 2. 尝试根据名称关键词匹配
                if not matched_category_id and item.name:
                    for cat_name, keywords in name_keywords.items():
                        for kw in keywords:
                            if kw in item.name:
                                if cat_name in category_name_map:
                                    matched_category_id = category_name_map[cat_name]
                                    break
                        if matched_category_id:
                            break

                # 3. 使用默认分类
                if not matched_category_id:
                    matched_category_id = default_category_id

                logger.info(f"🔧 修复物品 {item.name}: 旧分类={item.category_id}, 新分类={matched_category_id}")
                item.category_id = matched_category_id
                fixed_count += 1

            await db.commit()
            logger.info(f"✅ 为 {fixed_count} 个物品修复了分类")

            return {
                "success": True,
                "fixed_count": fixed_count,
                "message": f"已为 {fixed_count} 个物品修复分类"
            }
        except Exception as e:
            logger.error(f"修复物品分类失败: {str(e)}")
            await db.rollback()
            return {
                "success": False,
                "fixed_count": 0,
                "message": f"修复失败: {str(e)}"
            }

    # ==================== 章节上下文 ====================

    async def build_chapter_context(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_number: int,
        character_names: Optional[List[str]] = None,
        max_items: int = 15
    ) -> str:
        """构建章节生成的物品上下文（基于上下文优先级过滤）

        优先级过滤规则：
        - priority >= 0.3: 注入到上下文
        - priority < 0.3: 过滤掉（噪音过大）
        - 按优先级降序排序，优先注入高优先级物品
        """
        try:
            lines = []

            # === 优先级阈值：只注入高优先级物品 ===
            PRIORITY_THRESHOLD = 0.3

            # 1. 获取本章角色持有的物品（按优先级排序）
            if character_names:
                owner_items_query = (
                    select(Item)
                    .where(Item.project_id == project_id)
                    .where(Item.status == 'owned')
                    .where(Item.owner_character_name.in_(character_names))
                    .where(Item.context_priority >= PRIORITY_THRESHOLD)
                    .order_by(desc(Item.context_priority))
                    .limit(20)
                )
                result = await db.execute(owner_items_query)
                owner_items = result.scalars().all()

                if owner_items:
                    lines.append("【本章角色持有物品】")
                    for item in owner_items:
                        qty_str = f" x{item.quantity}" if item.quantity > 1 else ""
                        lines.append(f"- {item.owner_character_name}: {item.name}{qty_str}")
                        if item.special_effects:
                            lines.append(f"  特效: {item.special_effects[:50]}")

            # 2. 获取剧情关键物品（保持原有逻辑，优先级总是高）
            critical_query = (
                select(Item)
                .where(Item.project_id == project_id)
                .where(Item.is_plot_critical == True)
                .where(Item.status.in_(['appeared', 'owned', 'equipped', 'sealed']))
                .where(Item.context_priority >= PRIORITY_THRESHOLD)
                .limit(5)
            )
            result = await db.execute(critical_query)
            critical_items = result.scalars().all()

            if critical_items:
                lines.append("\n【剧情关键物品】")
                for item in critical_items:
                    lines.append(f"- {item.to_context_string()}")

            # 3. 获取高优先级物品（按上下文优先级排序）
            # 替换原有的"近期出现物品"逻辑，改用优先级排序
            high_priority_query = (
                select(Item)
                .where(Item.project_id == project_id)
                .where(Item.status.in_(['appeared', 'owned', 'equipped']))
                .where(Item.context_priority >= 0.5)  # 只取较高优先级
                .order_by(desc(Item.context_priority))
                .limit(max_items)
            )
            result = await db.execute(high_priority_query)
            high_priority_items = result.scalars().all()

            # 过滤掉已经在上面显示过的物品
            shown_item_ids = set()
            if character_names and owner_items:
                shown_item_ids.update(item.id for item in owner_items)
            if critical_items:
                shown_item_ids.update(item.id for item in critical_items)

            new_items = [item for item in high_priority_items if item.id not in shown_item_ids]

            if new_items:
                lines.append("\n【当前活跃物品】")
                for item in new_items[:8]:  # 最多显示8个
                    chapter_str = f"(第{item.last_mentioned_chapter or item.source_chapter_number}章提及)"
                    desc_preview = item.description[:40] if item.description else ""
                    lines.append(f"- {item.name} {chapter_str}: {desc_preview}...")

            return "\n".join(lines) if lines else ""
        except Exception as e:
            logger.warning(f"构建物品上下文失败: {str(e)}")
            return ""

    async def get_items_for_chapter(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_number: int,
        character_ids: Optional[List[str]] = None,
        max_items: int = 15
    ) -> List[Item]:
        """获取章节相关的物品列表"""
        try:
            items = []

            # 获取本章角色持有的物品
            if character_ids:
                owner_query = (
                    select(Item)
                    .where(Item.project_id == project_id)
                    .where(Item.owner_character_id.in_(character_ids))
                    .where(Item.status.in_(['owned', 'equipped']))
                    .limit(10)
                )
                result = await db.execute(owner_query)
                items.extend(result.scalars().all())

            # 获取剧情关键物品
            critical_query = (
                select(Item)
                .where(Item.project_id == project_id)
                .where(Item.is_plot_critical == True)
                .where(Item.status.in_(['appeared', 'owned', 'equipped', 'sealed']))
                .limit(3)
            )
            result = await db.execute(critical_query)
            critical_items = result.scalars().all()

            for item in critical_items:
                if item not in items:
                    items.append(item)

            # 限制数量
            return items[:max_items]
        except Exception as e:
            logger.warning(f"获取章节物品失败: {str(e)}")
            return []

    async def get_items_by_chapter(
        self,
        db: AsyncSession,
        project_id: str,
        chapter_number: int
    ) -> Dict[str, Any]:
        """
        获取与指定章节相关的所有物品

        Args:
            db: 数据库会话
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            包含物品列表和统计信息的字典
        """
        try:
            from app.models.item_attribute_change import ItemAttributeChange

            # 用于去重的集合
            item_ids = set()
            items = []

            # 1. 获取在本章节首次出现的物品
            appeared_query = (
                select(Item)
                .where(Item.project_id == project_id)
                .where(Item.source_chapter_number == chapter_number)
            )
            appeared_result = await db.execute(appeared_query)
            appeared_items = appeared_result.scalars().all()

            for item in appeared_items:
                if item.id not in item_ids:
                    item_ids.add(item.id)
                    items.append({
                        **item.to_dict(),
                        "relation_type": "首次出现",
                        "event_description": f"在第{chapter_number}章首次出现"
                    })

            # 2. 获取在本章节发生流转的物品
            transfer_query = (
                select(ItemTransfer, Item)
                .join(Item, ItemTransfer.item_id == Item.id)
                .where(ItemTransfer.project_id == project_id)
                .where(ItemTransfer.chapter_number == chapter_number)
            )
            transfer_result = await db.execute(transfer_query)
            transfer_rows = transfer_result.all()

            for transfer, item in transfer_rows:
                if item.id not in item_ids:
                    item_ids.add(item.id)
                    items.append({
                        **item.to_dict(),
                        "relation_type": "流转",
                        "event_description": transfer.description or f"从 {transfer.from_character_name or '未知'} 转移到 {transfer.to_character_name or '未知'}",
                        "transfer_type": transfer.transfer_type
                    })
                else:
                    # 更新已存在物品的事件描述
                    for existing_item in items:
                        if existing_item["id"] == item.id:
                            existing_item["relation_type"] = "多次事件"
                            break

            # 3. 获取在本章节数量发生变化的物品
            quantity_query = (
                select(ItemQuantityChange, Item)
                .join(Item, ItemQuantityChange.item_id == Item.id)
                .where(ItemQuantityChange.project_id == project_id)
                .where(ItemQuantityChange.chapter_number == chapter_number)
            )
            quantity_result = await db.execute(quantity_query)
            quantity_rows = quantity_result.all()

            for change, item in quantity_rows:
                if item.id not in item_ids:
                    item_ids.add(item.id)
                    change_desc = f"数量 {change.quantity_before} → {change.quantity_after}"
                    items.append({
                        **item.to_dict(),
                        "relation_type": "数量变更",
                        "event_description": change_desc,
                        "change_type": change.change_type
                    })
                else:
                    # 更新已存在物品的事件描述
                    for existing_item in items:
                        if existing_item["id"] == item.id:
                            if existing_item["relation_type"] != "多次事件":
                                existing_item["relation_type"] = "多次事件"
                            break

            # 4. 获取在本章节属性发生变化的物品
            attr_query = (
                select(ItemAttributeChange, Item)
                .join(Item, ItemAttributeChange.item_id == Item.id)
                .where(ItemAttributeChange.project_id == project_id)
                .where(ItemAttributeChange.chapter_number == chapter_number)
            )
            attr_result = await db.execute(attr_query)
            attr_rows = attr_result.all()

            for attr_change, item in attr_rows:
                if item.id not in item_ids:
                    item_ids.add(item.id)
                    attr_desc = f"{attr_change.attribute_label or attr_change.attribute_name}: {attr_change.value_before or '无'} → {attr_change.value_after or '无'}"
                    items.append({
                        **item.to_dict(),
                        "relation_type": "属性变更",
                        "event_description": attr_desc
                    })
                else:
                    # 更新已存在物品的事件描述
                    for existing_item in items:
                        if existing_item["id"] == item.id:
                            if existing_item["relation_type"] != "多次事件":
                                existing_item["relation_type"] = "多次事件"
                            break

            logger.info(f"获取章节 {chapter_number} 相关物品: {len(items)} 个")

            return {
                "chapter_number": chapter_number,
                "items": items,
                "total": len(items),
                "stats": {
                    "appeared_count": len(appeared_items),
                    "transfer_count": len(transfer_rows),
                    "quantity_change_count": len(quantity_rows),
                    "attribute_change_count": len(attr_rows)
                }
            }

        except Exception as e:
            logger.error(f"获取章节物品失败: {str(e)}")
            return {
                "chapter_number": chapter_number,
                "items": [],
                "total": 0,
                "stats": {}
            }


# 全局实例
item_service = ItemService()