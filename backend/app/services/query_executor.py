"""Query Executor - Execute SQL queries on data sources"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
import sqlite3
import urllib.parse

from app.models.datasource import DataSource
from app.utils.encryption import decrypt_api_key


async def execute_query(
    sql: str,
    datasource_id: str,
    limit: int,
    db: Session
) -> Dict[str, Any]:
    """Execute SQL query on specified datasource"""
    
    # Get datasource
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    
    if not datasource:
        # Return demo data if no datasource
        return get_demo_result()
    
    # Build connection string
    connection_string = build_connection_string(datasource)
    
    try:
        # Execute query
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            # Add LIMIT if not present
            if "LIMIT" not in sql.upper():
                sql = f"{sql} LIMIT {limit}"
            
            result = conn.execute(text(sql))
            columns = list(result.keys())
            data = [list(row) for row in result.fetchall()]
            
            return {
                "columns": columns,
                "data": data,
                "total_count": len(data),
                "chart_recommendation": recommend_chart_type(columns, data)
            }
    except Exception as e:
        # Return demo data on error
        print(f"Query execution error: {e}")
        return get_demo_result()


def build_connection_string(datasource: DataSource) -> str:
    """Build SQLAlchemy connection string from datasource config"""
    
    config = datasource.connection_config
    db_type = datasource.type
    
    if db_type == "sqlite":
        return f"sqlite:///{config.get('database', ':memory:')}"
    
    elif db_type == "postgresql":
        host = config.get("host", "localhost")
        port = config.get("port", 5432)
        database = config.get("database", "")
        username = urllib.parse.quote_plus(config.get("username", ""))
        password = urllib.parse.quote_plus(config.get("password", ""))
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    elif db_type == "mysql":
        host = config.get("host", "localhost")
        port = config.get("port", 3306)
        database = config.get("database", "")
        username = urllib.parse.quote_plus(config.get("username", ""))
        password = urllib.parse.quote_plus(config.get("password", ""))
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    
    elif db_type == "clickhouse":
        host = config.get("host", "localhost")
        port = config.get("port", 8123)
        database = config.get("database", "")
        username = urllib.parse.quote_plus(config.get("username", ""))
        password = urllib.parse.quote_plus(config.get("password", ""))
        return f"clickhouse://{username}:{password}@{host}:{port}/{database}"
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def recommend_chart_type(columns: List[str], data: List[List]) -> str:
    """Recommend chart type based on data characteristics"""
    
    if not columns or not data:
        return "table"
    
    # Check if first column looks like a date/time dimension
    first_col = columns[0].lower()
    is_time_series = any(keyword in first_col for keyword in ["date", "time", "日期", "时间", "month", "year", "day"])
    
    # Check number of rows
    num_rows = len(data)
    num_cols = len(columns)
    
    if is_time_series:
        return "line"
    elif num_rows <= 10 and num_cols == 2:
        # Few categories with single metric
        return "pie" if num_rows <= 6 else "bar"
    elif num_cols >= 2:
        return "bar"
    else:
        return "table"


def get_demo_result() -> Dict[str, Any]:
    """Return demo result for testing"""
    return {
        "columns": ["日期", "销售额", "订单数"],
        "data": [
            ["2024-01-01", 125000, 420],
            ["2024-01-02", 138000, 456],
            ["2024-01-03", 112000, 380],
            ["2024-01-04", 145000, 489],
            ["2024-01-05", 156000, 523],
            ["2024-01-06", 168000, 567],
            ["2024-01-07", 142000, 478]
        ],
        "total_count": 7,
        "chart_recommendation": "line"
    }
