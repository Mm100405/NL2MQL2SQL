"""MQL Formula Validator"""
import re
from typing import Dict, List, Tuple


class MQLValidator:
    """Validates MQL formulas"""
    
    VALID_TIME_FUNCTIONS = {
        'DateTrunc', 'AddMonths', 'CurrentDate', 'TODAY', 
        'LAST_N_DAYS', 'LAST_N_MONTHS', 'LAST_N_YEARS', 'BETWEEN', 'DateAdd'
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
        
        return True, "MQL 合规性校验通过"
    
    def validate(self, formula: str) -> Tuple[bool, str]:
        """
        Validate MQL formula
        Returns: (is_valid, message)
        """
        if not formula or not formula.strip():
            return False, "Formula cannot be empty"
        
        formula = formula.strip()
        
        # Check balanced parentheses
        if not self._check_balanced_parentheses(formula):
            return False, "Unbalanced parentheses"
        
        # Check aggregation function syntax
        agg_valid, agg_msg = self._validate_aggregations(formula)
        if not agg_valid:
            return False, agg_msg
        
        # Check operators
        op_valid, op_msg = self._validate_operators(formula)
        if not op_valid:
            return False, op_msg
        
        # Check for common syntax errors
        if '//' in formula or '**' in formula:
            return False, "Invalid operator syntax"
        
        return True, "Formula is valid"
    
    def _check_balanced_parentheses(self, formula: str) -> bool:
        """Check if parentheses are balanced"""
        count = 0
        for char in formula:
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1
            if count < 0:
                return False
        return count == 0
    
    def _validate_aggregations(self, formula: str) -> Tuple[bool, str]:
        """Validate aggregation functions"""
        # Find all aggregation function calls
        pattern = r'([A-Z_]+)\s*\('
        matches = re.findall(pattern, formula)
        
        for func in matches:
            if func not in self.VALID_AGGREGATIONS:
                return False, f"Invalid aggregation function: {func}"
        
        # Check that aggregations have closing parentheses
        for agg in self.VALID_AGGREGATIONS:
            if agg in formula:
                if f"{agg}(" not in formula.replace(" ", ""):
                    return False, f"Aggregation {agg} must be followed by parentheses"
        
        return True, ""
    
    def _validate_operators(self, formula: str) -> Tuple[bool, str]:
        """Validate mathematical operators"""
        # Remove valid parts (aggregations, numbers, parentheses, metric names)
        temp = re.sub(r'[A-Z_]+\([^)]+\)', '', formula)
        temp = re.sub(r'[a-zA-Z_][a-zA-Z0-9_]*', '', temp)
        temp = re.sub(r'\d+\.?\d*', '', temp)
        temp = re.sub(r'[\s()+\-*/]', '', temp)
        
        if temp:
            return False, f"Invalid characters in formula: {temp}"
        
        return True, ""
    
    def extract_referenced_metrics(self, formula: str) -> List[str]:
        """Extract metric names referenced in the formula"""
        # Remove aggregation functions
        temp = formula
        for agg in self.VALID_AGGREGATIONS:
            temp = re.sub(f'{agg}\\s*\\([^)]+\\)', '', temp)
        
        # Find remaining identifiers (metric names)
        pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
        metrics = re.findall(pattern, temp)
        
        return list(set(metrics))
