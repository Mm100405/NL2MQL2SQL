"""add_conversation_fields_to_query_history

Revision ID: feea14b28cbe
Revises: 6c116957672c
Create Date: 2026-02-05 15:16:15.477364

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'feea14b28cbe'
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


def _create_index_if_missing(table: str, index_name: str, columns: list[str], unique: bool = False) -> None:
    if not _has_table(table):
        return
    indexes = {idx['name'] for idx in _inspector().get_indexes(table)}
    if index_name not in indexes:
        op.create_index(index_name, table, columns, unique=unique)


def upgrade() -> None:
    if not _has_table('sql_analyses'):
        op.create_table(
            'sql_analyses',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('sql', sa.Text(), nullable=False, comment='SQL语句'),
            sa.Column('depth', sa.String(length=20), nullable=True, comment='分析深度: table/column/operator'),
            sa.Column('result', sa.JSON(), nullable=True, comment='分析结果'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        )
    _create_index_if_missing('sql_analyses', 'ix_sql_analyses_id', ['id'])

    if not _has_table('data_relations'):
        op.create_table(
            'data_relations',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('left_dataset_id', sa.String(length=36), nullable=False),
            sa.Column('right_dataset_id', sa.String(length=36), nullable=False),
            sa.Column('join_type', sa.String(length=20), nullable=False),
            sa.Column('join_conditions', sa.JSON(), nullable=False),
            sa.Column('relationship_type', sa.String(length=10), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['left_dataset_id'], ['datasets.id']),
            sa.ForeignKeyConstraint(['right_dataset_id'], ['datasets.id']),
        )

    _add_column_if_missing('query_history', sa.Column('conversation_id', sa.String(length=36), nullable=True))
    _add_column_if_missing('query_history', sa.Column('messages', sa.JSON(), nullable=True))
    _create_index_if_missing('query_history', 'ix_query_history_conversation_id', ['conversation_id'])

    _add_column_if_missing('workbooks', sa.Column('color', sa.String(length=20), nullable=True, comment='颜色标识'))
    _add_column_if_missing('workbooks', sa.Column('status', sa.String(length=20), nullable=True, comment='状态: active/stopped'))
    _add_column_if_missing('workbooks', sa.Column('owner', sa.String(length=100), nullable=True, comment='负责人'))

    _add_column_if_missing('metric_catalogs', sa.Column('code', sa.String(length=100), nullable=True, comment='指标编码'))
    _add_column_if_missing('metric_catalogs', sa.Column('type', sa.String(length=20), nullable=True, comment='指标类型: basic/derived/composite'))
    _add_column_if_missing('metric_catalogs', sa.Column('status', sa.String(length=20), nullable=True, comment='状态: published/draft/deprecated'))
    _add_column_if_missing('metric_catalogs', sa.Column('formula', sa.Text(), nullable=True, comment='计算逻辑'))
    _add_column_if_missing('metric_catalogs', sa.Column('owner', sa.String(length=100), nullable=True, comment='负责人'))
    _add_column_if_missing('metric_catalogs', sa.Column('dimensions', sa.JSON(), nullable=True, comment='关联维度'))
    _add_column_if_missing('metric_catalogs', sa.Column('query_count', sa.Integer(), nullable=True, comment='查询次数'))
    _add_column_if_missing('metric_catalogs', sa.Column('application_count', sa.Integer(), nullable=True, comment='应用数量'))
    _add_column_if_missing('metric_catalogs', sa.Column('dependency_count', sa.Integer(), nullable=True, comment='依赖指标数'))

    _add_column_if_missing('metric_applications', sa.Column('type', sa.String(length=20), nullable=True, comment='应用类型: dashboard/report/api'))
    _add_column_if_missing('metric_applications', sa.Column('metrics', sa.JSON(), nullable=True, comment='包含的指标列表'))
    _add_column_if_missing('metric_applications', sa.Column('owner', sa.String(length=100), nullable=True, comment='负责人'))
    _add_column_if_missing('metric_applications', sa.Column('view_count', sa.Integer(), nullable=True, comment='查看次数'))


def downgrade() -> None:
    pass
