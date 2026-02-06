"""MQL Engine - Parse MQL and convert to SQL"""
import re
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.dataset import Dataset
from app.models.datasource import DataSource
from app.models.settings import SystemSetting
from app.models.view import View


# Time function mappings for different SQL dialects
TIME_FUNCTIONS = {
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
    
    # 2. Dimension constraint validation
    await validate_dimensions_constraints(mql, db)
    
    # Get metadata for translation
    metrics = {m.name: m for m in db.query(Metric).all()}
    dimensions = {d.name: d for d in db.query(Dimension).all()}
    datasets = {d.id: d for d in db.query(Dataset).all()}
    views = {v.id: v for v in db.query(View).all()}
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
    
    # Determine dialect (default to mysql)
    dialect = "mysql"
    datasource_ids = []
    
    if datasources:
        dialect = datasources[0].type
        datasource_ids = [ds.id for ds in datasources]
    
    # Parse MQL and build SQL
    sql = translate_mql_to_sql(mql, metrics, dimensions, datasets, views, dialect, time_formats, label_to_format)
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
    if dialect == "mysql":
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


async def validate_dimensions_constraints(mql: Dict[str, Any], db: Session):
    """验证维度约束：查询维度必须在指标允许范围内
    
    逻辑：
    1. 获取MQL中所有指标
    2. 获取每个指标的 analysis_dimensions  
    3. 计算允许维度的交集
    4. 验证请求维度必须在这个交集中
    """
    if not mql.get("metrics") or not mql.get("dimensions"):
        return
    
    # 提取MQL中定义的所有指标
    metric_names = set(mql.get("metrics", []))
    if not metric_names:
        return
    
    metric_ids = []
    metric_lookup = {m.name: m for m in db.query(Metric).all()}
    
    # 从metricDefinitions中获取实际的指标引用
    metric_defs = mql.get("metricDefinitions", {})
    for alias in metric_names:
        defn = metric_defs.get(alias)
        if defn and defn.get("refMetric"):
            # 查找对应的Metric对象
            for metric in metric_lookup.values():
                if metric.name == defn["refMetric"] or metric.measure_column == defn["refMetric"]:
                    metric_ids.append(metric.id)
                    break
    
    if not metric_ids:
        return
    
    # 获取每个指标的允许维度集合
    from sqlalchemy import text
    metric_dim_sets = []
    
    for metric_id in metric_ids:
        metric = db.query(Metric).filter(Metric.id == metric_id).first()
        if metric:
            allowed_ids = set(metric.analysis_dimensions or [])
            metric_dim_sets.append(allowed_ids)
    
    if not metric_dim_sets:
        return
    
    # 计算交集
    if len(metric_dim_sets) == 1:
        common_dim_ids = metric_dim_sets[0]
    else:
        common_dim_ids = set.intersection(*metric_dim_sets)
    
    # 如果没有交集约束，跳过验证
    if not common_dim_ids:
        return
    
    # 获取允许维度的名称集合
    allowed_dims = db.query(Dimension).filter(Dimension.id.in_(common_dim_ids)).all()
    allowed_names = set()
    
    for dim in allowed_dims:
        allowed_names.add(dim.name)
        allowed_names.add(dim.display_name)
        allowed_names.add(dim.physical_column)
    
    # 验证请求维度
    requested_dims = mql.get("dimensions", [])
    invalid_dims = []
    
    for dim_name in requested_dims:
        base_name = dim_name.split("__")[0] if "__" in dim_name else dim_name
        if base_name not in allowed_names:
            invalid_dims.append(dim_name)
    
    if invalid_dims:
        raise ValueError(f"维度约束违反：维度 {invalid_dims} 不在指标允许的范围内")


def build_from_clause(
    mql: Dict[str, Any],
    metrics: Dict[str, Metric],
    dimensions: Dict[str, Dimension],
    datasets: Dict[str, Dataset],
    views: Dict[str, Any],
    dialect: str
) -> str:
    """
    根据MQL中的指标和维度确定使用哪个View或Dataset作为FROM子句
    优先级：
    1. 如果指标关联了View，使用View
    2. 否则如果指标关联了Dataset，使用Dataset
    3. 如果维度关联了View，使用View
    4. 否则使用维度关联的Dataset
    5. 默认使用第一个Dataset
    """
    used_view_id = None
    used_dataset_id = None
    
    # 检查指标关联的View/Dataset
    metric_defs = mql.get("metricDefinitions", {})
    for metric_alias in mql.get("metrics", []):
        defn = metric_defs.get(metric_alias)
        if not defn:
            continue
        ref_metric = defn.get("refMetric")
        
        # 查找指标对象
        for m in metrics.values():
            if m.name == ref_metric or m.measure_column == ref_metric:
                if m.view_id and m.view_id in views:
                    used_view_id = m.view_id
                    break
                elif m.dataset_id and m.dataset_id in datasets:
                    used_dataset_id = m.dataset_id
        if used_view_id:
            break
    
    # 如果没有找到，检查维度关联的View/Dataset
    if not used_view_id and not used_dataset_id:
        for dim_name in mql.get("dimensions", []):
            actual_name = dim_name.split("__")[0] if "__" in dim_name else dim_name
            
            for d in dimensions.values():
                if d.name == actual_name or d.display_name == actual_name:
                    if d.view_id and d.view_id in views:
                        used_view_id = d.view_id
                        break
                    elif d.dataset_id and d.dataset_id in datasets:
                        used_dataset_id = d.dataset_id
            if used_view_id:
                break
    
    # 构建FROM子句
    if used_view_id and used_view_id in views:
        view = views[used_view_id]
        return view.generate_from_clause(datasets, dialect)
    elif used_dataset_id and used_dataset_id in datasets:
        dataset = datasets[used_dataset_id]
        return dataset.physical_name
    elif datasets:
        # 默认使用第一个Dataset
        first_dataset = list(datasets.values())[0]
        return first_dataset.physical_name
    else:
        return "(SELECT 1) AS dummy"


def translate_mql_to_sql(
    mql: Dict[str, Any],
    metrics: Dict[str, Metric],
    dimensions: Dict[str, Dimension],
    datasets: Dict[str, Dataset],
    views: Dict[str, Any] = None,
    dialect: str = "mysql",
    time_formats: Dict[str, str] = None,
    label_to_format: Dict[str, str] = None
) -> str:
    """Translate JSON MQL to SQL"""
    if time_formats is None:
        time_formats = {}
    if label_to_format is None:
        label_to_format = {}
    if views is None:
        views = {}
    
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
    
    # 2. FROM clause - 优先使用View，否则使用Dataset
    from_clause = build_from_clause(mql, metrics, dimensions, datasets, views, dialect)
    sql += f" FROM {from_clause}"
        
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
    
    funcs = TIME_FUNCTIONS.get(dialect, TIME_FUNCTIONS["mysql"])
    
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
