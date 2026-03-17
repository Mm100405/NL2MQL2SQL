"""add data format configs table

Revision ID: 20260312_df
Revises:
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260312_df'
down_revision = 'b2c3d4e5f6g7'  # 连接到 add auto_filters 迁移
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    # Add foreign key if views table exists
    op.create_foreign_key(
        'fk_data_format_configs_view_id',
        'data_format_configs', 'views',
        ['view_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_data_format_configs_view_id', 'data_format_configs', type_='foreignkey')
    op.drop_table('data_format_configs')
