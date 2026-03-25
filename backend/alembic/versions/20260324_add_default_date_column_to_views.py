"""Add default_date_column_id to views

Revision ID: 20260324_default_date
Revises: feea14b28cbe
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers
revision = '20260324_default_date'
down_revision = '20260323_vd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 default_date_column_id 到 views 表
    op.add_column(
        'views',
        sa.Column('default_date_column_id', mysql.VARCHAR(36), nullable=True)
    )


def downgrade() -> None:
    # 移除 default_date_column_id
    op.drop_column('views', 'default_date_column_id')