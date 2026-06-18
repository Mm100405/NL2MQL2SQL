"""add dataset unique schema physical index

Revision ID: 20260610_dataset_unique_idx
Revises: 20260608_dataset_name_idx
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = '20260610_dataset_unique_idx'
down_revision = '20260608_dataset_name_idx'
branch_labels = None
depends_on = None

INDEX_NAME = 'uq_datasets_datasource_schema_physical'
TABLE_NAME = 'datasets'


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index['name'] for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_NAME in indexes:
        return

    dialect = bind.dialect.name
    if dialect == 'mysql':
        bind.execute(sa.text(f"""
            DELETE d1 FROM {TABLE_NAME} d1
            INNER JOIN {TABLE_NAME} d2
              ON d1.datasource_id = d2.datasource_id
             AND COALESCE(d1.schema_name, '') = COALESCE(d2.schema_name, '')
             AND d1.physical_name = d2.physical_name
             AND d1.id > d2.id
        """))
    else:
        bind.execute(sa.text(f"""
            DELETE FROM {TABLE_NAME}
            WHERE id NOT IN (
                SELECT id FROM (
                    SELECT MIN(id) AS id
                    FROM {TABLE_NAME}
                    GROUP BY datasource_id, COALESCE(schema_name, ''), physical_name
                ) deduped
            )
        """))

    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        ['datasource_id', 'schema_name', 'physical_name'],
        unique=True,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index['name'] for index in inspector.get_indexes(TABLE_NAME)}
    if INDEX_NAME in indexes:
        op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
