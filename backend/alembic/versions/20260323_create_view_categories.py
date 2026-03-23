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


def upgrade() -> None:
    op.create_table(
        'view_categories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_view_categories_parent_id', 'view_categories', ['parent_id'])
    op.create_unique_constraint('uq_view_categories_name', 'view_categories', ['name'])


def downgrade() -> None:
    op.drop_constraint('uq_view_categories_name', 'view_categories', type_='unique')
    op.drop_index('ix_view_categories_parent_id', 'view_categories')
    op.drop_table('view_categories')
