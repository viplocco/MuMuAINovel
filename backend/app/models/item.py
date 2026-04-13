"""物品管理数据模型"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, Boolean, JSON, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Item(Base):
    """
    物品主表 - 管理小说中的物品

    物品生命周期：
    - appeared: 已出现（未被任何人持有）
    - owned: 被持有
    - equipped: 已装备
    - consumed: 已消耗
    - destroyed: 已销毁
    - lost: 已丢失
    - sealed: 被封印
    """
    __tablename__ = "items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # === 基本信息 ===
    name = Column(String(100), nullable=False, comment="物品名称")
    alias = Column(JSON, comment="别名/曾用名列表: ['玄铁重剑', '那把剑']")
    category_id = Column(String(36), ForeignKey("item_categories.id", ondelete="SET NULL"), comment="分类ID")

    # === 物品属性 ===
    description = Column(Text, comment="物品描述/外观")
    unit = Column(String(20), default="个", comment="计量单位")
    quantity = Column(Float, default=1.0, comment="当前数量（支持小数，如灵石100.5）")
    initial_quantity = Column(Float, comment="初始数量（用于重置参考）")
    max_quantity = Column(Float, comment="最大堆叠数量（可选）")

    # === 物品详情 ===
    rarity = Column(String(20), comment="稀有度: common/uncommon/rare/epic/legendary/artifact")
    quality = Column(String(50), comment="品质（如：上品、极品）")
    attributes = Column(JSON, comment="物品属性(JSON): {attack: 100, defense: 50}")
    special_effects = Column(Text, comment="特殊效果描述")
    lore = Column(Text, comment="物品传说/背景故事")

    # === 价值和来源 ===
    value = Column(Integer, comment="价值（游戏币/灵石等）")
    source_type = Column(String(20), default='story', comment="来源: story(剧情)/craft(制作)/purchase(购买)/drop(掉落)")
    source_chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), comment="首次出现章节ID")
    source_chapter_number = Column(Integer, comment="首次出现章节号")

    # === 当前状态 ===
    status = Column(String(20), default='appeared', index=True, comment="物品状态")
    status_changed_at = Column(DateTime, comment="状态最后变更时间")

    # === 当前持有者 ===
    owner_character_id = Column(String(36), ForeignKey("characters.id", ondelete="SET NULL"), comment="当前持有者ID")
    owner_character_name = Column(String(100), comment="当前持有者名称（冗余存储）")

    # === 关联信息 ===
    related_characters = Column(JSON, comment="关联角色名列表（非持有者的相关角色）")
    related_chapters = Column(JSON, comment="关联章节号列表")

    # === 备注和标签 ===
    tags = Column(JSON, comment="标签列表: ['法宝', '传承', '神秘']")
    notes = Column(Text, comment="创作备注")
    is_plot_critical = Column(Boolean, default=False, comment="是否剧情关键物品")

    # === 上下文管理 ===
    last_mentioned_chapter = Column(Integer, comment="最后被提及的章节号")
    mention_count = Column(Integer, default=0, comment="累计提及次数")
    # 默认值设为 0.3（忽略阈值），真实值应在创建时计算
    context_priority = Column(Float, default=0.3, comment="上下文优先级(0.0-1.0)，越低越不重要")

    # === 时间戳 ===
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index('idx_item_project_status', 'project_id', 'status'),
        Index('idx_item_category', 'category_id'),
        Index('idx_item_owner', 'owner_character_id'),
    )

    def __repr__(self):
        return f"<Item(id={self.id[:8]}, name={self.name}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "alias": self.alias or [],
            "category_id": self.category_id,
            "description": self.description,
            "unit": self.unit,
            "quantity": self.quantity,
            "initial_quantity": self.initial_quantity,
            "rarity": self.rarity,
            "quality": self.quality,
            "attributes": self.attributes,
            "special_effects": self.special_effects,
            "lore": self.lore,
            "value": self.value,
            "source_type": self.source_type,
            "source_chapter_id": self.source_chapter_id,
            "source_chapter_number": self.source_chapter_number,
            "status": self.status,
            "owner_character_id": self.owner_character_id,
            "owner_character_name": self.owner_character_name,
            "related_characters": self.related_characters or [],
            "related_chapters": self.related_chapters or [],
            "tags": self.tags or [],
            "notes": self.notes,
            "is_plot_critical": self.is_plot_critical,
            "last_mentioned_chapter": self.last_mentioned_chapter,
            "mention_count": self.mention_count or 0,
            # 注意：context_priority 可能为 0.0（已销毁/消耗），不能用 `or` 语法
            "context_priority": self.context_priority if self.context_priority is not None else 0.3,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status_changed_at": self.status_changed_at.isoformat() if self.status_changed_at else None,
        }

    def to_context_string(self) -> str:
        """转换为上下文字符串（用于章节生成提示）"""
        parts = [f"物品「{self.name}」"]

        if self.rarity:
            parts.append(f"[{self.rarity}]")

        if self.status == 'owned' and self.owner_character_name:
            parts.append(f"(当前持有者: {self.owner_character_name})")
        elif self.status == 'appeared':
            parts.append("(未被发现)")
        elif self.status == 'equipped':
            parts.append(f"(已装备于 {self.owner_character_name})")

        if self.quantity > 1:
            parts.append(f" 数量:{self.quantity}{self.unit}")

        if self.description:
            desc_preview = self.description[:80] if len(self.description) > 80 else self.description
            parts.append(f": {desc_preview}")

        if self.special_effects:
            effects_preview = self.special_effects[:50] if len(self.special_effects) > 50 else self.special_effects
            parts.append(f" 特效: {effects_preview}")

        return "".join(parts)

    def get_all_names(self) -> list:
        """获取物品的所有名称（主名称+别名）"""
        names = [self.name]
        if self.alias:
            names.extend(self.alias)
        return names