"""
datasource_adapter.py - 多数据源统一适配器

基于 ibis 的多数据源统一查询接口。

支持的数据源：
- MySQL
- PostgreSQL
- ClickHouse
- DuckDB (本地文件/S3)
- BigQuery
- Snowflake
- SQLite

使用方式：
    adapter = DataSourceAdapter()
    adapter.connect("mysql", {"host": "...", "port": 3306, "database": "..."})
    result = adapter.execute("SELECT * FROM sales", "mysql")
"""

import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

# ibis 后端映射
IBIS_BACKEND_MAP = {
    "mysql": "mysql",
    "postgresql": "postgres",
    "postgres": "postgres",
    "pg": "postgres",
    "clickhouse": "clickhouse",
    "duckdb": "duckdb",
    "bigquery": "bigquery",
    "snowflake": "snowflake",
    "sqlite": "sqlite",
    "mssql": "mssql",
}


@dataclass
class ConnectionInfo:
    """连接信息"""
    host: str = "localhost"
    port: int = 3306
    database: str = ""
    username: str = ""
    password: str = ""
    url: Optional[str] = None  # 完整连接 URL（优先使用）

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "ConnectionInfo":
        """从字典创建连接信息"""
        if isinstance(config, str):
            # 可能是 JSON 字符串
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                # 可能是 URL
                return cls(url=config)

        return cls(
            host=config.get("host", "localhost"),
            port=config.get("port", 3306),
            database=config.get("database", ""),
            username=config.get("username", ""),
            password=config.get("password", ""),
            url=config.get("url"),
        )

    def to_ibis_url(self, backend: str) -> str:
        """转换为 ibis 连接 URL"""
        if self.url:
            return self.url

        if backend == "mysql":
            return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif backend in ("postgres", "postgresql"):
            return f"postgres://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif backend == "clickhouse":
            return f"clickhouse://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif backend == "duckdb":
            return f"duckdb:///{self.database}"  # DuckDB 使用文件路径
        elif backend == "sqlite":
            return f"sqlite:///{self.database}"
        elif backend == "bigquery":
            # BigQuery 使用项目 ID 和数据集
            project = self.host  # 复用 host 作为 project_id
            return f"bigquery://{project}/{self.database}"
        elif backend == "snowflake":
            account = self.host
            return f"snowflake://{self.username}:{self.password}@{account}/{self.database}"
        elif backend == "mssql":
            return f"mssql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

        return f"{backend}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class DataSourceAdapter:
    """
    多数据源适配器

    基于 ibis 提供统一的查询接口。
    支持连接池复用和自动重连。
    """

    def __init__(self):
        self._connections: Dict[str, Any] = {}  # backend -> ibis connection
        self._connection_info: Dict[str, ConnectionInfo] = {}

    def connect(self, datasource_type: str, connection_config: Dict[str, Any]) -> bool:
        """
        连接到数据源

        Args:
            datasource_type: 数据源类型（如 "mysql", "postgresql"）
            connection_config: 连接配置

        Returns:
            是否连接成功
        """
        datasource_type = datasource_type.lower()
        backend = IBIS_BACKEND_MAP.get(datasource_type, datasource_type)

        try:
            conn_info = ConnectionInfo.from_dict(connection_config)
            self._connection_info[backend] = conn_info

            # 根据后端类型连接
            if backend == "duckdb":
                # DuckDB 特殊处理（可以指定数据库文件）
                import ibis
                db_path = conn_info.database or ":memory:"
                self._connections[backend] = ibis.duckdb.connect(db_path)

            elif backend == "bigquery":
                # BigQuery 需要凭据文件
                import ibis
                credentials_path = connection_config.get("credentials_path")
                if credentials_path:
                    self._connections[backend] = ibis.bigquery.connect(
                        project_id=conn_info.host,
                        dataset_id=conn_info.database,
                        credentials_path=credentials_path,
                    )
                else:
                    # 使用默认凭据
                    self._connections[backend] = ibis.bigquery.connect(
                        project_id=conn_info.host,
                        dataset_id=conn_info.database,
                    )

            elif backend == "snowflake":
                import ibis
                self._connections[backend] = ibis.snowflake.connect(
                    account=conn_info.host,
                    user=conn_info.username,
                    password=conn_info.password,
                    database=conn_info.database,
                )

            else:
                # 通用 ibis 连接
                import ibis
                url = conn_info.to_ibis_url(backend)
                self._connections[backend] = ibis.connect(url)

            logger.info(f"Connected to {backend} successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {backend}: {e}")
            return False

    def execute(
        self,
        sql: str,
        datasource_type: str,
        params: Optional[Dict[str, Any]] = None,
        limit: int = 10000,
    ) -> Dict[str, Any]:
        """
        执行 SQL 查询

        Args:
            sql: SQL 语句
            datasource_type: 数据源类型
            params: 查询参数（可选）
            limit: 结果行数限制

        Returns:
            {
                "columns": [...],
                "data": [[...], ...],
                "total_count": int,
                "execution_time": float
            }
        """
        import time
        start_time = time.time()

        datasource_type = datasource_type.lower()
        backend = IBIS_BACKEND_MAP.get(datasource_type, datasource_type)

        # 确保已连接
        if backend not in self._connections:
            conn_info = self._connection_info.get(backend)
            if conn_info:
                self.connect(datasource_type, conn_info.__dict__ if hasattr(conn_info, '__dict__') else {})
            else:
                raise ConnectionError(f"Not connected to {backend}")

        try:
            conn = self._connections[backend]

            # 执行查询
            result = conn.sql(sql)

            # 转换为 Pandas DataFrame
            df = result.limit(limit).to_pandas()

            execution_time = time.time() - start_time

            return {
                "columns": df.columns.tolist(),
                "data": df.values.tolist(),
                "total_count": len(df),
                "execution_time": execution_time,
                "datasource": datasource_type,
            }

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def disconnect(self, datasource_type: Optional[str] = None):
        """
        断开连接

        Args:
            datasource_type: 数据源类型（None 表示断开所有）
        """
        if datasource_type:
            datasource_type = datasource_type.lower()
            backend = IBIS_BACKEND_MAP.get(datasource_type, datasource_type)
            if backend in self._connections:
                try:
                    self._connections[backend].disconnect()
                except Exception:
                    pass
                del self._connections[backend]
        else:
            # 断开所有
            for backend in list(self._connections.keys()):
                self.disconnect(backend)

    def is_connected(self, datasource_type: str) -> bool:
        """检查是否已连接"""
        datasource_type = datasource_type.lower()
        backend = IBIS_BACKEND_MAP.get(datasource_type, datasource_type)
        return backend in self._connections

    def list_tables(self, datasource_type: str) -> List[str]:
        """列出数据源中的表"""
        datasource_type = datasource_type.lower()
        backend = IBIS_BACKEND_MAP.get(datasource_type, datasource_type)

        if backend not in self._connections:
            return []

        try:
            conn = self._connections[backend]
            return conn.list_tables()
        except Exception:
            return []

    def get_schema(self, datasource_type: str, table_name: str) -> Dict[str, str]:
        """获取表的 schema"""
        datasource_type = datasource_type.lower()
        backend = IBIS_BACKEND_MAP.get(datasource_type, datasource_type)

        if backend not in self._connections:
            return {}

        try:
            conn = self._connections[backend]
            schema = conn.table(table_name).schema()
            return {name: str(typ) for name, typ in schema.items()}
        except Exception:
            return {}


# 全局单例（可选，用于共享连接）
_global_adapter: Optional[DataSourceAdapter] = None


def get_global_adapter() -> DataSourceAdapter:
    """获取全局数据源适配器实例"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = DataSourceAdapter()
    return _global_adapter
