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


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return column in {col['name'] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column('field_dictionaries', 'auto_filters'):
        op.add_column('field_dictionaries', sa.Column('auto_filters', sa.JSON, nullable=True))


def downgrade() -> None:
    pass
