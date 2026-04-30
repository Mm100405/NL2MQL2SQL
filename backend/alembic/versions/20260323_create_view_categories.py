"""create view categories table

Revision ID: 20260323_vcat
Revises: 20260323_vc
Create Date: 2026-03-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260323_vcat'
down_revision = '20260323_vc'
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return index_name in {idx['name'] for idx in _inspector().get_indexes(table)}


def _has_unique_constraint(table: str, name: str) -> bool:
    if not _has_table(table):
        return False
    return name in {constraint['name'] for constraint in _inspector().get_unique_constraints(table)}


def upgrade() -> None:
    if not _has_table('view_categories'):
        op.create_table(
            'view_categories',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('parent_id', sa.String(36), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if not _has_index('view_categories', 'ix_view_categories_parent_id'):
        op.create_index('ix_view_categories_parent_id', 'view_categories', ['parent_id'])
    if op.get_bind().dialect.name != 'sqlite' and not _has_unique_constraint('view_categories', 'uq_view_categories_name'):
        op.create_unique_constraint('uq_view_categories_name', 'view_categories', ['name'])


def downgrade() -> None:
    pass
