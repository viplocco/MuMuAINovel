"""物品管理 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ItemStatus(str, Enum):
    """物品状态枚举"""
    APPEARED = "appeared"      # 已出现（未被持有）
    OWNED = "owned"            # 被持有
    EQUIPPED = "equipped"      # 已装备
    CONSUMED = "consumed"      # 已消耗
    DESTROYED = "destroyed"    # 已销毁
    LOST = "lost"              # 已丢失
    SEALED = "sealed"          # 被封印


class ItemRarity(str, Enum):
    """物品稀有度枚举"""
    COMMON = "common"          # 普通
    UNCOMMON = "uncommon"      # 优秀
    RARE = "rare"              # 稀有
    EPIC = "epic"              # 史诗
    LEGENDARY = "legendary"    # 传说
    ARTIFACT = "artifact"      #神器


class ItemSourceType(str, Enum):
    """物品来源类型"""
    STORY = "story"            # 剧情中获得
    CRAFT = "craft"            # 制作
    PURCHASE = "purchase"      # 购买
    DROP = "drop"              # 掉落
    INHERIT = "inherit"        # 继承
    MANUAL = "manual"          # 手动添加


class TransferType(str, Enum):
    """流转类型枚举"""
    OBTAIN = "obtain"          # 获得
    GIVE = "give"              # 赠送
    TRADE = "trade"            # 交易
    TRANSFER = "transfer"      # 转移（通用转移类型）
    STEAL = "steal"            # 偷窃
    LOOT = "loot"              # 掠夺
    INHERIT = "inherit"        # 继承
    CRAFT = "craft"            # 制作获得
    FIND = "find"              # 发现/捡拾
    BUY = "buy"                # 购买
    SELL = "sell"              # 出售
    LOSE = "lose"              # 丢失
    EQUIP = "equip"            # 装备
    UNEQUIP = "unequip"        # 卸下
    SEAL = "seal"              # 封印
    DESTROY = "destroy"        # 销毁


class QuantityChangeType(str, Enum):
    """数量变更类型枚举"""
    OBTAIN = "obtain"          # 获得
    CONSUME = "consume"        # 消耗
    USE = "use"                # 使用
    SELL = "sell"              # 出售
    BUY = "buy"                # 购买
    CRAFT = "craft"            # 制作
    LOSE = "lose"              # 丢失
    SPLIT = "split"            # 分拆
    MERGE = "merge"            # 合并


class CategoryGenreType(str, Enum):
    """分类题材类型"""
    COMMON = "common"          # 通用
    FANTASY = "fantasy"        # 玄幻
    MODERN = "modern"          # 现代
    SCIFI = "scifi"            # 科幻
    HISTORICAL = "historical"  # 历史


# === 物品基础 Schema ===

class ItemBase(BaseModel):
    """物品基础信息"""
    name: str = Field(..., min_length=1, max_length=100, description="物品名称")
    alias: Optional[List[str]] = Field(None, description="别名列表")
    category_id: Optional[str] = Field(None, description="分类ID")

    description: Optional[str] = Field(None, description="物品描述")
    unit: str = Field("个", max_length=20, description="计量单位")
    quantity: float = Field(1.0, ge=0, description="当前数量")
    initial_quantity: Optional[float] = Field(None, ge=0, description="初始数量")
    max_quantity: Optional[float] = Field(None, ge=0, description="最大堆叠")

    rarity: Optional[ItemRarity] = Field(None, description="稀有度")
    quality: Optional[str] = Field(None, max_length=50, description="品质")
    attributes: Optional[Dict[str, Any]] = Field(None, description="物品属性")
    special_effects: Optional[str] = Field(None, description="特殊效果")
    lore: Optional[str] = Field(None, description="背景故事")

    value: Optional[int] = Field(None, ge=0, description="价值")
    source_type: ItemSourceType = Field(ItemSourceType.STORY, description="来源类型")
    source_chapter_number: Optional[int] = Field(None, ge=1, description="首次出现章节号")

    status: ItemStatus = Field(ItemStatus.APPEARED, description="物品状态")
    owner_character_id: Optional[str] = Field(None, description="持有者ID")
    owner_character_name: Optional[str] = Field(None, max_length=100, description="持有者名称")

    related_characters: Optional[List[str]] = Field(None, description="关联角色列表")
    related_chapters: Optional[List[int]] = Field(None, description="关联章节列表")

    tags: Optional[List[str]] = Field(None, description="标签列表")
    notes: Optional[str] = Field(None, description="创作备注")
    is_plot_critical: bool = Field(False, description="是否剧情关键物品")


class ItemCreate(ItemBase):
    """创建物品请求"""
    project_id: str = Field(..., description="项目ID")


class ItemUpdate(BaseModel):
    """更新物品请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    alias: Optional[List[str]] = None
    category_id: Optional[str] = None

    description: Optional[str] = None
    unit: Optional[str] = Field(None, max_length=20)
    quantity: Optional[float] = Field(None, ge=0)
    max_quantity: Optional[float] = Field(None, ge=0)

    rarity: Optional[ItemRarity] = None
    quality: Optional[str] = Field(None, max_length=50)
    attributes: Optional[Dict[str, Any]] = None
    special_effects: Optional[str] = None
    lore: Optional[str] = None

    value: Optional[int] = Field(None, ge=0)

    status: Optional[ItemStatus] = None
    owner_character_id: Optional[str] = None
    owner_character_name: Optional[str] = Field(None, max_length=100)

    related_characters: Optional[List[str]] = None
    related_chapters: Optional[List[int]] = None

    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_plot_critical: Optional[bool] = None


class ItemResponse(ItemBase):
    """物品响应"""
    id: str
    project_id: str

    category_name: Optional[str] = None  # 分类名称（关联查询）

    source_chapter_id: Optional[str] = None
    status_changed_at: Optional[datetime] = None

    # 上下文管理字段
    last_mentioned_chapter: Optional[int] = Field(None, description="最后被提及的章节号")
    mention_count: int = Field(0, description="累计提及次数")
    context_priority: float = Field(1.0, description="上下文优先级(0.0-1.0)")

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    """物品列表响应"""
    total: int
    items: List[ItemResponse]
    stats: Optional[Dict[str, Any]] = None


class ItemStatsResponse(BaseModel):
    """物品统计响应"""
    total: int
    by_status: Dict[str, int]
    by_rarity: Dict[str, int]
    plot_critical_count: int
    owned_count: int


# === 物品流转 Schema ===

class ItemTransferCreate(BaseModel):
    """创建流转记录请求"""
    transfer_type: TransferType = Field(..., description="流转类型")
    from_character_id: Optional[str] = Field(None, description="转出角色ID")
    from_character_name: Optional[str] = Field(None, description="转出角色名称")
    to_character_id: Optional[str] = Field(None, description="转入角色ID")
    to_character_name: Optional[str] = Field(None, description="转入角色名称")

    chapter_id: Optional[str] = Field(None, description="发生章节ID")
    chapter_number: Optional[int] = Field(None, ge=1, description="发生章节号")
    location: Optional[str] = Field(None, description="发生地点")

    quantity: float = Field(1.0, ge=0, description="流转数量")

    description: Optional[str] = Field(None, description="流转描述")
    reason: Optional[str] = Field(None, description="流转原因")
    conditions: Optional[str] = Field(None, description="流转条件")
    quote_text: Optional[str] = Field(None, description="原文引用")


class ItemTransferResponse(ItemTransferCreate):
    """流转记录响应"""
    id: str
    project_id: str
    item_id: str
    quantity_after: Optional[float] = None
    source_type: Optional[str] = None
    occurred_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# === 物品数量变更 Schema ===

class ItemQuantityChangeCreate(BaseModel):
    """创建数量变更请求"""
    change_type: QuantityChangeType = Field(..., description="变更类型")
    quantity_change: float = Field(..., description="变更量（正数增加，负数减少）")

    chapter_id: Optional[str] = Field(None, description="发生章节ID")
    chapter_number: Optional[int] = Field(None, ge=1, description="发生章节号")

    reason: Optional[str] = Field(None, description="变更原因")
    description: Optional[str] = Field(None, description="详细描述")
    involved_character_id: Optional[str] = Field(None, description="涉及角色ID")
    involved_character_name: Optional[str] = Field(None, description="涉及角色名称")


class ItemQuantityChangeResponse(ItemQuantityChangeCreate):
    """数量变更响应"""
    id: str
    project_id: str
    item_id: str
    quantity_before: Optional[float] = None
    quantity_after: Optional[float] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    source_type: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# === 物品状态变更 Schema ===

class ItemStatusChangeResponse(BaseModel):
    """状态变更响应"""
    id: str
    project_id: str
    item_id: str
    status_before: Optional[str] = None
    status_after: str
    chapter_id: Optional[str] = None
    chapter_number: Optional[int] = None
    trigger_event: Optional[str] = None
    description: Optional[str] = None
    involved_character_id: Optional[str] = None
    involved_character_name: Optional[str] = None
    source_type: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# === 物品属性变更 Schema ===

class ItemAttributeChangeResponse(BaseModel):
    """属性变更响应"""
    id: str
    project_id: str
    item_id: str
    attribute_name: str
    attribute_label: Optional[str] = None
    value_before: Optional[str] = None
    value_after: Optional[str] = None
    chapter_id: Optional[str] = None
    chapter_number: Optional[int] = None
    change_type: Optional[str] = None
    trigger_event: Optional[str] = None
    description: Optional[str] = None
    involved_character_id: Optional[str] = None
    involved_character_name: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    source_type: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# === 物品分类 Schema ===

class ItemCategoryBase(BaseModel):
    """分类基础信息"""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    description: Optional[str] = Field(None, description="分类描述")
    parent_id: Optional[str] = Field(None, description="父分类ID")
    order_index: int = Field(0, description="排序")

    attribute_template: Optional[str] = Field(None, description="属性模板")
    default_unit: Optional[str] = Field(None, max_length=20, description="默认单位")
    default_rarity: Optional[ItemRarity] = Field(None, description="默认稀有度")

    genre_type: Optional[CategoryGenreType] = Field(None, description="适用题材")


class ItemCategoryCreate(ItemCategoryBase):
    """创建分类请求"""
    project_id: str = Field(..., description="项目ID")


class ItemCategoryUpdate(BaseModel):
    """更新分类请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[str] = None
    order_index: Optional[int] = None

    attribute_template: Optional[str] = None
    default_unit: Optional[str] = Field(None, max_length=20)
    default_rarity: Optional[ItemRarity] = None


class ItemCategoryResponse(ItemCategoryBase):
    """分类响应"""
    id: str
    project_id: str
    level: int = 1
    path: Optional[str] = None
    item_count: int = 0
    is_system: bool = False
    children: Optional[List["ItemCategoryResponse"]] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# === 物品历史 Schema ===

class ItemHistoryResponse(BaseModel):
    """物品完整历史响应"""
    item: ItemResponse
    transfers: List[ItemTransferResponse]
    status_changes: List[ItemStatusChangeResponse]
    quantity_changes: List[ItemQuantityChangeResponse]
    attribute_changes: List[ItemAttributeChangeResponse] = []


# === AI分析结果物品 Schema ===

class ItemAnalysisResult(BaseModel):
    """AI分析中的物品识别结果"""
    item_name: str = Field(..., description="物品名称")
    item_type: Optional[str] = Field(None, description="物品类型(weapon/consumable/artifact等)")
    event_type: str = Field(..., description="事件类型(appear/transfer/consume/destroy/equip等)")

    reference_item_id: Optional[str] = Field(None, description="匹配的已有物品ID")

    from_character: Optional[str] = Field(None, description="原持有者")
    to_character: Optional[str] = Field(None, description="新持有者")

    quantity_change: Optional[float] = Field(None, description="数量变化")
    quantity_after: Optional[float] = Field(None, description="变化后数量")

    description: Optional[str] = Field(None, description="详细描述")
    keyword: Optional[str] = Field(None, description="原文定位关键词")

    # AI可自动提取的属性
    rarity: Optional[str] = Field(None, description="稀有度(common/uncommon/rare/epic/legendary/artifact)")
    special_effects: Optional[str] = Field(None, description="特殊效果")
    quality: Optional[str] = Field(None, description="品质（如：上品、极品、残缺等）")
    lore: Optional[str] = Field(None, description="背景故事/来历")
    value: Optional[int] = Field(None, description="价值（金币数）")
    aliases: Optional[List[str]] = Field(None, description="别名/别称列表")
    attributes: Optional[Dict[str, Any]] = Field(None, description="属性数值（如攻击力、防御力等）")
    is_plot_critical: Optional[bool] = Field(None, description="是否剧情关键物品")
    unit: Optional[str] = Field(None, description="计量单位（如：个、颗、把、张等）")

    # 分类相关
    suggested_category: Optional[str] = Field(None, description="建议分类名称")


class ItemSyncFromAnalysisRequest(BaseModel):
    """从分析同步物品请求"""
    chapter_id: str = Field(..., description="章节ID")
    chapter_number: int = Field(..., ge=1, description="章节号")
    items: List[ItemAnalysisResult] = Field(..., description="分析结果物品列表")
    existing_items: Optional[List[Dict[str, Any]]] = Field(None, description="已有物品列表（用于匹配）")


class ItemSyncFromAnalysisResponse(BaseModel):
    """从分析同步物品响应"""
    created_count: int
    updated_count: int
    matched_count: int
    skipped_count: int
    new_items: List[ItemResponse]
    updated_items: List[ItemResponse]
    skipped_reasons: List[Dict[str, Any]]


# === 章节上下文 Schema ===

class ItemContextRequest(BaseModel):
    """获取物品上下文请求"""
    chapter_number: int = Field(..., ge=1, description="章节号")
    character_ids: Optional[List[str]] = Field(None, description="本章涉及角色ID")
    max_items: int = Field(15, ge=1, le=30, description="最大物品数量")


class ItemContextResponse(BaseModel):
    """物品上下文响应"""
    chapter_number: int
    context_text: str
    items_count: int
    owned_items: List[ItemResponse]
    plot_critical_items: List[ItemResponse]
    recent_changes: List[Dict[str, Any]]


# 递归更新 forward references
ItemCategoryResponse.model_rebuild()