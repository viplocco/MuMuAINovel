"""添加物品上下文优先级字段

Revision ID: add_item_context_priority
Revises: 20260411_add_consistency_issues
Create Date: 2026-04-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_item_context_priority'
down_revision: Union[str, None] = 'add_consistency_issues'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加物品上下文管理相关字段
    op.add_column('items', sa.Column('last_mentioned_chapter', sa.Integer(), nullable=True, comment='最后被提及的章节号'))
    op.add_column('items', sa.Column('mention_count', sa.Integer(), server_default='0', nullable=True, comment='累计提及次数'))
    op.add_column('items', sa.Column('context_priority', sa.Float(), server_default='1.0', nullable=True, comment='上下文优先级(0.0-1.0)，越低越不重要'))

    # 添加索引以便按优先级查询
    op.create_index('idx_item_context_priority', 'items', ['context_priority'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_item_context_priority', table_name='items')
    op.drop_column('items', 'context_priority')
    op.drop_column('items', 'mention_count')
    op.drop_column('items', 'last_mentioned_chapter')