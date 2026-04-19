"""添加世界设定Markdown字段

Revision ID: add_world_setting_markdown
Revises: add_world_setting_data
Create Date: 2026-04-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_world_setting_markdown'
down_revision: Union[str, None] = 'add_world_setting_data'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 projects 表添加 world_setting_markdown 字段
    op.add_column(
        'projects',
        sa.Column(
            'world_setting_markdown',
            sa.Text(),
            nullable=True,
            comment='世界设定Markdown内容'
        )
    )

    # 为 projects 表添加 world_setting_format 字段
    op.add_column(
        'projects',
        sa.Column(
            'world_setting_format',
            sa.String(10),
            nullable=True,
            server_default='json',
            comment='数据格式: json/markdown'
        )
    )


def downgrade() -> None:
    op.drop_column('projects', 'world_setting_format')
    op.drop_column('projects', 'world_setting_markdown')