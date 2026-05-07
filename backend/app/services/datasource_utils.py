from __future__ import annotations

from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy import create_engine
import urllib.parse

from app.models.datasource import DataSource, DataSourceType


def normalize_datasource_type(datasource_type: str) -> str:
    return DataSource.normalize_type(datasource_type)


def get_default_port(datasource_type: str) -> int:
    datasource_type = normalize_datasource_type(datasource_type)
    ports = {
        DataSourceType.postgresql.value: 5432,
        DataSourceType.mysql.value: 3306,
        DataSourceType.clickhouse.value: 8123,
        DataSourceType.highgo.value: 5866,
        DataSourceType.dameng.value: 5236,
    }
    return ports.get(datasource_type, 0)


def build_connection_string(datasource_type: str, connection_config: Dict[str, Any]) -> str:
    config = dict(connection_config or {})
    datasource_type = normalize_datasource_type(datasource_type)

    if config.get("url"):
        return config["url"]

    host = config.get("host", "localhost")
    port = config.get("port") or get_default_port(datasource_type)
    database = config.get("database", "")
    username = urllib.parse.quote_plus(config.get("username", ""))
    password = urllib.parse.quote_plus(config.get("password", ""))

    if datasource_type == DataSourceType.postgresql.value:
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.highgo.value:
        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.mysql.value:
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.clickhouse.value:
        return f"clickhouse://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.dameng.value:
        return f"dm://{username}:{password}@{host}:{port}"

    raise ValueError(f"Unsupported database type: {datasource_type}")


def create_datasource_engine(datasource_type: str, connection_config: Dict[str, Any]) -> Engine:
    connection_string = build_connection_string(datasource_type, connection_config)
    try:
        return create_engine(connection_string)
    except NoSuchModuleError as exc:
        normalized = normalize_datasource_type(datasource_type)
        if normalized == DataSourceType.dameng.value:
            raise RuntimeError("达梦驱动未安装，请在运行环境安装 SQLAlchemy-Dm / dmPython 后再测试或执行。") from exc
        raise


def test_connection(datasource_type: str, connection_config: Dict[str, Any]) -> None:
    engine = create_datasource_engine(datasource_type, connection_config)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def quote_identifier(identifier: str, datasource_type: str) -> str:
    datasource_type = normalize_datasource_type(datasource_type)
    escaped = str(identifier).replace('"', '""')
    if datasource_type == DataSourceType.mysql.value:
        return f"`{identifier}`"
    return f'"{escaped}"'


def fetch_tables_and_columns(datasource_type: str, connection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    datasource_type = normalize_datasource_type(datasource_type)

    if datasource_type in (DataSourceType.postgresql.value, DataSourceType.highgo.value):
        engine = create_datasource_engine(datasource_type, connection_config)
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
            """)).fetchall()
            tables = []
            for table_name, schema_name in rows:
                columns_result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table_name AND table_schema = :schema_name
                    ORDER BY ordinal_position
                """), {"table_name": table_name, "schema_name": schema_name}).fetchall()
                tables.append({
                    "name": table_name,
                    "physical_name": table_name,
                    "schema_name": schema_name,
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == "YES",
                            "comment": "",
                        }
                        for col in columns_result
                    ],
                })
            return tables

    if datasource_type == DataSourceType.mysql.value:
        engine = create_datasource_engine(datasource_type, connection_config)
        with engine.connect() as conn:
            rows = conn.execute(text("SHOW TABLES")).fetchall()
            tables = []
            for row in rows:
                table_name = row[0]
                quoted_table_name = quote_identifier(table_name, datasource_type)
                columns_result = conn.execute(text(f"SHOW FULL COLUMNS FROM {quoted_table_name}")).fetchall()
                tables.append({
                    "name": table_name,
                    "physical_name": table_name,
                    "schema_name": connection_config.get("database", ""),
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[3] == "YES",
                            "comment": col[8] or "",
                        }
                        for col in columns_result
                    ],
                })
            return tables

    if datasource_type == DataSourceType.dameng.value:
        engine = create_datasource_engine(datasource_type, connection_config)
        owner = (connection_config.get("schema") or connection_config.get("username") or "").upper()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT TABLE_NAME, OWNER
                FROM ALL_TABLES
                WHERE (:owner = '' OR OWNER = :owner)
                ORDER BY OWNER, TABLE_NAME
            """), {"owner": owner}).fetchall()
            tables = []
            for table_name, schema_name in rows:
                columns_result = conn.execute(text("""
                    SELECT COLUMN_NAME, DATA_TYPE, NULLABLE
                    FROM ALL_TAB_COLUMNS
                    WHERE TABLE_NAME = :table_name AND OWNER = :schema_name
                    ORDER BY COLUMN_ID
                """), {"table_name": table_name, "schema_name": schema_name}).fetchall()
                tables.append({
                    "name": table_name,
                    "physical_name": table_name,
                    "schema_name": schema_name,
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == "Y",
                            "comment": "",
                        }
                        for col in columns_result
                    ],
                })
            return tables

    raise ValueError(f"Unsupported database type: {datasource_type}")


def get_datasource_connection_config(datasource: DataSource) -> Dict[str, Any]:
    return datasource.get_connection_config(include_password=True)
