"""distinct_validator.py - 校验 distinct 字段（去重）"""

from typing import Any, Dict
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class DistinctValidator(BaseMQLValidator):
    """校验 distinct 字段（去重）"""

    field_name = "distinct"
    error_code_prefix = "DISTINCT_"

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None:
            return result

        if not isinstance(value, bool):
            result.add_error(self.error(
                "INVALID_DISTINCT_TYPE",
                f"distinct 必须是布尔值",
                "distinct",
                value=type(value).__name__,
                suggestion="distinct 格式：distinct: true 或 distinct: false"
            ))

        return result



