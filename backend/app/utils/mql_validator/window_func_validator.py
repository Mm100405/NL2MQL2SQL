"""
window_func_validator.py - 窗口函数校验器
"""

from typing import Any, Dict
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class WindowFuncValidator(BaseMQLValidator):
    """
    校验 windowFunctions

    规则：
    1. windowFunctions 必须是列表
    2. 每个元素必须有 alias, func, field
    3. func 必须是合法的窗口函数
    4. field 必须是存在的字段
    """

    field_name = "windowFunctions"
    error_code_prefix = "WINDOW_"

    VALID_FUNCTIONS = {
        "SUM", "AVG", "COUNT", "MAX", "MIN",
        "ROW_NUMBER", "RANK", "DENSE_RANK",
        "LAG", "LEAD",
        "FIRST_VALUE", "LAST_VALUE",
    }

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None:
            return result

        if not isinstance(value, list):
            result.add_error(self.error(
                "INVALID_WINDOW_FUNCTIONS_TYPE",
                f"windowFunctions 必须是列表",
                "windowFunctions",
                value=type(value).__name__,
                suggestion="windowFunctions 格式：[{\"alias\": \"累计\", \"func\": \"SUM\", \"field\": \"销售额\"}]"
            ))
            return result

        for i, window_spec in enumerate(value):
            if not isinstance(window_spec, dict):
                result.add_error(self.error(
                    "INVALID_WINDOW_SPEC_TYPE",
                    f"windowFunctions[{i}] 必须是对象",
                    "windowFunctions",
                    value=type(window_spec).__name__,
                    suggestion="windowFunctions 格式：[{\"alias\": \"累计\", \"func\": \"SUM\", \"field\": \"销售额\"}]"
                ))
                continue

            alias = window_spec.get("alias")
            if not alias:
                result.add_error(self.error(
                    "MISSING_WINDOW_ALIAS",
                    f"windowFunctions[{i}] 缺少 alias 字段",
                    "windowFunctions",
                    value=window_spec,
                    suggestion="添加 alias 字段，如：{\"alias\": \"累计销售额\", \"func\": \"SUM\", \"field\": \"销售额\"}"
                ))

            func = window_spec.get("func")
            if not func:
                result.add_error(self.error(
                    "MISSING_WINDOW_FUNC",
                    f"windowFunctions[{i}] 缺少 func 字段",
                    "windowFunctions",
                    value=window_spec,
                    suggestion="添加 func 字段，如：{\"func\": \"SUM\"}"
                ))
            elif func.upper() not in self.VALID_FUNCTIONS:
                result.add_error(self.error(
                    "INVALID_WINDOW_FUNC",
                    f"窗口函数 '{func}' 不合法",
                    "windowFunctions",
                    value=func,
                    suggestion=f"支持的窗口函数：{', '.join(self.VALID_FUNCTIONS)}"
                ))

            field = window_spec.get("field")
            if field and self.context:
                if not self.context.is_metric(field) and not self.context.is_dimension(field):
                    result.add_warning(self.warning(
                        "WINDOW_FIELD_NOT_FOUND",
                        f"窗口函数字段 '{field}' 不存在",
                        "windowFunctions",
                        value=field,
                    ))

        return result
