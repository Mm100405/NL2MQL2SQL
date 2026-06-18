from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple
import re
import urllib.parse

from sqlalchemy import create_engine, text
from sqlalchemy.dialects import registry
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchModuleError

from app.models.datasource import DataSource, DataSourceType


class HighGoDialect_psycopg2(PGDialect_psycopg2):
    name = "highgo"
    supports_statement_cache = True

    def _get_server_version_info(self, connection):
        for statement in ("SHOW server_version", "SELECT current_setting('server_version')"):
            try:
                version = connection.exec_driver_sql(statement).scalar() or ""
            except Exception:
                continue
            match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
            if match:
                return tuple(int(part) for part in match.groups() if part is not None)

        version = connection.exec_driver_sql("select pg_catalog.version()").scalar() or ""
        highgo_match = re.search(r"Release\s+(\d+)(?:\.(\d+))?(?:\.(\d+))?", version, re.IGNORECASE)
        if highgo_match:
            return tuple(int(part) for part in highgo_match.groups() if part is not None)
        return super()._get_server_version_info(connection)


registry.register("highgo.psycopg2", __name__, "HighGoDialect_psycopg2")


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
        url = str(config["url"])
        if datasource_type == DataSourceType.highgo.value:
            return re.sub(r"^postgresql(?:\+psycopg2)?://", "highgo+psycopg2://", url, count=1)
        return url

    host = config.get("host", "localhost")
    port = config.get("port") or get_default_port(datasource_type)
    database = config.get("database", "")
    username = urllib.parse.quote_plus(config.get("username", ""))
    password = urllib.parse.quote_plus(config.get("password", ""))

    if datasource_type == DataSourceType.postgresql.value:
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.highgo.value:
        return f"highgo+psycopg2://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.mysql.value:
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.clickhouse.value:
        return f"clickhouse://{username}:{password}@{host}:{port}/{database}"
    if datasource_type == DataSourceType.dameng.value:
        return f"dm://{username}:{password}@{host}:{port}"

    raise ValueError(f"Unsupported database type: {datasource_type}")


def create_datasource_engine(datasource_type: str, connection_config: Dict[str, Any]) -> Engine:
    datasource_type = normalize_datasource_type(datasource_type)
    connection_string = build_connection_string(datasource_type, connection_config)
    connect_args: Dict[str, Any] = {}
    if datasource_type in (DataSourceType.postgresql.value, DataSourceType.highgo.value):
        connect_args["connect_timeout"] = int((connection_config or {}).get("connect_timeout") or 10)
    elif datasource_type == DataSourceType.mysql.value:
        connect_args["connect_timeout"] = int((connection_config or {}).get("connect_timeout") or 10)
    try:
        return create_engine(connection_string, connect_args=connect_args, pool_pre_ping=True)
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


def get_metadata_schema_filter(datasource_type: str, connection_config: Dict[str, Any]) -> str:
    datasource_type = normalize_datasource_type(datasource_type)
    config = connection_config or {}
    schema = str(config.get("schema") or "").strip()
    if schema:
        return schema
    if datasource_type == DataSourceType.highgo.value:
        return str(config.get("database") or "").strip()
    return ""


def fetch_tables_and_columns(datasource_type: str, connection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    datasource_type = normalize_datasource_type(datasource_type)

    if datasource_type in (DataSourceType.postgresql.value, DataSourceType.highgo.value):
        schema_filter = get_metadata_schema_filter(datasource_type, connection_config)
        engine = create_datasource_engine(datasource_type, connection_config)
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT DISTINCT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND (:schema_filter = '' OR table_schema = :schema_filter)
                  AND table_type IN ('BASE TABLE', 'VIEW')
                ORDER BY table_schema, table_name
            """), {"schema_filter": schema_filter}).fetchall()

            table_keys: List[Tuple[str, str]] = []
            seen_tables = set()
            for table_name, schema_name in rows:
                key = (schema_name, table_name)
                if key not in seen_tables:
                    seen_tables.add(key)
                    table_keys.append(key)

            columns_result = conn.execute(text("""
                SELECT table_schema, table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND (:schema_filter = '' OR table_schema = :schema_filter)
                ORDER BY table_schema, table_name, ordinal_position
            """), {"schema_filter": schema_filter}).fetchall()

            columns_by_table: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
            table_key_set = set(table_keys)
            for schema_name, table_name, column_name, data_type, is_nullable in columns_result:
                key = (schema_name, table_name)
                if key not in table_key_set:
                    continue
                columns_by_table[key].append({
                    "name": column_name,
                    "type": data_type,
                    "nullable": is_nullable == "YES",
                    "comment": "",
                })

            return [
                {
                    "name": table_name,
                    "physical_name": table_name,
                    "schema_name": schema_name,
                    "columns": columns_by_table.get((schema_name, table_name), []),
                }
                for schema_name, table_name in table_keys
            ]

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
