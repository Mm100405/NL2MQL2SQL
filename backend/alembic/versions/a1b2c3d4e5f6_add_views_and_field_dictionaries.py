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


def upgrade() -> None:
    # 1. 创建 views 表
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
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # 2. 创建 field_dictionaries 表
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
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # 3. 修改 datasets 表：添加 column_metadata
    op.add_column('datasets', sa.Column('column_metadata', sa.JSON, nullable=True))
    
    # 4. 修改 metrics 表：添加 view_id
    op.add_column('metrics', sa.Column('view_id', sa.String(36), nullable=True))
    op.create_foreign_key('fk_metrics_view_id', 'metrics', 'views', ['view_id'], ['id'])
    
    # 5. 修改 dimensions 表：添加 view_id 和 value_config
    op.add_column('dimensions', sa.Column('view_id', sa.String(36), nullable=True))
    op.add_column('dimensions', sa.Column('value_config', sa.JSON, nullable=True))
    op.create_foreign_key('fk_dimensions_view_id', 'dimensions', 'views', ['view_id'], ['id'])
    
    # 6. 修改 dimensions 表：将 dataset_id 改为可空（因为现在可以关联到 view）
    op.alter_column('dimensions', 'dataset_id', existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    # 6. 恢复 dimensions.dataset_id 为非空
    op.alter_column('dimensions', 'dataset_id', existing_type=sa.String(36), nullable=False)
    
    # 5. 删除 dimensions 的新字段
    op.drop_constraint('fk_dimensions_view_id', 'dimensions', type_='foreignkey')
    op.drop_column('dimensions', 'value_config')
    op.drop_column('dimensions', 'view_id')
    
    # 4. 删除 metrics.view_id
    op.drop_constraint('fk_metrics_view_id', 'metrics', type_='foreignkey')
    op.drop_column('metrics', 'view_id')
    
    # 3. 删除 datasets.column_metadata
    op.drop_column('datasets', 'column_metadata')
    
    # 2. 删除 field_dictionaries 表
    op.drop_table('field_dictionaries')
    
    # 1. 删除 views 表
    op.drop_table('views')
