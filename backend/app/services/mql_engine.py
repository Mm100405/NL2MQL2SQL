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


async def mql_to_sql(mql: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Convert MQL to SQL"""
    from app.utils.mql_validator import MQLValidator
    
    # 1. Strong Validation
    validator = MQLValidator(db)
    is_valid, msg = validator.validate_mql(mql)
    if not is_valid:
        raise ValueError(f"MQL Validation Failed: {msg}")
    
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
    sql = replace_time_functions(sql, dialect)
    
    return {
        "sql": sql,
        "datasources": datasource_ids,
        "lineage": {
            "metrics": list(metrics.keys()),
            "dimensions": list(dimensions.keys())
        }
    }


def get_metric_expression(metric_obj: Metric, metrics: Dict[str, Metric]) -> str:
    """Recursively get the SQL expression for a metric"""
    if not metric_obj:
        return "0"
        
    if metric_obj.metric_type == "basic":
        if metric_obj.calculation_method == "expression" and metric_obj.calculation_formula:
            return metric_obj.calculation_formula
        else:
            return f"{metric_obj.aggregation}({metric_obj.measure_column})"
            
    elif metric_obj.metric_type == "derived":
        base_metric = next((m for m in metrics.values() if m.id == metric_obj.base_metric_id), None)
        if base_metric:
            base_expr = get_metric_expression(base_metric, metrics)
            if metric_obj.derivation_type == "yoy":
                return f"{base_expr} * 1.1" # Placeholder
            elif metric_obj.derivation_type == "yoy_growth":
                return f"({base_expr} * 0.15)"
            return base_expr
        return "0"
        
    elif metric_obj.metric_type == "composite":
        expr = metric_obj.calculation_formula or "0"
        # Find all [MetricName] and replace them
        ref_names = re.findall(r'\[(.*?)\]', expr)
        for ref_name in ref_names:
            ref_m = metrics.get(ref_name)
            if ref_m:
                ref_expr = get_metric_expression(ref_m, metrics)
                expr = expr.replace(f"[{ref_name}]", f"({ref_expr})")
        return expr
        
    return "0"


def translate_mql_to_sql(
    mql: Dict[str, Any],
    metrics: Dict[str, Metric],
    dimensions: Dict[str, Dimension],
    datasets: Dict[str, Dataset],
    dialect: str = "sqlite"
) -> str:
    """Translate JSON MQL to SQL"""
    
    # 1. SELECT clause
    select_items = []
    group_by_items = []
    
    # Dimensions
    for dim_name in mql.get("dimensions", []):
        dim_obj = dimensions.get(dim_name)
        if not dim_obj:
            # Try to find by display name or physical column
            for d in dimensions.values():
                if d.display_name == dim_name or d.physical_column == dim_name:
                    dim_obj = d
                    break
        
        if dim_obj:
            select_items.append(f"{dim_obj.physical_column} AS {dim_name}")
            group_by_items.append(dim_obj.physical_column)
        else:
            select_items.append(f"{dim_name} AS {dim_name}")
            group_by_items.append(dim_name)
            
    # Metrics
    metric_defs = mql.get("metricDefinitions", {})
    for metric_alias in mql.get("metrics", []):
        defn = metric_defs.get(metric_alias)
        if not defn:
            continue
            
        ref_metric = defn.get("refMetric")
        indirections = defn.get("indirections", [])
        
        metric_obj = None
        for m in metrics.values():
            if m.name == ref_metric or m.measure_column == ref_metric:
                metric_obj = m
                break
        
        if metric_obj:
            expr = get_metric_expression(metric_obj, metrics)
            
            # Simple YOY logic from existing code (if requested in MQL indirections)
            if "sameperiod__yoy__growth" in indirections:
                select_items.append(f"({expr}) * 0.15 AS {metric_alias}") # Demo growth
            else:
                select_items.append(f"{expr} AS {metric_alias}")
        else:
            select_items.append(f"0 AS {metric_alias}")

    if not select_items:
        return "SELECT 1"

    sql = "SELECT " + ", ".join(select_items)
    
    # 2. FROM clause
    first_dataset = list(datasets.values())[0] if datasets else None
    if first_dataset:
        sql += f" FROM {first_dataset.physical_name}"
    else:
        sql += " FROM (SELECT 1) AS dummy"
        
    # 3. WHERE clause
    where_parts = []
    time_constraint = mql.get("timeConstraint")
    if time_constraint and time_constraint != "true":
        # Replace [field_name] with actual physical column name using regex for exact matches
        processed_time = time_constraint
        
        # Find all [field] references
        ref_fields = re.findall(r'\[(.*?)\]', processed_time)
        for ref_field in ref_fields:
            # 1. Try dimension name
            dim_obj = dimensions.get(ref_field)
            if dim_obj:
                processed_time = processed_time.replace(f"[{ref_field}]", dim_obj.physical_column)
                continue
            
            # 2. Try metric name
            met_obj = metrics.get(ref_field)
            if met_obj and met_obj.measure_column:
                processed_time = processed_time.replace(f"[{ref_field}]", met_obj.measure_column)
                continue
                
            # 3. Try fallback (look through all for name or physical_column)
            found = False
            for d in dimensions.values():
                if d.name == ref_field or d.physical_column == ref_field:
                    processed_time = processed_time.replace(f"[{ref_field}]", d.physical_column)
                    found = True
                    break
            if found: continue
            
            for m in metrics.values():
                if (m.name == ref_field or m.measure_column == ref_field) and m.measure_column:
                    processed_time = processed_time.replace(f"[{ref_field}]", m.measure_column)
                    found = True
                    break
        
        # Strip remaining brackets if any
        processed_time = re.sub(r'\[(.*?)\]', r'\1', processed_time)
        where_parts.append(processed_time)
        
    for filter_expr in mql.get("filters", []):
        where_parts.append(filter_expr)
        
    if where_parts:
        sql += " WHERE " + " AND ".join(where_parts)
        
    # 4. GROUP BY clause
    if group_by_items:
        sql += " GROUP BY " + ", ".join(group_by_items)
        
    # 5. LIMIT
    limit = mql.get("limit", 1000)
    sql += f" LIMIT {limit}"
    
    return sql


def replace_time_functions(sql: str, dialect: str) -> str:
    """Replace MQL time functions with SQL dialect-specific functions"""
    
    funcs = TIME_FUNCTIONS.get(dialect, TIME_FUNCTIONS["sqlite"])
    
    # 1. DateTrunc(col, 'MONTH/YEAR/DAY')
    if dialect == "mysql":
        sql = re.sub(r"DateTrunc\((.*?), 'MONTH'\)", r"DATE_FORMAT(\1, '%Y-%m-01')", sql, flags=re.IGNORECASE)
        sql = re.sub(r"DateTrunc\((.*?), 'YEAR'\)", r"DATE_FORMAT(\1, '%Y-01-01')", sql, flags=re.IGNORECASE)
        sql = re.sub(r"DateTrunc\((.*?), 'DAY'\)", r"DATE(\1)", sql, flags=re.IGNORECASE)
        # AddMonths(date, n)
        sql = re.sub(r"AddMonths\((.*?), (.*?)\)", r"DATE_ADD(\1, INTERVAL \2 MONTH)", sql, flags=re.IGNORECASE)
        # CurrentDate()
        sql = sql.replace("CurrentDate()", "CURDATE()")
    elif dialect == "postgresql":
        sql = re.sub(r"DateTrunc\((.*?), '(.*?)'\)", r"date_trunc('\2', \1)", sql, flags=re.IGNORECASE)
        sql = re.sub(r"AddMonths\((.*?), (.*?)\)", r"\1 + INTERVAL '\2 months'", sql, flags=re.IGNORECASE)
        sql = sql.replace("CurrentDate()", "CURRENT_DATE")
    elif dialect == "sqlite":
        sql = re.sub(r"DateTrunc\((.*?), 'MONTH'\)", r"strftime('%Y-%m-01', \1)", sql, flags=re.IGNORECASE)
        sql = re.sub(r"DateTrunc\((.*?), 'YEAR'\)", r"strftime('%Y-01-01', \1)", sql, flags=re.IGNORECASE)
        sql = re.sub(r"DateTrunc\((.*?), 'DAY'\)", r"date(\1)", sql, flags=re.IGNORECASE)
        sql = re.sub(r"AddMonths\((.*?), (.*?)\)", r"date(\1, '\2 months')", sql, flags=re.IGNORECASE)
        sql = sql.replace("CurrentDate()", "date('now')")

    # 2. TODAY(-N) pattern
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
