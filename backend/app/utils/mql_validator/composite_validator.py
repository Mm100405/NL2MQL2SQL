"""
composite_validator.py - 组合校验器

组合所有独立校验器，提供统一的 MQL 校验接口
"""

from typing import Dict, Any
from sqlalchemy.orm import Session

from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationContext,
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


class MQLCompositeValidator:
    """
    MQL 组合校验器

    组合所有独立校验器，一次性验证完整的 MQL。
    """

    def __init__(self, db: Session):
        self.db = db
        self.context = ValidationContext(db)

        # 创建所有校验器并注入上下文
        self.validators = [
            MetricValidator(db),
            DimensionValidator(db),
            FilterValidator(db),
            HavingValidator(db),
            OrderByValidator(db),
            DistinctValidator(db),
            LimitValidator(db),
            WindowFuncValidator(db),
            UnionValidator(db),
            CTEValidator(db),
            TimeConstraintValidator(db),
        ]

        # 注入上下文
        for validator in self.validators:
            validator.set_context(self.context)

    def validate(self, mql: Dict[str, Any]) -> ValidationResult:
        """
        验证完整的 MQL

        Args:
            mql: MQL JSON 对象

        Returns:
            ValidationResult，包含所有错误和警告
        """
        result = ValidationResult()

        # 运行所有校验器
        for validator in self.validators:
            try:
                # 获取字段值
                field_value = mql.get(validator.field_name)
                # 传入完整 MQL（用于交叉校验）
                field_result = validator.validate(field_value, mql)
                result.merge(field_result)
            except Exception as e:
                result.add_error(validator.error(
                    "VALIDATOR_EXCEPTION",
                    f"校验器 {validator.__class__.__name__} 执行异常: {str(e)}",
                    validator.field_name,
                    value=str(e),
                ))

        return result

    def validate_and_raise(self, mql: Dict[str, Any]) -> None:
        """
        验证 MQL，如果存在 ERROR 级别的错误则抛出异常

        Args:
            mql: MQL JSON 对象

        Raises:
            MQLValidationError: 存在 ERROR 级别错误时抛出
        """
        result = self.validate(mql)

        if not result.is_valid:
            errors = [e.to_dict() for e in result.errors]
            raise MQLValidationError(errors)

    def get_context(self) -> ValidationContext:
        """获取校验上下文"""
        return self.context


class MQLValidationError(Exception):
    """MQL 校验异常"""

    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"MQL 校验失败，共 {len(errors)} 个错误")


def validate_mql(mql: Dict[str, Any], db: Session) -> ValidationResult:
    """
    便捷函数：验证 MQL

    Args:
        mql: MQL JSON 对象
        db: 数据库会话

    Returns:
        ValidationResult
    """
    validator = MQLCompositeValidator(db)
    return validator.validate(mql)


def validate_mql_strict(mql: Dict[str, Any], db: Session) -> None:
    """
    便捷函数：严格验证 MQL（存在错误则抛出异常）

    Args:
        mql: MQL JSON 对象
        db: 数据库会话

    Raises:
        MQLValidationError
    """
    validator = MQLCompositeValidator(db)
    validator.validate_and_raise(mql)
