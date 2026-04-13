"""添加一致性检测结果字段到剧情分析表

Revision ID: add_consistency_issues
Revises: 9571161d4354
Create Date: 2026-04-11 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_consistency_issues'
down_revision: Union[str, None] = '9571161d4354'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为 plot_analysis 表添加 consistency_issues 字段
    op.add_column(
        'plot_analysis',
        sa.Column(
            'consistency_issues',
            sa.JSON(),
            nullable=True,
            comment='一致性检测结果: [{"type": "character_death", "character_name": "张三", "issue": "角色在第5章已死亡，但在本章出现", "severity": "high", "suggestion": "修改为回忆或他人提及"}]'
        )
    )


def downgrade() -> None:
    op.drop_column('plot_analysis', 'consistency_issues')