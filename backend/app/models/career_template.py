"""职业模板数据模型"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class CareerTemplate(Base):
    """职业模板表（系统预置，按小说类型分类）"""
    __tablename__ = "career_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 基本信息
    name = Column(String(100), nullable=False, comment="职业名称")
    type = Column(String(20), nullable=False, comment="职业类型: main(主职业)/sub(副职业)")
    description = Column(Text, comment="职业描述")
    category = Column(String(50), comment="职业分类（如：战斗系、生产系、辅助系）")

    # 适用小说类型（可多选）
    applicable_genres = Column(Text, nullable=False, comment="适用小说类型(JSON): ['玄幻', '仙侠']")

    # 阶段设定
    stages = Column(Text, nullable=False, comment="职业阶段列表(JSON): [{level:1, name:'', description:''}, ...]")
    max_stage = Column(Integer, nullable=False, default=10, comment="最大阶段数")

    # 职业特性
    requirements = Column(Text, comment="职业要求/限制")
    special_abilities = Column(Text, comment="特殊能力描述")
    worldview_rules = Column(Text, comment="世界观规则关联")

    # 能力配置
    attribute_bonuses = Column(Text, comment="属性加成(JSON): {strength: '+10%', intelligence: '+5%'}")
    base_attributes = Column(Text, comment="职业基础能力配置(JSON): {灵力: 60, 悟性: 70}")
    per_stage_bonus = Column(Text, comment="每阶段能力加成(JSON): {灵力: {per_stage: 50}, 悟性: {per_stage: 5}}")

    # 模板元数据
    is_official = Column(Boolean, default=True, comment="是否为官方预置模板")
    is_active = Column(Boolean, default=True, comment="是否启用")
    order_index = Column(Integer, default=0, comment="排序序号")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index('idx_career_template_type', 'type'),
        Index('idx_career_template_official', 'is_official'),
    )

    def __repr__(self):
        return f"<CareerTemplate(id={self.id}, name={self.name}, type={self.type})>"