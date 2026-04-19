"""添加系统装饰配置表

Revision ID: add_system_decoration_config
Revises: extend_org_member_fields
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_system_decoration_config'
down_revision: Union[str, None] = 'extend_org_member_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('system_decoration_config',
        sa.Column('id', sa.String(length=36), nullable=False, comment='UUID'),
        sa.Column('decoration_type', sa.String(length=20), nullable=True,
                  default='auto', comment='装饰类型'),
        sa.Column('force_enabled', sa.Boolean(), nullable=True,
                  default=False, comment='是否强制启用'),
        sa.Column('description', sa.Text(), nullable=True, comment='装饰说明'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'),
                  nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'),
                  nullable=True, comment='更新时间'),
        sa.Column('updated_by', sa.String(length=100), nullable=True,
                  comment='最后更新者用户ID'),
        sa.PrimaryKeyConstraint('id')
    )

    # 插入默认配置记录
    op.execute(
        sa.text("""
            INSERT INTO system_decoration_config (id, decoration_type, force_enabled)
            VALUES ('default_decoration_config', 'auto', false)
        """)
    )


def downgrade() -> None:
    op.drop_table('system_decoration_config')