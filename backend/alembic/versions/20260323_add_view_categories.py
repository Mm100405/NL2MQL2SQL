"""add category fields to views table

Revision ID: 20260323_vc
Revises: 20260312_df
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260323_vc'
down_revision = '20260312_df'
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {col['name'] for col in _inspector().get_columns(table)}


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return index_name in {idx['name'] for idx in _inspector().get_indexes(table)}


def upgrade() -> None:
    if _has_table('views') and not _has_column('views', 'category_id'):
        op.add_column('views', sa.Column('category_id', sa.String(36), nullable=True))
    if _has_table('views') and not _has_column('views', 'category_name'):
        op.add_column('views', sa.Column('category_name', sa.String(255), nullable=True))
    if _has_table('views') and not _has_index('views', 'ix_views_category_id'):
        op.create_index('ix_views_category_id', 'views', ['category_id'])


def downgrade() -> None:
    pass
