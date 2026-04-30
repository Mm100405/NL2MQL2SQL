"""add data format configs table

Revision ID: 20260312_df
Revises:
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260312_df'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _inspector().get_table_names()


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


def upgrade() -> None:
    if not _has_table('data_format_configs'):
        op.create_table(
            'data_format_configs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('user_id', sa.String(36), nullable=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('natural_language', sa.Text(), nullable=True),
            sa.Column('target_format_example', sa.JSON(), nullable=True),
            sa.Column('api_parameters_str', sa.Text(), nullable=True),
            sa.Column('generated_api', sa.JSON(), nullable=True),
            sa.Column('transform_script', sa.Text(), nullable=True),
            sa.Column('parameter_mappings', sa.JSON(), nullable=True),
            sa.Column('mql_template', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('view_id', sa.String(36), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
    if _has_table('views') and not _foreign_key_exists('data_format_configs', 'fk_data_format_configs_view_id', ['view_id'], 'views', ['id']):
        op.create_foreign_key(
            'fk_data_format_configs_view_id',
            'data_format_configs', 'views',
            ['view_id'], ['id']
        )


def downgrade() -> None:
    pass
