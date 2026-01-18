"""MQL Engine - Parse MQL and convert to SQL"""
import re
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.dataset import Dataset
from app.models.datasource import DataSource


# Time function mappings for different SQL dialects
TIME_FUNCTIONS = {
    "sqlite": {
        "TODAY()": "date('now')",
        "TODAY(-{n})": "date('now', '-{n} days')",
        "YESTERDAY()": "date('now', '-1 day')",
        "LAST_N_DAYS({n})": "date('now', '-{n} days')",
        "LAST_N_MONTHS({n})": "date('now', '-{n} months')",
        "THIS_WEEK()": "date('now', 'weekday 0', '-7 days')",
        "THIS_MONTH()": "date('now', 'start of month')",
        "THIS_YEAR()": "date('now', 'start of year')"
    },
    "postgresql": {
        "TODAY()": "CURRENT_DATE",
        "TODAY(-{n})": "CURRENT_DATE - INTERVAL '{n} days'",
        "YESTERDAY()": "CURRENT_DATE - INTERVAL '1 day'",
        "LAST_N_DAYS({n})": "CURRENT_DATE - INTERVAL '{n} days'",
        "LAST_N_MONTHS({n})": "CURRENT_DATE - INTERVAL '{n} months'",
        "THIS_WEEK()": "date_trunc('week', CURRENT_DATE)",
        "THIS_MONTH()": "date_trunc('month', CURRENT_DATE)",
        "THIS_YEAR()": "date_trunc('year', CURRENT_DATE)"
    },
    "mysql": {
        "TODAY()": "CURDATE()",
        "TODAY(-{n})": "DATE_SUB(CURDATE(), INTERVAL {n} DAY)",
        "YESTERDAY()": "DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
        "LAST_N_DAYS({n})": "DATE_SUB(CURDATE(), INTERVAL {n} DAY)",
        "LAST_N_MONTHS({n})": "DATE_SUB(CURDATE(), INTERVAL {n} MONTH)",
        "THIS_WEEK()": "DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)",
        "THIS_MONTH()": "DATE_FORMAT(CURDATE(), '%Y-%m-01')",
        "THIS_YEAR()": "DATE_FORMAT(CURDATE(), '%Y-01-01')"
    }
}


async def mql_to_sql(mql: str, db: Session) -> Dict[str, Any]:
    """Convert MQL to SQL"""
    
    # Get metadata for translation
    metrics = {m.name: m for m in db.query(Metric).all()}
    dimensions = {d.name: d for d in db.query(Dimension).all()}
    datasets = {d.id: d for d in db.query(Dataset).all()}
    datasources = db.query(DataSource).all()
    
    # Determine dialect (default to sqlite for demo)
    dialect = "sqlite"
    datasource_ids = []
    
    if datasources:
        dialect = datasources[0].type
        datasource_ids = [ds.id for ds in datasources]
    
    # Parse MQL and build SQL
    sql = translate_mql_to_sql(mql, metrics, dimensions, datasets, dialect)
    
    return {
        "sql": sql,
        "datasources": datasource_ids,
        "lineage": {
            "metrics": list(metrics.keys()),
            "dimensions": list(dimensions.keys())
        }
    }


def translate_mql_to_sql(
    mql: str,
    metrics: Dict[str, Metric],
    dimensions: Dict[str, Dimension],
    datasets: Dict[str, Dataset],
    dialect: str = "sqlite"
) -> str:
    """Translate MQL to SQL with proper field mappings"""
    
    sql = mql
    
    # Replace time functions
    sql = replace_time_functions(sql, dialect)
    
    # Replace metric names with physical expressions
    for name, metric in metrics.items():
        if metric.aggregation and metric.measure_column:
            physical_expr = f"{metric.aggregation}({metric.measure_column})"
            # Handle both with and without aggregation in MQL
            sql = re.sub(
                rf'\b{metric.aggregation}\({re.escape(name)}\)',
                physical_expr,
                sql,
                flags=re.IGNORECASE
            )
            sql = re.sub(
                rf'\b{re.escape(name)}\b(?!\s*\()',
                physical_expr,
                sql
            )
    
    # Replace dimension names with physical columns
    for name, dimension in dimensions.items():
        sql = re.sub(
            rf'\b{re.escape(name)}\b',
            dimension.physical_column,
            sql
        )
    
    # Add FROM clause if missing
    if 'FROM' not in sql.upper() and datasets:
        # Use first dataset as default
        first_dataset = list(datasets.values())[0] if datasets else None
        if first_dataset:
            table_name = first_dataset.physical_name
            # Insert FROM clause after SELECT ... 
            select_match = re.search(r'(SELECT\s+.+?)(?=\s+WHERE|\s+GROUP|\s+ORDER|\s+LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
            if select_match:
                sql = sql[:select_match.end()] + f" FROM {table_name}" + sql[select_match.end():]
    
    return sql


def replace_time_functions(sql: str, dialect: str) -> str:
    """Replace MQL time functions with SQL dialect-specific functions"""
    
    funcs = TIME_FUNCTIONS.get(dialect, TIME_FUNCTIONS["sqlite"])
    
    # TODAY(-N) pattern
    pattern = r'TODAY\(\s*-\s*(\d+)\s*\)'
    for match in re.finditer(pattern, sql):
        n = match.group(1)
        replacement = funcs["TODAY(-{n})"].format(n=n)
        sql = sql.replace(match.group(0), replacement)
    
    # LAST_N_DAYS(N) pattern
    pattern = r'LAST_N_DAYS\(\s*(\d+)\s*\)'
    for match in re.finditer(pattern, sql):
        n = match.group(1)
        replacement = funcs["LAST_N_DAYS({n})"].format(n=n)
        sql = sql.replace(match.group(0), replacement)
    
    # LAST_N_MONTHS(N) pattern
    pattern = r'LAST_N_MONTHS\(\s*(\d+)\s*\)'
    for match in re.finditer(pattern, sql):
        n = match.group(1)
        replacement = funcs["LAST_N_MONTHS({n})"].format(n=n)
        sql = sql.replace(match.group(0), replacement)
    
    # Simple replacements
    simple_funcs = ["TODAY()", "YESTERDAY()", "THIS_WEEK()", "THIS_MONTH()", "THIS_YEAR()"]
    for func in simple_funcs:
        if func in sql:
            sql = sql.replace(func, funcs[func])
    
    return sql
