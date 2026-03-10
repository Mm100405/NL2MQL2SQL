"""add auto_filters to field_dictionaries

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = '3fe7001f9299'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 auto_filters 列到 field_dictionaries 表
    op.add_column('field_dictionaries', sa.Column('auto_filters', sa.JSON, nullable=True))


def downgrade() -> None:
    # 删除 auto_filters 列
    op.drop_column('field_dictionaries', 'auto_filters')
