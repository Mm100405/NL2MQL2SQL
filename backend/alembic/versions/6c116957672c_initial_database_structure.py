"""Initial database structure

Revision ID: 6c116957672c
Revises: 
Create Date: 2026-02-04 16:51:56.144152

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql  # 专门针对MySQL的类型

# revision identifiers
revision = '6c116957672c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create datasources table
    op.create_table('datasources',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),  # 使用VARCHAR(36)代替UUID
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('connection_config', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),  # 使用MySQL DATETIME
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create datasets table
    op.create_table('datasets',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('datasource_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('physical_name', sa.String(length=255), nullable=False),
        sa.Column('schema_name', sa.String(length=255), nullable=True),
        sa.Column('columns', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(['datasource_id'], ['datasources.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create metrics table
    op.create_table('metrics',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('metric_type', sa.String(length=20), nullable=False),
        sa.Column('dataset_id', mysql.VARCHAR(36), nullable=True),
        sa.Column('aggregation', sa.String(length=20), nullable=True),
        sa.Column('calculation_method', sa.String(length=20), nullable=True),
        sa.Column('measure_column', sa.String(length=255), nullable=True),
        sa.Column('calculation_formula', sa.Text(), nullable=True),
        sa.Column('is_semi_additive', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('date_column_id', mysql.VARCHAR(36), nullable=True),
        sa.Column('base_metric_id', mysql.VARCHAR(36), nullable=True),
        sa.Column('derivation_type', sa.String(length=20), nullable=True),
        sa.Column('time_constraint', sa.Text(), nullable=True),
        sa.Column('analysis_dimensions', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('filters', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('synonyms', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('format', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(['base_metric_id'], ['metrics.id'], ),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create dimensions table
    op.create_table('dimensions',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('dataset_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('physical_column', sa.String(length=255), nullable=False),
        sa.Column('data_type', sa.String(length=20), nullable=False),
        sa.Column('dimension_type', sa.String(length=20), nullable=False),
        sa.Column('hierarchy', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('format_config', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('synonyms', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create relations table
    op.create_table('relations',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('relation_type', sa.String(length=50), nullable=False),
        sa.Column('source_dataset_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('target_dataset_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('join_conditions', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(['source_dataset_id'], ['datasets.id'], ),
        sa.ForeignKeyConstraint(['target_dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create query_history table
    op.create_table('query_history',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('natural_language', sa.Text(), nullable=False),
        sa.Column('mql_query', mysql.JSON, nullable=True),
        sa.Column('sql_query', sa.Text(), nullable=True),
        sa.Column('execution_time', sa.Integer(), nullable=True),  # milliseconds
        sa.Column('result_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('chart_config', mysql.JSON, nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create model_configs table
    op.create_table('model_configs',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),  # openai, ollama, azure, custom
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=True),  # Encrypted API key
        sa.Column('api_base', sa.String(length=500), nullable=True),  # Custom API endpoint
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('config_params', mysql.JSON, nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create system_settings table
    op.create_table('system_settings',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', mysql.JSON, nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='general'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # AIR Module Tables
    # Create workbooks table
    op.create_table('workbooks',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('owner_id', sa.String(length=255), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create integration_tasks table
    op.create_table('integration_tasks',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_config', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('target_config', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('schedule_config', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('last_run_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create consolidation_rules table
    op.create_table('consolidation_rules',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('rule_config', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('apply_to', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create data_accelerations table
    op.create_table('data_accelerations',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_dataset_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('acceleration_config', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('refresh_schedule', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('last_refresh_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(['source_dataset_id'], ['datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # CAN Module Tables
    # Create metric_catalogs table
    op.create_table('metric_catalogs',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('tags', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create metric_applications table
    op.create_table('metric_applications',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metric_ids', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('application_config', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create metric_accelerations table
    op.create_table('metric_accelerations',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metric_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('acceleration_config', mysql.LONGTEXT, nullable=False),  # 使用LONGTEXT代替JSON
        sa.Column('refresh_interval', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('last_calculated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create system_roles table
    op.create_table('system_roles',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('permissions', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=True),
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create audit_logs table
    op.create_table('audit_logs',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('timestamp', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # BIG Module Tables
    # Create lineage_nodes table
    op.create_table('lineage_nodes',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('data_source', sa.String(length=255), nullable=True),
        sa.Column('properties', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create lineage_connections table
    op.create_table('lineage_connections',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('source_node_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('target_node_id', mysql.VARCHAR(36), nullable=False),
        sa.Column('connection_type', sa.String(length=50), nullable=False),
        sa.Column('properties', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.ForeignKeyConstraint(['source_node_id'], ['lineage_nodes.id'], ),
        sa.ForeignKeyConstraint(['target_node_id'], ['lineage_nodes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create sql_analysis table
    op.create_table('sql_analysis',
        sa.Column('id', mysql.VARCHAR(36), nullable=False),
        sa.Column('original_query', sa.Text(), nullable=False),
        sa.Column('analyzed_query', sa.Text(), nullable=True),
        sa.Column('query_plan', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('performance_metrics', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('recommendations', mysql.LONGTEXT, nullable=True),  # 使用LONGTEXT代替JSON
        sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('sql_analysis')
    op.drop_table('lineage_connections')
    op.drop_table('lineage_nodes')
    op.drop_table('audit_logs')
    op.drop_table('system_roles')
    op.drop_table('metric_accelerations')
    op.drop_table('metric_applications')
    op.drop_table('metric_catalogs')
    op.drop_table('data_accelerations')
    op.drop_table('consolidation_rules')
    op.drop_table('integration_tasks')
    op.drop_table('workbooks')
    op.drop_table('system_settings')
    op.drop_table('model_configs')
    op.drop_table('query_history')
    op.drop_table('relations')
    op.drop_table('dimensions')
    op.drop_table('metrics')
    op.drop_table('datasets')
    op.drop_table('datasources')