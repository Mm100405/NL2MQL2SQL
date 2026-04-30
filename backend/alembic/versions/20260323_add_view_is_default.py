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
    if _has_table('views') and not _has_column('views', 'is_default'):
        op.add_column('views', sa.Column('is_default', sa.Boolean(), nullable=True, default=False))
    if _has_table('views') and not _has_index('views', 'ix_views_is_default'):
        op.create_index('ix_views_is_default', 'views', ['is_default'], unique=False)


def downgrade() -> None:
    pass
