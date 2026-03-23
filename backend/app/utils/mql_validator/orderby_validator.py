"""
orderby_validator.py - ORDER BY 校验器
"""

from typing import Any, Dict, List
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class OrderByValidator(BaseMQLValidator):
    """
    校验 orderBy

    规则：
    1. orderBy 必须是列表
    2. 每个元素必须有 field 字段
    3. direction 必须是 ASC 或 DESC
    4. field 必须在 SELECT 中（metrics 或 dimensions）
    """

    field_name = "orderBy"
    error_code_prefix = "ORDERBY_"

    VALID_DIRECTIONS = {"ASC", "DESC", "asc", "desc"}

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None or value == "":
            return result

        if not isinstance(value, list):
            result.add_error(self.error(
                "INVALID_ORDERBY_TYPE",
                f"orderBy 必须是列表",
                "orderBy",
                value=type(value).__name__,
                suggestion="orderBy 格式：[{\"field\": \"销售额\", \"direction\": \"DESC\"}]"
            ))
            return result

        # 获取 SELECT 中可用的字段
        select_fields = set()
        select_fields.update(mql.get("metrics", []))
        select_fields.update(mql.get("dimensions", []))

        for i, order_spec in enumerate(value):
            if not isinstance(order_spec, dict):
                result.add_error(self.error(
                    "INVALID_ORDER_SPEC_TYPE",
                    f"orderBy[^{i}] 必须是对象",
                    "orderBy",
                    value=type(order_spec).__name__,
                    suggestion="orderBy 格式：[{\"field\": \"销售额\", \"direction\": \"DESC\"}]"
                ))
                continue

            field = order_spec.get("field")
            if not field:
                result.add_error(self.error(
                    "MISSING_FIELD",
                    f"orderBy[^{i}] 缺少 field 字段",
                    "orderBy",
                    value=order_spec,
                    suggestion="添加 field 字段，如：{\"field\": \"销售额\", \"direction\": \"DESC\"}"
                ))
            else:
                # 检查 field 是否在 SELECT 中
                # 允许字段名或带别名的字段
                field_base = field.split("__")[0] if "__" in field else field
                is_valid = (
                    field in select_fields or
                    field_base in select_fields or
                    (self.context and (
                        self.context.is_metric(field) or
                        self.context.is_dimension(field)
                    ))
                )

                if not is_valid:
                    result.add_warning(self.warning(
                        "FIELD_NOT_IN_SELECT",
                        f"orderBy 字段 '{field}' 不在 SELECT 中",
                        "orderBy",
                        value=order_spec,
                        suggestion=f"orderBy 字段必须在 metrics 或 dimensions 中，可选：{list(select_fields)[:5]}..."
                    ))

            # 检查 direction
            direction = order_spec.get("direction", "ASC").upper()
            if direction not in self.VALID_DIRECTIONS:
                result.add_error(self.error(
                    "INVALID_DIRECTION",
                    f"orderBy direction '{direction}' 不合法",
                    "orderBy",
                    value=direction,
                    suggestion="direction 必须是 ASC 或 DESC"
                ))

        return result
