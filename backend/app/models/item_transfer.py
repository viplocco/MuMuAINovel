"""物品流转记录 - 追踪物品归属变化"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ItemTransfer(Base):
    """
    物品流转记录表 - 记录物品的归属变化历史

    支持的流转类型：
    - obtain: 获得物品（出现→持有）
    - give: 赠送（持有→转移）
    - trade: 交易
    - steal: 偷窃
    - loot: 掠夺/战利品
    - inherit: 继承
    - craft: 制作获得
    - find: 发现/捡拾
    - buy: 购买
    - sell: 出售
    - lose: 丢失
    """
    __tablename__ = "item_transfers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)

    # === 流转类型 ===
    transfer_type = Column(String(20), nullable=False, comment="流转类型")

    # === 涉及角色 ===
    from_character_id = Column(String(36), ForeignKey("characters.id", ondelete="SET NULL"), comment="转出角色ID")
    from_character_name = Column(String(100), comment="转出角色名称")
    to_character_id = Column(String(36), ForeignKey("characters.id", ondelete="SET NULL"), comment="转入角色ID")
    to_character_name = Column(String(100), comment="转入角色名称")

    # === 发生位置 ===
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), comment="发生章节ID")
    chapter_number = Column(Integer, comment="发生章节号")
    location = Column(String(200), comment="发生地点")

    # === 数量信息 ===
    quantity = Column(Float, default=1.0, comment="流转数量")
    quantity_after = Column(Float, comment="流转后物品总数量")

    # === 流转详情 ===
    description = Column(Text, comment="流转描述")
    reason = Column(Text, comment="流转原因")
    conditions = Column(Text, comment="流转条件（如：交易价格、代价等）")

    # === 引用原文 ===
    quote_text = Column(Text, comment="原文引用")
    quote_position = Column(Integer, comment="引用位置")

    # === 来源信息 ===
    source_type = Column(String(20), default='story', comment="来源: story/analysis/manual")

    # === 时间戳 ===
    occurred_at = Column(DateTime, server_default=func.now(), comment="发生时间")
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ItemTransfer(id={self.id[:8]}, type={self.transfer_type}, item={self.item_id[:8]})>"

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "item_id": self.item_id,
            "transfer_type": self.transfer_type,
            "from_character_id": self.from_character_id,
            "from_character_name": self.from_character_name,
            "to_character_id": self.to_character_id,
            "to_character_name": self.to_character_name,
            "chapter_id": self.chapter_id,
            "chapter_number": self.chapter_number,
            "location": self.location,
            "quantity": self.quantity,
            "quantity_after": self.quantity_after,
            "description": self.description,
            "reason": self.reason,
            "conditions": self.conditions,
            "quote_text": self.quote_text,
            "source_type": self.source_type,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }