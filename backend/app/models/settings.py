"""设置数据模型"""
from sqlalchemy import Column, String, Text, Float, Integer, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base
import uuid


class Settings(Base):
    """设置表"""
    __tablename__ = "settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), nullable=False, unique=True, index=True, comment="用户ID")
    api_provider = Column(String(50), default="openai", comment="API提供商")
    api_key = Column(String(500), comment="API密钥")
    api_base_url = Column(String(500), comment="自定义API地址")
    llm_model = Column(String(100), default="gpt-4", comment="模型名称")
    temperature = Column(Float, default=0.7, comment="温度参数")
    max_tokens = Column(Integer, default=2000, comment="最大token数")
    system_prompt = Column(Text, comment="系统级别提示词，每次AI调用都会使用")
    preferences = Column(Text, comment="其他偏好设置(JSON)")

    # SMTP 配置
    smtp_host = Column(String(200), comment="SMTP服务器地址")
    smtp_port = Column(Integer, default=465, comment="SMTP端口")
    smtp_username = Column(String(200), comment="SMTP用户名")
    smtp_password = Column(String(200), comment="SMTP密码")
    smtp_use_tls = Column(Integer, default=0, comment="是否使用TLS")
    smtp_use_ssl = Column(Integer, default=1, comment="是否使用SSL")
    smtp_from_email = Column(String(200), comment="发件人邮箱")
    smtp_from_name = Column(String(100), default="MuMuAINovel", comment="发件人名称")

    # 邮箱认证配置
    email_auth_enabled = Column(Integer, default=1, comment="是否启用邮箱认证")
    email_register_enabled = Column(Integer, default=1, comment="是否启用邮箱注册")
    verification_code_ttl_minutes = Column(Integer, default=10, comment="验证码有效期(分钟)")
    verification_resend_interval_seconds = Column(Integer, default=60, comment="验证码重发间隔(秒)")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        Index('idx_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<Settings(id={self.id}, user_id={self.user_id}, api_provider={self.api_provider})>"