"""
union_validator.py - UNION 查询校验器
"""

from typing import Any, Dict
from .base import (
    BaseMQLValidator,
    ValidationResult,
)


class UnionValidator(BaseMQLValidator):
    """
    校验 union

    规则：
    1. union 必须是 {"type": "ALL"|"", "queries": [MQL列表]}
    2. type 必须是 "ALL" 或空字符串
    3. queries 必须是 MQL 列表
    4. 每个子 MQL 也需要递归校验
    """

    field_name = "union"
    error_code_prefix = "UNION_"

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None:
            return result

        if not isinstance(value, dict):
            result.add_error(self.error(
                "INVALID_UNION_TYPE",
                f"union 必须是对象",
                "union",
                value=type(value).__name__,
                suggestion="union 格式：{\"type\": \"ALL\", \"queries\": [MQL1, MQL2]}"
            ))
            return result

        union_type = value.get("type", "")
        if union_type not in ("", "ALL"):
            result.add_error(self.error(
                "INVALID_UNION_TYPE_VALUE",
                f"union.type '{union_type}' 不合法",
                "union",
                value=union_type,
                suggestion="union.type 必须是空字符串（去重）或 \"ALL\"（不去重）"
            ))

        queries = value.get("queries", [])
        if not isinstance(queries, list):
            result.add_error(self.error(
                "INVALID_UNION_QUERIES_TYPE",
                f"union.queries 必须是列表",
                "union",
                value=type(queries).__name__,
                suggestion="union.queries 格式：[MQL1, MQL2]"
            ))
        elif len(queries) < 2:
            result.add_error(self.error(
                "UNION_TOO_FEW_QUERIES",
                f"UNION 至少需要 2 个查询",
                "union",
                value=len(queries),
                suggestion="UNION 需要至少 2 个查询，如：{\"queries\": [MQL1, MQL2]}"
            ))
        else:
            # 递归校验每个子查询
            from .composite_validator import MQLCompositeValidator
            if self.context:
                validator = MQLCompositeValidator(self.context.db)
                for i, sub_mql in enumerate(queries):
                    if isinstance(sub_mql, dict):
                        sub_result = validator.validate(sub_mql)
                        # 修改错误字段路径，标记是第几个子查询
                        for error in sub_result.errors:
                            error.field = f"union.queries[{i}].{error.field}"
                            result.add_error(error)
                        for warning in sub_result.warnings:
                            warning.field = f"union.queries[{i}].{warning.field}"
                            result.add_warning(warning)

        return result
