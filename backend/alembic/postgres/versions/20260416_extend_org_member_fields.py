"""extend organization_member fields length

Revision ID: extend_org_member_fields
Revises: add_world_setting_markdown
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'extend_org_member_fields'
down_revision: Union[str, None] = 'add_world_setting_markdown'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 修改 position 字段长度从 100 到 200
    op.alter_column('organization_members', 'position',
                    existing_type=sa.String(100),
                    type_=sa.String(200),
                    existing_nullable=False)

    # 修改 joined_at 字段从 VARCHAR(100) 到 TEXT
    op.alter_column('organization_members', 'joined_at',
                    existing_type=sa.String(100),
                    type_=sa.Text,
                    existing_nullable=True)

    # 修改 left_at 字段从 VARCHAR(100) 到 TEXT
    op.alter_column('organization_members', 'left_at',
                    existing_type=sa.String(100),
                    type_=sa.Text,
                    existing_nullable=True)


def downgrade() -> None:
    # 回滚：position 从 200 到 100
    op.alter_column('organization_members', 'position',
                    existing_type=sa.String(200),
                    type_=sa.String(100),
                    existing_nullable=False)

    # 回滚：joined_at 从 TEXT 到 VARCHAR(100)
    op.alter_column('organization_members', 'joined_at',
                    existing_type=sa.Text,
                    type_=sa.String(100),
                    existing_nullable=True)

    # 回滚：left_at 从 TEXT 到 VARCHAR(100)
    op.alter_column('organization_members', 'left_at',
                    existing_type=sa.Text,
                    type_=sa.String(100),
                    existing_nullable=True)