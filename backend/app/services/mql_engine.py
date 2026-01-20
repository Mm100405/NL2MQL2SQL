"""MQL Engine - Parse MQL and convert to SQL"""
import re
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.dataset import Dataset
from app.models.datasource import DataSource
from app.models.settings import SystemSetting


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
        "LAST_N_YEARS({n})": "DATE_SUB(CURDATE(), INTERVAL {n} YEAR)",
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
    
    # Get time format settings
    time_formats_setting = db.query(SystemSetting).filter(SystemSetting.key == "time_formats").first()
    time_formats = {} # suffix -> format (YYYY-MM)
    label_to_format = {} # label (按月) -> format (YYYY-MM)
    if time_formats_setting:
        for f in time_formats_setting.value:
            time_formats[f["suffix"]] = f["name"]
            label_to_format[f["label"]] = f["name"]
    else:
        # Default fallback
        time_formats = {
            "day": "YYYY-MM-DD",
            "month": "YYYY-MM",
            "year": "YYYY",
            "week": "YYYY-WW"
        }
        label_to_format = {
            "按日": "YYYY-MM-DD",
            "按月": "YYYY-MM",
            "按年": "YYYY",
            "按周": "YYYY-WW"
        }
    
    # Determine dialect (default to sqlite for demo)
    dialect = "sqlite"
    datasource_ids = []
    
    if datasources:
        dialect = datasources[0].type
        datasource_ids = [ds.id for ds in datasources]
    
    # Parse MQL and build SQL
    sql = translate_mql_to_sql(mql, metrics, dimensions, datasets, dialect, time_formats, label_to_format)
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


def get_date_format_expr(column: str, fmt: str, dialect: str) -> str:
    """Get SQL expression for date formatting based on dialect"""
    if dialect == "sqlite":
        # SQLite uses strftime
        mapping = {
            "YYYY-MM-DD": f"date({column})",
            "YYYY-MM": f"strftime('%Y-%m', {column})",
            "YYYY": f"strftime('%Y', {column})",
            "YYYY-WW": f"strftime('%Y-%W', {column})"
        }
        return mapping.get(fmt, column)
    elif dialect == "mysql":
        # MySQL uses DATE_FORMAT
        mapping = {
            "YYYY-MM-DD": f"DATE_FORMAT({column}, '%Y-%m-%d')",
            "YYYY-MM": f"DATE_FORMAT({column}, '%Y-%m')",
            "YYYY": f"DATE_FORMAT({column}, '%Y')",
            "YYYY-WW": f"DATE_FORMAT({column}, '%Y-%v')"
        }
        return mapping.get(fmt, column)
    elif dialect == "postgresql":
        # PostgreSQL uses to_char
        mapping = {
            "YYYY-MM-DD": f"to_char({column}, 'YYYY-MM-DD')",
            "YYYY-MM": f"to_char({column}, 'YYYY-MM')",
            "YYYY": f"to_char({column}, 'YYYY')",
            "YYYY-WW": f"to_char({column}, 'IYYY-IW')"
        }
        return mapping.get(fmt, column)
    return column


def process_mql_expression(expr: str, metrics: Dict[str, Metric], dimensions: Dict[str, Dimension], dialect: str, time_formats: Dict[str, str], label_to_format: Dict[str, str], is_where: bool = False) -> str:
    """Helper to replace [field] in expressions with physical columns or formatted expressions"""
    if not expr or expr == "true" or expr == "1=1":
        return expr
        
    processed = expr
    # Find all [field] references
    ref_fields = re.findall(r'\[(.*?)\]', processed)
    for ref_field in ref_fields:
        actual_lookup_name = ref_field
        suffix = None
        if "__" in ref_field:
            parts = ref_field.split("__", 1)
            actual_lookup_name = parts[0]
            suffix = parts[1]
            
        found_obj = None
        # 1. 优先尝试展示名称 (display_name)
        for d in dimensions.values():
            if d.display_name == actual_lookup_name:
                found_obj = d
                break
        
        if not found_obj:
            for m in metrics.values():
                if m.display_name == actual_lookup_name:
                    found_obj = m
                    break
        
        # 2. 尝试逻辑名称 (name)
        if not found_obj:
            found_obj = dimensions.get(actual_lookup_name) or metrics.get(actual_lookup_name)
            
        # 3. 最后尝试物理列名匹配
        if not found_obj:
            for d in dimensions.values():
                if d.physical_column == actual_lookup_name:
                    found_obj = d
                    break
            if not found_obj:
                for m in metrics.values():
                    if m.measure_column == actual_lookup_name:
                        found_obj = m
                        break
        
        if found_obj:
            if isinstance(found_obj, Dimension):
                col_expr = found_obj.physical_column
                # 如果有后缀且是时间维度，尝试应用格式化
                fmt = None
                if suffix and suffix in label_to_format:
                    fmt = label_to_format[suffix]
                elif suffix and suffix in time_formats:
                    fmt = time_formats[suffix]
                
                # 关键修复：如果在 WHERE 子句中 (is_where=True)，我们通常跳过格式化以避免嵌套。
                # 但如果它是直接的等值过滤（下钻分析产生），且没有被 DateTrunc 包装，则必须应用格式化。
                is_wrapped_by_func = is_where and f"DateTrunc([{ref_field}]" in processed
                if fmt and found_obj.dimension_type == "time":
                    if not is_wrapped_by_func:
                        col_expr = get_date_format_expr(col_expr, fmt, dialect)
                
                processed = processed.replace(f"[{ref_field}]", col_expr)
            else: # Metric
                processed = processed.replace(f"[{ref_field}]", found_obj.measure_column or "0")
    
    # Strip remaining brackets if any
    processed = re.sub(r'\[(.*?)\]', r'\1', processed)
    return processed


def translate_mql_to_sql(
    mql: Dict[str, Any],
    metrics: Dict[str, Metric],
    dimensions: Dict[str, Dimension],
    datasets: Dict[str, Dataset],
    dialect: str = "sqlite",
    time_formats: Dict[str, str] = None,
    label_to_format: Dict[str, str] = None
) -> str:
    """Translate JSON MQL to SQL"""
    if time_formats is None:
        time_formats = {}
    if label_to_format is None:
        label_to_format = {}
    
    # 1. SELECT clause
    select_items = []
    group_by_items = []
    
    # Dimensions
    for dim_name in mql.get("dimensions", []):
        actual_lookup_name = dim_name
        suffix = None
        
        # 识别后缀 (如 date__year 或 日期__按月)
        if "__" in dim_name:
            parts = dim_name.split("__", 1)
            actual_lookup_name = parts[0]
            suffix = parts[1]
            
        dim_obj = None
        # 优先按展示名查找
        for d in dimensions.values():
            if d.display_name == actual_lookup_name:
                dim_obj = d
                break
        
        # 次选按逻辑名查找
        if not dim_obj:
            dim_obj = dimensions.get(actual_lookup_name)
        
        # 备选按物理列名查找
        if not dim_obj:
            for d in dimensions.values():
                if d.physical_column == actual_lookup_name:
                    dim_obj = d
                    break
        
        if dim_obj:
            col_expr = dim_obj.physical_column
            
            # --- 格式化推断逻辑 ---
            fmt = None
            
            # 1. 优先尝试从 label_to_format 匹配 (针对 "按月" 等)
            if suffix and suffix in label_to_format:
                fmt = label_to_format[suffix]
            # 2. 次选尝试从 time_formats 匹配 (针对 "year" 等)
            elif suffix and suffix in time_formats:
                fmt = time_formats[suffix]
            
            # 3. 再次：使用元数据默认格式 (如果是时间维度)
            if not fmt and dim_obj.dimension_type == "time" and dim_obj.format_config:
                fmt = dim_obj.format_config.get("default_format")
            
            # 应用格式化
            if fmt and dim_obj.dimension_type == "time":
                col_expr = get_date_format_expr(col_expr, fmt, dialect)
            
            select_items.append(f"{col_expr} AS {dim_name}")
            group_by_items.append(col_expr)
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
    if time_constraint:
        processed_time = process_mql_expression(time_constraint, metrics, dimensions, dialect, time_formats, label_to_format, is_where=True)
        if processed_time and processed_time != "true" and processed_time != "1=1":
            where_parts.append(processed_time)
        
    for filter_expr in mql.get("filters", []):
        processed_filter = process_mql_expression(filter_expr, metrics, dimensions, dialect, time_formats, label_to_format, is_where=True)
        if processed_filter and processed_filter != "true" and processed_filter != "1=1":
            where_parts.append(processed_filter)
        
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
    
    # LAST_N_YEARS(N) pattern
    pattern = r'LAST_N_YEARS\(\s*(\d+)\s*\)'
    for match in re.finditer(pattern, sql):
        n = match.group(1)
        if "LAST_N_YEARS({n})" in funcs:
            replacement = funcs["LAST_N_YEARS({n})"].format(n=n)
            sql = sql.replace(match.group(0), replacement)
    
    # Simple replacements
    simple_funcs = ["TODAY()", "YESTERDAY()", "THIS_WEEK()", "THIS_MONTH()", "THIS_YEAR()"]
    for func in simple_funcs:
        if func in sql:
            sql = sql.replace(func, funcs[func])
    
    return sql
