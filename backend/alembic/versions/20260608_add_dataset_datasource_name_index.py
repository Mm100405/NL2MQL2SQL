"""add dataset datasource name index

Revision ID: 20260608_dataset_name_idx
Revises: 20260519_query_history_title
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa


revision = '20260608_dataset_name_idx'
down_revision = '20260519_query_history_title'
branch_labels = None
depends_on = None


INDEX_NAME = 'idx_datasets_datasource_name'
TABLE_NAME = 'datasets'


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index['name'] for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_NAME not in indexes:
        op.create_index(INDEX_NAME, TABLE_NAME, ['datasource_id', 'name'])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index['name'] for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_NAME in indexes:
        op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
