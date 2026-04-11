"""物品数量变更历史"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ItemQuantityChange(Base):
    """
    物品数量变更记录表

    记录物品数量的变化历史，每次变化都记录原因和数值：
    - obtain: 获得 +N
    - consume: 消耗 -N
    - use: 使用 -N
    - sell: 出售 -N
    - buy: 购买 +N
    - craft: 制作 +N
    - lose: 丢失 -N
    - split: 分拆
    - merge: 合并
    """
    __tablename__ = "item_quantity_changes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)

    # === 变更类型 ===
    change_type = Column(String(20), nullable=False, comment="变更类型")

    # === 数值变化 ===
    quantity_before = Column(Float, comment="变更前数量")
    quantity_change = Column(Float, nullable=False, comment="变更量（正数增加，负数减少）")
    quantity_after = Column(Float, comment="变更后数量")

    # === 发生位置 ===
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"))
    chapter_number = Column(Integer)

    # === 变更详情 ===
    reason = Column(Text, comment="变更原因")
    description = Column(Text, comment="详细描述")
    involved_character_id = Column(String(36), ForeignKey("characters.id", ondelete="SET NULL"))
    involved_character_name = Column(String(100))

    # === 关联信息 ===
    related_entity_type = Column(String(50), comment="关联实体类型(如：任务、交易等)")
    related_entity_id = Column(String(36))

    # === 来源 ===
    source_type = Column(String(20), default='story', comment="来源: story/analysis/manual")

    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        change_symbol = "+" if self.quantity_change > 0 else ""
        return f"<ItemQuantityChange(id={self.id[:8]}, {change_symbol}{self.quantity_change})>"

    def to_dict(self):
        change_symbol = "+" if self.quantity_change > 0 else ""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "item_id": self.item_id,
            "change_type": self.change_type,
            "quantity_before": self.quantity_before,
            "quantity_change": self.quantity_change,
            "quantity_after": self.quantity_after,
            "change_display": f"{change_symbol}{self.quantity_change}",
            "chapter_id": self.chapter_id,
            "chapter_number": self.chapter_number,
            "reason": self.reason,
            "description": self.description,
            "involved_character_id": self.involved_character_id,
            "involved_character_name": self.involved_character_name,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }