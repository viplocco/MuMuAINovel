"""物品状态变更历史"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ItemStatusChange(Base):
    """
    物品状态变更记录表

    记录物品状态的完整变更历史：
    - appeared → owned: 被拾取/获得
    - owned → equipped: 装备
    - equipped → owned: 卸下装备
    - owned → consumed: 消耗
    - owned → destroyed: 销毁
    - owned → lost: 丢失
    - owned → sealed: 封印
    - sealed → owned: 解封
    """
    __tablename__ = "item_status_changes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)

    # === 状态变更 ===
    status_before = Column(String(20), comment="变更前状态")
    status_after = Column(String(20), nullable=False, comment="变更后状态")

    # === 发生位置 ===
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"))
    chapter_number = Column(Integer)

    # === 变更详情 ===
    trigger_event = Column(Text, comment="触发事件")
    description = Column(Text, comment="变更描述")
    involved_character_id = Column(String(36), ForeignKey("characters.id", ondelete="SET NULL"))
    involved_character_name = Column(String(100))

    # === 来源 ===
    source_type = Column(String(20), default='story', comment="来源: story/analysis/manual")

    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ItemStatusChange(id={self.id[:8]}, {self.status_before}→{self.status_after})>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "item_id": self.item_id,
            "status_before": self.status_before,
            "status_after": self.status_after,
            "chapter_id": self.chapter_id,
            "chapter_number": self.chapter_number,
            "trigger_event": self.trigger_event,
            "description": self.description,
            "involved_character_id": self.involved_character_id,
            "involved_character_name": self.involved_character_name,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }