"""sync current model schema

Revision ID: 20260430_schema_sync
Revises: 20260324_default_date
Create Date: 2026-04-30

"""
from alembic import op
import sqlalchemy as sa

from app.database import Base
from app.models import *  # noqa: F401,F403


revision = '20260430_schema_sync'
down_revision = '20260324_default_date'
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    inspector = _inspector()
    table_names = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in table_names:
            continue
        existing_columns = {column['name'] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns or column.primary_key:
                continue
            op.add_column(table.name, sa.Column(column.name, column.type, nullable=True))


def downgrade() -> None:
    pass
