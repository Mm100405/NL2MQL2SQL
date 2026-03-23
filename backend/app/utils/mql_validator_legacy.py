"""
Legacy MQL Validator
====================
This file contains the old MQLValidator class for backward compatibility.
The new modular validators are in: app/utils/mql_validator/

Usage:
    from app.utils.mql_validator import MQLValidator
    validator = MQLValidator(db_session)
    is_valid, msg = validator.validate_mql(mql)
"""

import re
from typing import Dict, List, Tuple


class MQLValidator:
    """Legacy MQL Validator for backward compatibility"""

    VALID_TIME_FUNCTIONS = {
        'DateTrunc', 'AddMonths', 'CurrentDate', 'TODAY', 
        'LAST_N_DAYS', 'LAST_N_MONTHS', 'LAST_N_YEARS', 'BETWEEN', 'DateAdd'
    }
    
    VALID_FILTER_OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'NOT IN', 'LIKE', 'IS NULL', 'IS NOT NULL']
    
    VALID_AGGREGATIONS = {
        'SUM', 'COUNT', 'AVG', 'MIN', 'MAX', 
        'SUM_IF', 'COUNT_IF', 'AVG_IF', 'MIN_IF', 'MAX_IF',
        'SUM_DISTINCT', 'COUNT_DISTINCT', 'AVG_DISTINCT'
    }
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def validate_mql(self, mql: Dict) -> Tuple[bool, str]:
        """
        Deep validate MQL object against metadata
        """
        from app.models.metric import Metric
        from app.models.dimension import Dimension
        from app.models.settings import SystemSetting
        import json

        # 获取全局时间格式配置
        time_formats_setting = self.db_session.query(SystemSetting).filter(SystemSetting.key == "time_formats").first()
        time_formats = []
        if time_formats_setting:
            val = time_formats_setting.value
            if isinstance(val, str):
                try:
                    time_formats = json.loads(val)
                except:
                    pass
            elif isinstance(val, list):
                time_formats = val
        
        if not time_formats:
            time_formats = [
                {"name": "YYYY-MM-DD", "label": "按日", "suffix": "day"},
                {"name": "YYYY-MM", "label": "按月", "suffix": "month"},
                {"name": "YYYY", "label": "按年", "suffix": "year"},
                {"name": "YYYY-WW", "label": "按周", "suffix": "week"}
            ]
        valid_labels = {f["label"] for f in time_formats}
            
        # 0. Validate queryResultType
        result_type = mql.get("queryResultType", "DATA")
        if result_type not in ["DATA", "CHART"]:
            return False, f"Invalid queryResultType '{result_type}'. Must be 'DATA' or 'CHART'."
        
        # 1. Validate Dimensions
        dimensions = mql.get("dimensions", [])
        dim_configs = mql.get("dimensionConfigs", {})
        
        for dim_name in dimensions:
            actual_lookup_name = dim_name
            label = None
            if "__" in dim_name:
                parts = dim_name.split("__", 1)
                actual_lookup_name = parts[0]
                label = parts[1]
                
            dim_obj = self.db_session.query(Dimension).filter(
                (Dimension.name == actual_lookup_name) | 
                (Dimension.physical_column == actual_lookup_name) |
                (Dimension.display_name == actual_lookup_name)
            ).first()

            if not dim_obj:
                return False, f"维度 '{actual_lookup_name}' 在元数据中不存在，请从可用列表中选择逻辑名。"
            
            # 如果带有标签，校验标签是否合法且维度是否为时间类型
            if label:
                if label not in valid_labels:
                    return False, f"维度 '{dim_name}' 的后缀标签 '{label}' 不合法。有效标签: {list(valid_labels)}"
                
                # 兼容 Enum 或 String
                d_type = str(dim_obj.dimension_type).lower() if dim_obj.dimension_type else ""
                if hasattr(dim_obj.dimension_type, 'value'):
                    d_type = dim_obj.dimension_type.value
                d_data_type = str(dim_obj.data_type).lower() if dim_obj.data_type else ""
                
                is_time_dim = (d_type == "time") or (d_data_type in ["date", "datetime", "timestamp"])
                if not is_time_dim:
                    return False, f"非时间维度 '{actual_lookup_name}' 不能使用时间格式化后缀 '{label}'。"
            
            # Validate dimensionConfigs if present (Optional fallback)
            if actual_lookup_name in dim_configs:
                config = dim_configs[actual_lookup_name]
                if not isinstance(config, dict):
                    return False, f"维度配置 '{dim_name}' 格式错误，应为 JSON 对象。"
                
                fmt = config.get("format")
                if fmt and dim_obj.dimension_type == "time":
                    # Optional: validate format against metadata options
                    if dim_obj.format_config and "options" in dim_obj.format_config:
                        allowed_options = dim_obj.format_config["options"]
                        if fmt not in allowed_options:
                            return False, f"时间维度 '{dim_name}' 不支持格式 '{fmt}'。可选：{allowed_options}"
        
        # 2. Validate Metrics
        metric_aliases = mql.get("metrics", [])
        metric_defs = mql.get("metricDefinitions", {})
            
        for alias in metric_aliases:
            defn = metric_defs.get(alias)
            if not defn:
                return False, f"指标别名 '{alias}' 缺少定义。"
                
            ref_metric = defn.get("refMetric")
            metric_obj = self.db_session.query(Metric).filter(
                (Metric.name == ref_metric) | (Metric.measure_column == ref_metric)
            ).first()
            
            if not metric_obj:
                return False, f"基础指标 '{ref_metric}' 不存在，请使用指标逻辑名。"
        
        # 3. Validate timeConstraint
        time_constraint = mql.get("timeConstraint")
        if time_constraint and time_constraint != "true":
            # 3.1 Check for unauthorized functions or syntax errors
            # Find all function calls Word(...)
            found_funcs = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', time_constraint)
            for func in found_funcs:
                if func not in self.VALID_TIME_FUNCTIONS:
                    return False, f"使用了不支持的时间函数 '{func}'。仅允许: {', '.join(self.VALID_TIME_FUNCTIONS)}"
                        
            # 3.2 Extract fields from [field] pattern and validate
            # Brackets should ONLY contain field names, not functions
            fields = re.findall(r'\[(.*?)\]', time_constraint)
            for field in fields:
                if field in self.VALID_TIME_FUNCTIONS:
                    return False, f"语法错误：函数 '{field}' 不应该被中括号 [] 包裹。只有元数据字段（如 [date]）才需要包裹。"
                
                actual_lookup_name = field
                label = None
                if "__" in field:
                    parts = field.split("__", 1)
                    actual_lookup_name = parts[0]
                    label = parts[1]
                            
                metric_exists = self.db_session.query(Metric).filter(
                            (Metric.display_name == actual_lookup_name) | 
                            (Metric.name == actual_lookup_name) | 
                            (Metric.measure_column == actual_lookup_name)
                         ).first()
                
                dim_obj = self.db_session.query(Dimension).filter(
                            (Dimension.display_name == actual_lookup_name) |
                            (Dimension.name == actual_lookup_name) | 
                            (Dimension.physical_column == actual_lookup_name)
                         ).first()
                
                if not (metric_exists or dim_obj):
                    return False, f"timeConstraint 中引用的字段 '[{field}]' 在元数据中不存在，请确保使用展示名称或逻辑名。"
                
                # 如果是带有后缀的时间维度
                if label:
                    if label not in valid_labels:
                        return False, f"timeConstraint 中字段 '[{field}]' 的后缀标签 '{label}' 不合法。有效标签: {list(valid_labels)}"
                    
                    if dim_obj:
                        d_type = str(dim_obj.dimension_type).lower() if dim_obj.dimension_type else ""
                        if hasattr(dim_obj.dimension_type, 'value'):
                            d_type = dim_obj.dimension_type.value
                        d_data_type = str(dim_obj.data_type).lower() if dim_obj.data_type else ""
                        
                        is_time_dim = (d_type == "time") or (d_data_type in ["date", "datetime", "timestamp"])
                        if not is_time_dim:
                            return False, f"timeConstraint 中非时间维度 '[{actual_lookup_name}]' 不能使用时间格式化后缀 '{label}'。"
        
        # 4. Validate filters
        filters = mql.get("filters", [])
        if filters:
            is_valid, msg = self.validate_filters(filters)
            if not is_valid:
                return False, msg
        
        return True, "MQL 合规性校验通过"
    
    def validate_filters(self, filters: List[str]) -> Tuple[bool, str]:
        """
        验证 filters 字段
        
        规则：
        1. 字段名必须用 [中括号] 包裹
        2. 字段必须在元数据中存在（维度或视图字段）
        3. 操作符必须合法
        4. 如果字段配置了字典值，值必须在可选范围内
        """
        from app.models.dimension import Dimension
        from app.models.view import View
        from app.models.field_dict import FieldDictionary
        from app.models.settings import SystemSetting
        import json

        # 获取全局时间格式配置
        time_formats_setting = self.db_session.query(SystemSetting).filter(SystemSetting.key == "time_formats").first()
        time_formats = []
        if time_formats_setting:
            val = time_formats_setting.value
            if isinstance(val, str):
                try:
                    time_formats = json.loads(val)
                except:
                    pass
            elif isinstance(val, list):
                time_formats = val

        if not time_formats:
            time_formats = [
                {"name": "YYYY-MM-DD", "label": "按日", "suffix": "day"},
                {"name": "YYYY-MM", "label": "按月", "suffix": "month"},
                {"name": "YYYY", "label": "按年", "suffix": "year"},
                {"name": "YYYY-WW", "label": "按周", "suffix": "week"}
            ]
        valid_labels = {f["label"] for f in time_formats}

        if not filters:
            return True, ""
        
        for filter_expr in filters:
            # 1. 检查字段引用格式 [field]
            fields = re.findall(r'\[(.*?)\]', filter_expr)
            if not fields:
                return False, f"过滤条件 '{filter_expr}' 缺少字段引用，应使用 [字段名] 格式"
            
            for field in fields:
                actual_lookup_name = field
                label = None

                # 处理时间维度后缀 (如 创建时间__按年)
                if "__" in field:
                    parts = field.split("__", 1)
                    actual_lookup_name = parts[0]
                    label = parts[1]

                # 2. 验证字段是否存在（先查维度，再查视图字段）
                found = False
                dim_obj = None

                # 查维度
                dim_obj = self.db_session.query(Dimension).filter(
                    (Dimension.display_name == actual_lookup_name) |
                    (Dimension.name == actual_lookup_name) |
                    (Dimension.physical_column == actual_lookup_name)
                ).first()

                if dim_obj:
                    found = True
                    field_type = "dimension"

                    # 如果有后缀标签，验证是否合法
                    if label:
                        if label not in valid_labels:
                            return False, f"过滤条件中字段 '[{field}]' 的后缀标签 '{label}' 不合法。有效标签: {list(valid_labels)}"

                        # 验证是否为时间维度
                        d_type = str(dim_obj.dimension_type).lower() if dim_obj.dimension_type else ""
                        if hasattr(dim_obj.dimension_type, 'value'):
                            d_type = dim_obj.dimension_type.value
                        d_data_type = str(dim_obj.data_type).lower() if dim_obj.data_type else ""

                        is_time_dim = (d_type == "time") or (d_data_type in ["date", "datetime", "timestamp"])
                        if not is_time_dim:
                            return False, f"过滤条件中非时间维度 '[{actual_lookup_name}]' 不能使用时间格式化后缀 '{label}'。"
                else:
                    # 尝试从视图字段中查找
                    # 获取所有视图，查找包含该字段的视图
                    views = self.db_session.query(View).all()
                    for view in views:
                        if view.columns:
                            for col in view.columns:
                                if col.get("name") == actual_lookup_name or col.get("display_name") == actual_lookup_name:
                                    found = True
                                    field_type = "view_field"
                                    break
                        if found:
                            break

                if not found:
                    return False, f"过滤条件中的字段 '[{field}]' 在元数据中不存在"
                
                # 3. 检查操作符是否合法
                expr_upper = filter_expr.upper()
                has_valid_op = any(op in expr_upper for op in self.VALID_FILTER_OPERATORS)
                if not has_valid_op:
                    return False, f"过滤条件 '{filter_expr}' 缺少有效的比较操作符。支持: {', '.join(self.VALID_FILTER_OPERATORS)}"
                
                # 4. 可选：如果字段配置了字典值，验证值是否在可选范围内
                # TODO: 这部分可以在后续增强，需要从视图字段配置中获取字典并验证值
                
        return True, ""
