"""add query history title

Revision ID: 20260519_query_history_title
Revises: 20260430_schema_sync
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa


revision = '20260519_query_history_title'
down_revision = '20260430_schema_sync'
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column['name'] for column in inspector.get_columns('query_history')}
    if 'title' not in columns:
        op.add_column('query_history', sa.Column('title', sa.String(length=255), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column['name'] for column in inspector.get_columns('query_history')}
    if 'title' in columns:
        op.drop_column('query_history', 'title')
