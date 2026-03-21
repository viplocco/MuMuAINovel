"""添加SMTP邮件服务相关字段到settings表

Revision ID: 202603211200_add_smtp_fields
Revises: d4d253e3f4c6
Create Date: 2026-03-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202603211200_add_smtp_fields'
down_revision: Union[str, None] = 'd4d253e3f4c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 SMTP 配置字段
    op.add_column('settings', sa.Column('smtp_host', sa.String(length=200), nullable=True))
    op.add_column('settings', sa.Column('smtp_port', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('smtp_username', sa.String(length=200), nullable=True))
    op.add_column('settings', sa.Column('smtp_password', sa.String(length=200), nullable=True))
    op.add_column('settings', sa.Column('smtp_use_tls', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('smtp_use_ssl', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('smtp_from_email', sa.String(length=200), nullable=True))
    op.add_column('settings', sa.Column('smtp_from_name', sa.String(length=100), nullable=True))

    # 添加邮箱认证配置字段
    op.add_column('settings', sa.Column('email_auth_enabled', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('email_register_enabled', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('verification_code_ttl_minutes', sa.Integer(), nullable=True))
    op.add_column('settings', sa.Column('verification_resend_interval_seconds', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('settings', 'verification_resend_interval_seconds')
    op.drop_column('settings', 'verification_code_ttl_minutes')
    op.drop_column('settings', 'email_register_enabled')
    op.drop_column('settings', 'email_auth_enabled')
    op.drop_column('settings', 'smtp_from_name')
    op.drop_column('settings', 'smtp_from_email')
    op.drop_column('settings', 'smtp_use_ssl')
    op.drop_column('settings', 'smtp_use_tls')
    op.drop_column('settings', 'smtp_password')
    op.drop_column('settings', 'smtp_username')
    op.drop_column('settings', 'smtp_port')
    op.drop_column('settings', 'smtp_host')