"""添加AI味分析字段到剧情分析表

Revision ID: add_ai_flavor_fields
Revises: add_item_context_priority
Create Date: 2026-04-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_ai_flavor_fields'
down_revision: Union[str, None] = 'add_item_context_priority'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 plot_analysis 表添加 AI味分析相关字段
    op.add_column(
        'plot_analysis',
        sa.Column(
            'ai_flavor_score',
            sa.Float(),
            nullable=True,
            comment='AI味评分 0.0-10.0（越高越像AI生成）'
        )
    )
    op.add_column(
        'plot_analysis',
        sa.Column(
            'ai_flavor_indicators',
            sa.JSON(),
            nullable=True,
            comment='AI味指标列表: [{"type": "repetitive_patterns", "content": "原文示例", "suggestion": "改进建议", "severity": "high", "position_hint": "中段"}]'
        )
    )
    op.add_column(
        'plot_analysis',
        sa.Column(
            'ai_flavor_report',
            sa.Text(),
            nullable=True,
            comment='AI味分析详细报告'
        )
    )


def downgrade() -> None:
    op.drop_column('plot_analysis', 'ai_flavor_report')
    op.drop_column('plot_analysis', 'ai_flavor_indicators')
    op.drop_column('plot_analysis', 'ai_flavor_score')