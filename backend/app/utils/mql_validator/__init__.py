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

__all__ = [
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
