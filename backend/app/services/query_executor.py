"""Query Executor - Execute SQL queries on data sources"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime, time
from decimal import Decimal
import logging

from app.models.datasource import DataSource, DataSourceType
from app.services.datasource_utils import create_datasource_engine, get_datasource_connection_config, normalize_datasource_type

logger = logging.getLogger(__name__)


def convert_query_value(value: Any) -> Any:
    """递归转换查询结果为 JSON 可序列化值"""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, list):
        return [convert_query_value(item) for item in value]
    if isinstance(value, tuple):
        return [convert_query_value(item) for item in value]
    if isinstance(value, dict):
        return {k: convert_query_value(v) for k, v in value.items()}
    return value


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
        # Return error if no datasource
        logger.error(f"数据源不存在: {datasource_id}")
        return {
            "error": f"数据源不存在: {datasource_id}",
            "success": False
        }
    
    logger.info(f"执行查询: {sql}")
    logger.info(f"数据源: {datasource.name} ({datasource.type})")

    try:
        engine = create_datasource_engine(datasource.type, get_datasource_connection_config(datasource))
        with engine.connect() as conn:
            sql = append_limit_clause(sql, limit, datasource.type)

            logger.debug("连接成功，执行 SQL...")
            result = conn.execute(text(sql))
            columns = list(result.keys())
            data = [list(row) for row in result.fetchall()]

            logger.info(f"查询成功，返回 {len(data)} 行数据")
            logger.debug(f"列名: {columns}")

            # 转换查询结果为 JSON 可序列化值，便于接口和 SSE 返回
            data = convert_query_value(data)

            return {
                "columns": columns,
                "data": data,
                "total_count": len(data),
                "chart_recommendation": recommend_chart_type(columns, data),
                "success": True
            }
    except Exception as e:
        # Return error on exception
        logger.exception(f"查询执行错误: {e}")
        return {
            "error": f"查询执行失败: {str(e)}",
            "success": False
        }


def append_limit_clause(sql: str, limit: int, datasource_type: str) -> str:
    normalized_type = normalize_datasource_type(datasource_type)
    upper_sql = sql.upper()
    if "LIMIT" in upper_sql or "FETCH FIRST" in upper_sql:
        return sql
    if normalized_type == DataSourceType.dameng.value:
        return f"{sql} FETCH FIRST {limit} ROWS ONLY"
    return f"{sql} LIMIT {limit}"


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
