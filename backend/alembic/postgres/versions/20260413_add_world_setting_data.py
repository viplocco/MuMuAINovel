"""添加世界设定结构化数据字段

Revision ID: add_world_setting_data
Revises: add_ai_flavor_fields
Create Date: 2026-04-13 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_world_setting_data'
down_revision: Union[str, None] = 'add_ai_flavor_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 projects 表添加 world_setting_data 字段
    op.add_column(
        'projects',
        sa.Column(
            'world_setting_data',
            sa.Text(),
            nullable=True,
            comment='世界设定结构化数据(JSON)'
        )
    )


def downgrade() -> None:
    op.drop_column('projects', 'world_setting_data')