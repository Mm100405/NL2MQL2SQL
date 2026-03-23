"""
having_validator.py - HAVING 子句校验器

having 中可以引用指标（聚合后过滤）
"""

import re
from typing import Any, Dict
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class HavingValidator(BaseMQLValidator):
    """
    校验 having

    规则：
    1. having 可以引用指标（这是正确的用法）
    2. having 中的指标必须存在
    3. having 中的维度也可以存在
    4. 操作符和值格式必须正确
    """

    field_name = "having"
    error_code_prefix = "HAVING_"

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None or value == "":
            return result

        # having 可以是字符串或字符串列表
        if isinstance(value, str):
            having_exprs = [value]
        elif isinstance(value, list):
            having_exprs = value
        else:
            result.add_error(self.error(
                "INVALID_HAVING_TYPE",
                f"having 必须是字符串或字符串列表",
                "having",
                value=type(value).__name__,
                suggestion="having 格式：having: \"[销售额] > 10000\" 或 having: [\"[销售额] > 10000\", \"[订单数] > 10\"]"
            ))
            return result

        # 获取 metrics 和 dimensions
        metrics = set(mql.get("metrics", []))
        metric_defs = mql.get("metricDefinitions", {})
        dimensions = set(mql.get("dimensions", []))

        for having_expr in having_exprs:
            if not isinstance(having_expr, str):
                continue

            # 提取字段引用
            field_refs = self.extract_field_refs(having_expr)

            for field_ref in field_refs:
                # 检查字段是否存在于 metrics 或 dimensions
                is_metric = (
                    field_ref in metrics or
                    field_ref in metric_defs or
                    (self.context and self.context.is_metric(field_ref))
                )
                is_dimension = (
                    field_ref in dimensions or
                    (self.context and self.context.is_dimension(field_ref))
                )

                if not is_metric and not is_dimension:
                    result.add_warning(self.warning(
                        "FIELD_NOT_FOUND",
                        f"字段 '{field_ref}' 在 having 中引用但不存在",
                        "having",
                        value=having_expr,
                        suggestion="检查字段名是否正确"
                    ))

            # 检查操作符
            filter_upper = having_expr.upper()
            has_operator = False
            for op in ["=", "!=", "<", ">", "<=", ">="]:
                if op in filter_upper:
                    has_operator = True
                    break

            if not has_operator:
                result.add_warning(self.warning(
                    "MISSING_OPERATOR",
                    f"having 表达式缺少比较操作符",
                    "having",
                    value=having_expr,
                    suggestion="having 需要包含比较操作符，如：[销售额] > 10000"
                ))

        return result
