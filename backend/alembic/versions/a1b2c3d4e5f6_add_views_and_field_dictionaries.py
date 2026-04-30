"""add views and field dictionaries

Revision ID: a1b2c3d4e5f6
Revises: 6c116957672c
Create Date: 2026-02-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6c116957672c'
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


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if _has_table(table) and not _has_column(table, column.name):
        op.add_column(table, column)


def _foreign_key_exists(table: str, name: str, local_cols: list[str] | None = None, remote_table: str | None = None, remote_cols: list[str] | None = None) -> bool:
    if not _has_table(table):
        return False
    for fk in _inspector().get_foreign_keys(table):
        if fk.get('name') == name:
            return True
        if local_cols and remote_table and remote_cols:
            if fk.get('constrained_columns') == local_cols and fk.get('referred_table') == remote_table and fk.get('referred_columns') == remote_cols:
                return True
    return False


def _create_foreign_key_if_missing(name: str, source: str, referent: str, local_cols: list[str], remote_cols: list[str]) -> None:
    if _has_table(source) and _has_table(referent) and not _foreign_key_exists(source, name, local_cols, referent, remote_cols):
        op.create_foreign_key(name, source, referent, local_cols, remote_cols)


def upgrade() -> None:
    if not _has_table('views'):
        op.create_table(
            'views',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False, unique=True),
            sa.Column('display_name', sa.String(255), nullable=True),
            sa.Column('datasource_id', sa.String(36), sa.ForeignKey('datasources.id'), nullable=False),
            sa.Column('view_type', sa.String(20), nullable=False, server_default='single_table'),
            sa.Column('base_table_id', sa.String(36), sa.ForeignKey('datasets.id'), nullable=True),
            sa.Column('join_config', sa.JSON, nullable=True),
            sa.Column('custom_sql', sa.Text, nullable=True),
            sa.Column('columns', sa.JSON, nullable=True),
            sa.Column('canvas_config', sa.JSON, nullable=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    if not _has_table('field_dictionaries'):
        op.create_table(
            'field_dictionaries',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False, unique=True),
            sa.Column('display_name', sa.String(255), nullable=True),
            sa.Column('source_type', sa.String(20), nullable=False, server_default='manual'),
            sa.Column('mappings', sa.JSON, nullable=True),
            sa.Column('ref_view_id', sa.String(36), sa.ForeignKey('views.id'), nullable=True),
            sa.Column('ref_value_column', sa.String(255), nullable=True),
            sa.Column('ref_label_column', sa.String(255), nullable=True),
            sa.Column('auto_source_dataset_id', sa.String(36), sa.ForeignKey('datasets.id'), nullable=True),
            sa.Column('auto_source_column', sa.String(255), nullable=True),
            sa.Column('auto_last_sync', sa.DateTime, nullable=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        )

    _add_column_if_missing('datasets', sa.Column('column_metadata', sa.JSON, nullable=True))
    _add_column_if_missing('metrics', sa.Column('view_id', sa.String(36), nullable=True))
    _create_foreign_key_if_missing('fk_metrics_view_id', 'metrics', 'views', ['view_id'], ['id'])
    _add_column_if_missing('dimensions', sa.Column('view_id', sa.String(36), nullable=True))
    _add_column_if_missing('dimensions', sa.Column('value_config', sa.JSON, nullable=True))
    _create_foreign_key_if_missing('fk_dimensions_view_id', 'dimensions', 'views', ['view_id'], ['id'])

    if _has_table('dimensions') and _has_column('dimensions', 'dataset_id') and op.get_bind().dialect.name != 'sqlite':
        dataset_id_column = next(col for col in _inspector().get_columns('dimensions') if col['name'] == 'dataset_id')
        if not dataset_id_column.get('nullable', True):
            op.alter_column('dimensions', 'dataset_id', existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    pass
