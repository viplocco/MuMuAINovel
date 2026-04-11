"""物品分类数据模型 - 树形结构"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base
import uuid


class ItemCategory(Base):
    """
    物品分类表 - 树形分类体系

    支持多级分类，如：
    - 法宝
      - 攻击类法宝
        - 剑类法宝
        - 刀类法宝
      - 防御类法宝
    - 丹药
      - 疗伤丹药
      - 突破丹药
    """
    __tablename__ = "item_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # === 分类信息 ===
    name = Column(String(100), nullable=False, comment="分类名称")
    description = Column(Text, comment="分类描述")

    # === 树形结构 ===
    parent_id = Column(String(36), ForeignKey("item_categories.id", ondelete="SET NULL"), comment="父分类ID")
    level = Column(Integer, default=1, comment="层级（1为顶级分类）")
    path = Column(String(500), comment="分类路径（如：法宝,攻击类法宝,剑类法宝）")
    order_index = Column(Integer, default=0, comment="同级排序")

    # === 分类属性模板 ===
    attribute_template = Column(Text, comment="该分类下物品的属性模板")
    default_unit = Column(String(20), comment="默认计量单位")
    default_rarity = Column(String(20), comment="默认稀有度")

    # === 适用题材 ===
    genre_type = Column(String(50), comment="适用题材类型: fantasy/modern/scifi/historical/common")

    # === 统计信息 ===
    item_count = Column(Integer, default=0, comment="该分类下物品数量（含子分类）")

    # === 元数据 ===
    is_system = Column(Boolean, default=False, comment="是否系统预设分类")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ItemCategory(id={self.id[:8]}, name={self.name}, level={self.level})>"

    def to_dict(self, include_children=False):
        result = {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "level": self.level,
            "path": self.path,
            "order_index": self.order_index,
            "attribute_template": self.attribute_template,
            "default_unit": self.default_unit,
            "default_rarity": self.default_rarity,
            "genre_type": self.genre_type,
            "item_count": self.item_count,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            result["children"] = []
        return result

    def update_path(self, parent_path=None):
        """更新分类路径"""
        if parent_path:
            self.path = f"{parent_path},{self.name}"
        else:
            self.path = self.name
        return self.path