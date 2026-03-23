"""add is_default to views

Revision ID: 20260323_vd
Revises: 20260323_vcat
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260323_vd'
down_revision = '20260323_vcat'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 is_default 字段
    op.add_column('views', sa.Column('is_default', sa.Boolean(), nullable=True, default=False))
    
    # 创建索引（可选，用于快速查找默认视图）
    op.create_index('ix_views_is_default', 'views', ['is_default'], unique=False)


def downgrade():
    op.drop_index('ix_views_is_default', table_name='views')
    op.drop_column('views', 'is_default')
