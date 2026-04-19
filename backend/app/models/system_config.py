"""系统级配置数据模型 - 全局装饰配置"""
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base
import uuid


class SystemDecorationConfig(Base):
    """
    系统装饰配置表 - 存储全局装饰设置

    管理员可以设置全局装饰，覆盖用户本地选择。
    支持强制启用模式（所有用户必须显示特定装饰）。
    """
    __tablename__ = "system_decoration_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 装饰类型设置
    # 值: 'spring-festival' | 'spring' | 'summer' | 'autumn' | 'winter' | 'auto' | 'none'
    # 'auto' 表示根据日期自动判断季节
    decoration_type = Column(String(20), default='auto', comment="装饰类型")

    # 强制启用设置
    force_enabled = Column(Boolean, default=False, comment="是否强制启用(覆盖用户本地设置)")

    # 装饰描述/说明
    description = Column(Text, comment="装饰说明(管理员备注)")

    # 创建和更新信息
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    updated_by = Column(String(100), comment="最后更新者用户ID")

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "decoration_type": self.decoration_type,
            "force_enabled": self.force_enabled,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }