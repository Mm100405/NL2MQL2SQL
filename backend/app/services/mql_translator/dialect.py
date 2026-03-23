"""
dialect.py - SQL 方言转换器

基于 sqlglot 的 SQL 方言转换，支持 25+ 种 SQL 方言。

支持的数据源类型（对应 DataSource.type）：
- mysql -> MySQL
- postgresql -> PostgreSQL
- clickhouse -> ClickHouse
- bigquery -> BigQuery
- snowflake -> Snowflake
- mssql -> MSSQL
- oracle -> Oracle
- trino -> Trino
- duckdb -> DuckDB
"""

from typing import Dict, Optional
import sqlglot
from sqlglot import exp, dialects

# Wren 支持的数据源到 sqlglot 方言的映射
DATASOURCE_TO_DIALECT: Dict[str, str] = {
    "mysql": "mysql",
    "postgresql": "postgres",
    "clickhouse": "clickhouse",
    "bigquery": "bigquery",
    "snowflake": "snowflake",
    "mssql": "mssql",
    "oracle": "oracle",
    "trino": "trino",
    "duckdb": "duckdb",
    # 别名
    "pg": "postgres",
    "postgres": "postgres",
    "postgre": "postgres",
}


def get_dialect_name(datasource_type: str) -> str:
    """获取 sqlglot 方言名称"""
    return DATASOURCE_TO_DIALECT.get(datasource_type.lower(), datasource_type.lower())


def transpile_sql(
    sql: str,
    source_dialect: Optional[str] = None,
    target_dialect: str = "mysql",
) -> str:
    """
    将 SQL 从源方言转换为目标方言

    Args:
        sql: SQL 字符串
        source_dialect: 源方言（默认 None，表示通用）
        target_dialect: 目标方言（默认 mysql）

    Returns:
        转换后的 SQL 字符串
    """
    source = get_dialect_name(source_dialect) if source_dialect else None
    target = get_dialect_name(target_dialect)

    if source == target:
        return sql

    try:
        result = sqlglot.transpile(sql, read=source, write=target, identify=True)[0]
        return result
    except Exception as e:
        # 转换失败，返回原 SQL
        return sql


class DialectConverter:
    """
    SQL 方言转换器

    使用方式：
        converter = DialectConverter("mysql")
        sql = converter.to_dialect(ast, "postgresql")
    """

    def __init__(self, default_dialect: str = "mysql"):
        self.default_dialect = get_dialect_name(default_dialect)

    def to_dialect(
        self,
        ast: exp.Expression,
        target_dialect: str,
    ) -> str:
        """
        将 AST 转换为指定方言的 SQL

        Args:
            ast: sqlglot AST
            target_dialect: 目标方言

        Returns:
            SQL 字符串
        """
        target = get_dialect_name(target_dialect)
        try:
            return ast.sql(dialect=target)
        except Exception:
            # 失败，返回默认方言
            return ast.sql(dialect=self.default_dialect)

    def parse(
        self,
        sql: str,
        dialect: Optional[str] = None,
    ) -> exp.Expression:
        """
        解析 SQL 为 AST

        Args:
            sql: SQL 字符串
            dialect: 方言（默认使用 default_dialect）

        Returns:
            sqlglot AST
        """
        dialect = dialect or self.default_dialect
        try:
            return sqlglot.parse_one(sql, dialect=dialect)
        except Exception:
            # 解析失败，尝试通用解析
            return sqlglot.parse_one(sql)

    def validate(self, sql: str, dialect: Optional[str] = None) -> bool:
        """
        验证 SQL 是否符合方言规范

        Args:
            sql: SQL 字符串
            dialect: 方言

        Returns:
            是否有效
        """
        try:
            self.parse(sql, dialect)
            return True
        except Exception:
            return False
