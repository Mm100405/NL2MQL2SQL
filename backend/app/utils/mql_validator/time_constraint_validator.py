"""
time_constraint_validator.py - 时间约束校验器

⚠️ 已废弃 (DEPRECATED) ⚠️

从 V2 版本开始，timeConstraint 字段已废弃。
时间过滤应统一使用 filters 字段，支持任意时间类型字段。

废弃原因：
1. timeConstraint 只能指定一个时间字段，无法支持多时间字段场景
2. 默认时间字段已迁移到 View.default_date_column_id
3. 时间过滤与其他维度过滤统一，简化 MQL 结构

迁移指南：
- 旧格式: "timeConstraint": "[日期] >= LAST_N_DAYS(30)"
- 新格式: "filters": {"operator": "AND", "conditions": [{"field": "日期", "op": ">=", "value": "LAST_N_DAYS(30)"}]}

此校验器保留用于向后兼容，但会输出废弃警告。
"""

import re
from typing import Any, Dict, Set
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class TimeConstraintValidator(BaseMQLValidator):
    """
    校验 timeConstraint

    规则：
    1. 只允许白名单时间函数
    2. 字段引用必须是时间维度
    3. 函数参数格式正确
    """

    field_name = "timeConstraint"
    error_code_prefix = "TIME_CONSTRAINT_"

    # 白名单时间函数（统一大写比较）
    VALID_FUNCTIONS = {
        "TODAY", "YESTERDAY", "TOMORROW",
        "LAST_N_DAYS", "LAST_N_MONTHS", "LAST_N_YEARS",
        "THIS_WEEK", "THIS_MONTH", "THIS_YEAR",
        "DATETRUNC", "ADDMONTHS", "DATEADD", "DATESUB",
        "CURRENT_DATE", "CURRENT_TIMESTAMP", "DATE_SUB", "DATE_FORMAT",
    }

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        if value is None or value == "":
            return result

        if not isinstance(value, str):
            result.add_error(self.error(
                "INVALID_TIME_CONSTRAINT_TYPE",
                f"timeConstraint 必须是字符串",
                "timeConstraint",
                value=type(value).__name__,
                suggestion="timeConstraint 格式：\"[日期] >= LAST_N_DAYS(30)\""
            ))
            return result

        # 提取时间函数
        func_pattern = r"([A-Z_]+)\s*\("
        funcs = re.findall(func_pattern, value, re.IGNORECASE)

        for func in funcs:
            func_upper = func.upper()
            if func_upper not in self.VALID_FUNCTIONS:
                result.add_error(self.error(
                    "INVALID_TIME_FUNCTION",
                    f"时间函数 '{func}' 不在白名单中",
                    "timeConstraint",
                    value=func,
                    suggestion=f"支持的时间函数：{', '.join(sorted(self.VALID_FUNCTIONS))}"
                ))

        # 检查字段引用
        field_refs = self.extract_field_refs(value)
        for field_ref in field_refs:
            if self.context:
                if not self.context.is_dimension(field_ref):
                    result.add_warning(self.warning(
                        "FIELD_NOT_A_DIMENSION",
                        f"timeConstraint 中的字段 '{field_ref}' 不是维度",
                        "timeConstraint",
                        value=field_ref,
                    ))
                elif field_ref not in self.context.time_dimensions:
                    result.add_warning(self.warning(
                        "FIELD_NOT_TIME_DIMENSION",
                        f"字段 '{field_ref}' 不是时间维度",
                        "timeConstraint",
                        value=field_ref,
                    ))

        return result
