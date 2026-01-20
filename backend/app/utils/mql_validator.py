"""MQL Formula Validator"""
import re
from typing import Dict, List, Tuple


class MQLValidator:
    """Validates MQL formulas"""
    
    VALID_AGGREGATIONS = {'SUM', 'COUNT', 'AVG', 'MAX', 'MIN', 'COUNT_DISTINCT'}
    VALID_OPERATORS = {'+', '-', '*', '/', '(', ')'}
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def validate_mql(self, mql: Dict) -> Tuple[bool, str]:
        """
        Deep validate MQL object against metadata
        """
        from app.models.metric import Metric
        from app.models.dimension import Dimension
            
        # 0. Validate queryResultType
        result_type = mql.get("queryResultType", "DATA")
        if result_type not in ["DATA", "CHART"]:
            return False, f"Invalid queryResultType '{result_type}'. Must be 'DATA' or 'CHART'."
    
        # 1. Validate Dimensions
        dimensions = mql.get("dimensions", [])
        for dim_name in dimensions:
            dim_obj = self.db_session.query(Dimension).filter(
                (Dimension.name == dim_name) | 
                (Dimension.physical_column == dim_name)
            ).first()
            if not dim_obj:
                dim_obj = self.db_session.query(Dimension).filter(Dimension.display_name == dim_name).first()
                if not dim_obj:
                    return False, f"维度 '{dim_name}' 在元数据中不存在，请从可用列表中选择逻辑名。"
            
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
                # 3.1 Check supported functions
                supported_funcs = ['DateTrunc', 'AddMonths', 'CurrentDate', 'TODAY', 'LAST_N_DAYS', 'LAST_N_MONTHS', 'BETWEEN']
                # Simple check for DateAdd which is explicitly forbidden
                if 'DateAdd' in time_constraint:
                    return False, "禁止使用 DateAdd 函数，请使用 AddMonths 或 DateTrunc。"
                    
                # 3.2 Extract fields from [field] pattern
                fields = re.findall(r'\[(.*?)\]', time_constraint)
                for field in fields:
                    exists = self.db_session.query(Metric).filter(
                                (Metric.name == field) | (Metric.measure_column == field)
                             ).first() or \
                             self.db_session.query(Dimension).filter(
                                (Dimension.name == field) | (Dimension.physical_column == field)
                             ).first()
                    if not exists:
                        return False, f"timeConstraint 中引用的字段 '[{field}]' 不存在。"
    
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
