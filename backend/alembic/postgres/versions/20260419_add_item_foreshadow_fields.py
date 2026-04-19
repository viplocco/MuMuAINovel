"""add item foreshadow fields and status expansion

Revision ID: add_item_foreshadow_fields
Revises: add_system_decoration_config
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_item_foreshadow_fields'
down_revision: Union[str, None] = 'add_system_decoration_config'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加伏笔关联字段
    op.add_column('items', sa.Column('related_foreshadow_id', sa.String(36), sa.ForeignKey('foreshadows.id', ondelete='SET NULL'), nullable=True, comment='关联伏笔ID'))
    op.add_column('items', sa.Column('is_foreshadow_item', sa.Boolean(), default=False, nullable=True, comment='是否伏笔关联物品'))

    # 添加别名提及次数字段
    op.add_column('items', sa.Column('alias_mention_count', sa.Integer(), default=0, nullable=True, comment='别名提及次数（累计）'))

    # 添加索引
    op.create_index('idx_item_foreshadow', 'items', ['related_foreshadow_id'])

    # 更新状态注释（无需修改列，只是扩展状态定义）
    # 新增状态：borrowed, stored, pending
    # 这些状态在代码中定义，数据库无需修改


def downgrade() -> None:
    op.drop_index('idx_item_foreshadow', 'items')
    op.drop_column('items', 'alias_mention_count')
    op.drop_column('items', 'is_foreshadow_item')
    op.drop_column('items', 'related_foreshadow_id')