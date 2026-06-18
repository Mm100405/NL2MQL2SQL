"""add metric semantic enabled flag

Revision ID: 20260610_metric_semantic
Revises: 20260610_dataset_unique_idx
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = '20260610_metric_semantic'
down_revision = '20260610_dataset_unique_idx'
branch_labels = None
depends_on = None

TABLE_NAME = 'metrics'
COLUMN_NAME = 'is_semantic_enabled'


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(COLUMN_NAME, sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.alter_column(TABLE_NAME, COLUMN_NAME, server_default=None)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column['name'] for column in inspector.get_columns(TABLE_NAME)}
    if COLUMN_NAME in columns:
        op.drop_column(TABLE_NAME, COLUMN_NAME)
