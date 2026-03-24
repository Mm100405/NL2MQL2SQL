"""
cte_validator.py - CTE 公共表表达式校验器
"""

from typing import Any, Dict
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class CTEValidator(BaseMQLValidator):
    """
    校验 cte

    规则：
    1. cte 必须是 [{"name": "CTE名", "query": MQL}, ...] 格式
    2. name 不能为空
    3. query 必须是有效的 MQL 对象
    """

    field_name = "cte"
    error_code_prefix = "CTE_"

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None:
            return result

        if not isinstance(value, list):
            result.add_error(self.error(
                "INVALID_CTE_TYPE",
                f"cte 必须是列表",
                "cte",
                value=type(value).__name__,
                suggestion="cte 格式：[{\"name\": \"sales_summary\", \"query\": {MQL对象}}]"
            ))
            return result

        cte_names = set()
        for i, cte_def in enumerate(value):
            if not isinstance(cte_def, dict):
                result.add_error(self.error(
                    "INVALID_CTE_ITEM_TYPE",
                    f"cte[{i}] 必须是对象",
                    "cte",
                    value=type(cte_def).__name__,
                    suggestion="cte 格式：[{\"name\": \"sales_summary\", \"query\": {MQL对象}}]"
                ))
                continue

            name = cte_def.get("name")
            if not name:
                result.add_error(self.error(
                    "MISSING_CTE_NAME",
                    f"cte[{i}] 缺少 name 字段",
                    "cte",
                    value=cte_def,
                    suggestion="添加 name 字段，如：{\"name\": \"sales_summary\", \"query\": {...}}"
                ))
            elif name in cte_names:
                result.add_error(self.error(
                    "DUPLICATE_CTE_NAME",
                    f"CTE 名称 '{name}' 重复",
                    "cte",
                    value=name,
                    suggestion="每个 CTE 必须有唯一的名称"
                ))
            else:
                cte_names.add(name)

            query = cte_def.get("query")
            if not query:
                result.add_error(self.error(
                    "MISSING_CTE_QUERY",
                    f"cte[{i}] 缺少 query 字段",
                    "cte",
                    value=name,
                    suggestion="添加 query 字段，如：{\"name\": \"sales_summary\", \"query\": {MQL对象}}"
                ))
            elif not isinstance(query, dict):
                result.add_error(self.error(
                    "INVALID_CTE_QUERY_TYPE",
                    f"cte[{i}].query 必须是 MQL 对象",
                    "cte",
                    value=type(query).__name__,
                    suggestion="query 必须是 MQL 对象"
                ))
            else:
                # 递归校验 CTE 子查询
                from .composite_validator import MQLCompositeValidator
                if self.context:
                    validator = MQLCompositeValidator(self.context.db)
                    cte_result = validator.validate(query)
                    # 修改错误字段路径，标记是第几个CTE
                    for error in cte_result.errors:
                        error.field = f"cte[{i}].query.{error.field}"
                        result.add_error(error)
                    for warning in cte_result.warnings:
                        warning.field = f"cte[{i}].query.{warning.field}"
                        result.add_warning(warning)

        return result
