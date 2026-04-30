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


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return column in {col['name'] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column('views', 'default_date_column_id'):
        op.add_column(
            'views',
            sa.Column('default_date_column_id', mysql.VARCHAR(36), nullable=True)
        )


def downgrade() -> None:
    pass
