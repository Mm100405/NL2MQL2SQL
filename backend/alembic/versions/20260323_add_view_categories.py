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


def upgrade() -> None:
    op.add_column('views', sa.Column('category_id', sa.String(36), nullable=True))
    op.add_column('views', sa.Column('category_name', sa.String(255), nullable=True))
    # Create index on category_id
    op.create_index('ix_views_category_id', 'views', ['category_id'])


def downgrade() -> None:
    op.drop_index('ix_views_category_id', 'views')
    op.drop_column('views', 'category_name')
    op.drop_column('views', 'category_id')
