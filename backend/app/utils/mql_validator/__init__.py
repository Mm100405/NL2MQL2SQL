"""
mql_validator - 模块化 MQL 校验器

各校验器负责验证 MQL 的不同字段：
- MetricValidator: metrics, metricDefinitions
- DimensionValidator: dimensions
- FilterValidator: filters
- HavingValidator: having
- OrderByValidator: orderBy
- DistinctValidator: distinct
- LimitValidator: limit
- WindowFuncValidator: windowFunctions
- UnionValidator: union
- CTEValidator: cte
- TimeConstraintValidator: timeConstraint
- CompositeValidator: 组合所有校验器

设计原则：
1. 每个校验器独立，可单独使用
2. 错误信息包含 severity、code、message、suggestion
3. 支持 WARNING（容忍）和 ERROR（必须修正）两种级别
"""

from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationError,
    ValidationResult,
)
from app.utils.mql_validator.metric_validator import MetricValidator
from app.utils.mql_validator.dimension_validator import DimensionValidator
from app.utils.mql_validator.filter_validator import FilterValidator
from app.utils.mql_validator.having_validator import HavingValidator
from app.utils.mql_validator.orderby_validator import OrderByValidator
from app.utils.mql_validator.distinct_validator import DistinctValidator
from app.utils.mql_validator.limit_validator import LimitValidator
from app.utils.mql_validator.window_func_validator import WindowFuncValidator
from app.utils.mql_validator.union_validator import UnionValidator
from app.utils.mql_validator.cte_validator import CTEValidator
from app.utils.mql_validator.time_constraint_validator import TimeConstraintValidator
from app.utils.mql_validator.composite_validator import MQLCompositeValidator


class MQLValidator:
    VALID_AGGREGATIONS = {"SUM", "COUNT", "AVG", "MAX", "MIN", "COUNT_DISTINCT"}

    def __init__(self, db_session):
        self.db_session = db_session

    def validate(self, formula: str):
        if not formula or not formula.strip():
            return False, "Formula cannot be empty"

        formula = formula.strip()
        if not self._check_balanced_parentheses(formula):
            return False, "Unbalanced parentheses"

        agg_valid, agg_msg = self._validate_aggregations(formula)
        if not agg_valid:
            return False, agg_msg

        op_valid, op_msg = self._validate_operators(formula)
        if not op_valid:
            return False, op_msg

        if "//" in formula or "**" in formula:
            return False, "Invalid operator syntax"

        return True, "Formula is valid"

    def _check_balanced_parentheses(self, formula: str) -> bool:
        count = 0
        for char in formula:
            if char == "(":
                count += 1
            elif char == ")":
                count -= 1
            if count < 0:
                return False
        return count == 0

    def _validate_aggregations(self, formula: str):
        import re

        matches = re.findall(r"([A-Z_]+)\s*\(", formula)
        for func in matches:
            if func not in self.VALID_AGGREGATIONS:
                return False, f"Invalid aggregation function: {func}"
        return True, ""

    def _validate_operators(self, formula: str):
        import re

        temp = formula
        for agg in self.VALID_AGGREGATIONS:
            temp = re.sub(rf"{agg}\s*\([^)]+\)", "", temp)
        temp = re.sub(r"[a-zA-Z_][a-zA-Z0-9_]*", "", temp)
        temp = re.sub(r"\d+\.?\d*", "", temp)
        temp = re.sub(r"[\s()+\-*/]", "", temp)
        if temp:
            return False, f"Invalid characters in formula: {temp}"
        return True, ""

    def extract_referenced_metrics(self, formula: str):
        import re

        temp = formula or ""
        for agg in self.VALID_AGGREGATIONS:
            temp = re.sub(rf"{agg}\s*\([^)]+\)", "", temp)
        metrics = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", temp)
        return list(set(metrics))


__all__ = [
    "MQLValidator",
    "BaseMQLValidator",
    "ValidationError",
    "ValidationResult",
    "MetricValidator",
    "DimensionValidator",
    "FilterValidator",
    "HavingValidator",
    "OrderByValidator",
    "DistinctValidator",
    "LimitValidator",
    "WindowFuncValidator",
    "UnionValidator",
    "CTEValidator",
    "TimeConstraintValidator",
    "MQLCompositeValidator",
]
