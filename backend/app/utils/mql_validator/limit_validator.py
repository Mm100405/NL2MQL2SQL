"""limit_validator.py - 校验 limit 字段（结果限制）"""

from typing import Any, Dict
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class LimitValidator(BaseMQLValidator):
    """校验 limit 字段（结果限制）"""

    field_name = "limit"
    error_code_prefix = "LIMIT_"

    MAX_LIMIT = 100000
    DEFAULT_LIMIT = 1000

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None:
            return result

        if not isinstance(value, int):
            result.add_error(self.error(
                "INVALID_LIMIT_TYPE",
                f"limit 必须是整数",
                "limit",
                value=type(value).__name__,
                suggestion="limit 格式：limit: 1000"
            ))
            return result

        if value <= 0:
            result.add_error(self.error(
                "INVALID_LIMIT_VALUE",
                f"limit 必须大于 0",
                "limit",
                value=value,
                suggestion="limit 必须是正整数"
            ))

        if value > self.MAX_LIMIT:
            result.add_warning(self.warning(
                "LIMIT_TOO_LARGE",
                f"limit 值 {value} 过大，可能影响性能",
                "limit",
                value=value,
                suggestion=f"建议 limit 不超过 {self.MAX_LIMIT}"
            ))

        return result
