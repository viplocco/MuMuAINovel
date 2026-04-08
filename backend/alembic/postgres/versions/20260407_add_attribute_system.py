"""添加动态能力系统和职业模板库

Revision ID: add_attribute_system
Revises: d4d253e3f4c6
Create Date: 2026-04-07 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_attribute_system'
down_revision: Union[str, None] = '202603211200_add_smtp_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Project 表添加 attribute_schema 字段
    op.add_column('projects', sa.Column('attribute_schema', sa.Text(), nullable=True, comment='能力属性配置(JSON)，继承自小说类型或自定义'))

    # 2. Character 表添加能力数值字段
    op.add_column('characters', sa.Column('attributes', sa.Text(), nullable=True, comment='角色能力数值(JSON)'))
    op.add_column('characters', sa.Column('base_attributes', sa.Text(), nullable=True, comment='初始能力值(JSON)'))

    # 3. Career 表添加能力配置字段
    op.add_column('careers', sa.Column('base_attributes', sa.Text(), nullable=True, comment='职业基础能力配置(JSON)'))
    op.add_column('careers', sa.Column('per_stage_bonus', sa.Text(), nullable=True, comment='每阶段能力加成(JSON)'))

    # 4. 创建 career_templates 表
    op.create_table(
        'career_templates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, comment='职业名称'),
        sa.Column('type', sa.String(20), nullable=False, comment='职业类型: main/sub'),
        sa.Column('description', sa.Text(), nullable=True, comment='职业描述'),
        sa.Column('category', sa.String(50), nullable=True, comment='职业分类'),
        sa.Column('applicable_genres', sa.Text(), nullable=False, comment='适用小说类型(JSON)'),
        sa.Column('stages', sa.Text(), nullable=False, comment='职业阶段列表(JSON)'),
        sa.Column('max_stage', sa.Integer(), nullable=False, server_default='10', comment='最大阶段数'),
        sa.Column('requirements', sa.Text(), nullable=True, comment='职业要求'),
        sa.Column('special_abilities', sa.Text(), nullable=True, comment='特殊能力'),
        sa.Column('worldview_rules', sa.Text(), nullable=True, comment='世界观规则关联'),
        sa.Column('attribute_bonuses', sa.Text(), nullable=True, comment='属性加成(JSON)'),
        sa.Column('base_attributes', sa.Text(), nullable=True, comment='基础能力配置(JSON)'),
        sa.Column('per_stage_bonus', sa.Text(), nullable=True, comment='每阶段能力加成(JSON)'),
        sa.Column('is_official', sa.Boolean(), nullable=True, server_default='1', comment='是否官方模板'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1', comment='是否启用'),
        sa.Column('order_index', sa.Integer(), nullable=True, server_default='0', comment='排序序号'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), comment='更新时间'),
    )

    # 创建索引
    op.create_index('idx_career_template_type', 'career_templates', ['type'])
    op.create_index('idx_career_template_official', 'career_templates', ['is_official'])


def downgrade() -> None:
    # 删除 career_templates 表
    op.drop_index('idx_career_template_official', 'career_templates')
    op.drop_index('idx_career_template_type', 'career_templates')
    op.drop_table('career_templates')

    # 删除 Career 表字段
    op.drop_column('careers', 'per_stage_bonus')
    op.drop_column('careers', 'base_attributes')

    # 删除 Character 表字段
    op.drop_column('characters', 'base_attributes')
    op.drop_column('characters', 'attributes')

    # 删除 Project 表字段
    op.drop_column('projects', 'attribute_schema')