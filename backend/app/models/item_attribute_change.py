"""物品属性变更历史"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ItemAttributeChange(Base):
    """
    物品属性变更记录表

    记录物品除状态和数量外的其他属性变更历史：
    - 品质变化（quality）
    - 稀有度变化（rarity）
    - 持有者变化（owner_character_name）
    - 特效变化（special_effects）
    - 描述变化（description）
    - 价值变化（value）
    - 其他自定义属性变化
    """
    __tablename__ = "item_attribute_changes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)

    # === 变更字段 ===
    attribute_name = Column(String(50), nullable=False, comment="变更的属性名")
    attribute_label = Column(String(100), comment="属性显示名称")

    # === 变更值 ===
    value_before = Column(Text, comment="变更前值（JSON或文本）")
    value_after = Column(Text, comment="变更后值（JSON或文本）")

    # === 发生位置 ===
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"))
    chapter_number = Column(Integer)

    # === 变更详情 ===
    change_type = Column(String(30), comment="变更类型: update/enhance/degrade/acquire/lose")
    trigger_event = Column(Text, comment="触发事件")
    description = Column(Text, comment="变更描述")
    involved_character_id = Column(String(36), ForeignKey("characters.id", ondelete="SET NULL"))
    involved_character_name = Column(String(100))

    # === 扩展信息 ===
    extra_data = Column(JSON, comment="额外数据（如对比详情、原因等）")

    # === 来源 ===
    source_type = Column(String(20), default='story', comment="来源: story/analysis/manual")

    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ItemAttributeChange(id={self.id[:8]}, {self.attribute_name}: {self.value_before}→{self.value_after})>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "item_id": self.item_id,
            "attribute_name": self.attribute_name,
            "attribute_label": self.attribute_label,
            "value_before": self.value_before,
            "value_after": self.value_after,
            "chapter_id": self.chapter_id,
            "chapter_number": self.chapter_number,
            "change_type": self.change_type,
            "trigger_event": self.trigger_event,
            "description": self.description,
            "involved_character_id": self.involved_character_id,
            "involved_character_name": self.involved_character_name,
            "extra_data": self.extra_data,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }