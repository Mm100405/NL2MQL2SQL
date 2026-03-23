"""
dimension_validator.py - 维度字段校验器
"""

import re
from typing import Any, Dict, List
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class DimensionValidator(BaseMQLValidator):
    """
    校验 dimensions

    规则：
    1. 维度字段必须存在于元数据
    2. 时间维度可以使用粒度后缀（__按月, __year 等）
    3. 非时间维度不能使用时间粒度后缀
    """

    field_name = "dimensions"
    error_code_prefix = "DIMENSION_"

    # 时间粒度后缀
    TIME_SUFFIXES = {
        "按日", "按月", "按年", "按周",
        "day", "month", "year", "week",
        "year", "month", "day",
    }

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        dimensions = value if isinstance(value, list) else mql.get("dimensions", [])

        for dim_name in dimensions:
            if not isinstance(dim_name, str):
                result.add_error(self.error(
                    "INVALID_DIMENSION_TYPE",
                    f"dimension 必须是字符串类型",
                    "dimensions",
                    value=type(dim_name).__name__,
                    suggestion="dimensions 格式：[{\"街道\"}, {\"日期__按月\"}]"
                ))
                continue

            # 解析后缀
            actual_name = dim_name
            suffix = None
            if "__" in dim_name:
                parts = dim_name.split("__", 1)
                actual_name = parts[0]
                suffix = parts[1]

            # 检查维度是否存在
            if self.context:
                if not self.context.is_dimension(actual_name):
                    # 检查是否可以通过 display_name 找到
                    found = False
                    for name, defn in self.context.dimension_definitions.items():
                        if defn.get("display_name") == actual_name:
                            found = True
                            break

                    if not found:
                        result.add_error(self.error(
                            "DIMENSION_NOT_FOUND",
                            f"维度 '{actual_name}' 不存在",
                            "dimensions",
                            value=dim_name,
                            suggestion=f"可选维度：{list(self.context.dimension_names)[:5]}..."
                        ))

            # 如果有后缀，检查是否为时间维度
            if suffix:
                if self.context:
                    is_time_dim = actual_name in self.context.time_dimensions
                    if not is_time_dim:
                        result.add_error(self.error(
                            "INVALID_TIME_SUFFIX",
                            f"维度 '{actual_name}' 不是时间维度，不能使用时间粒度后缀 '__^{suffix}'",
                            "dimensions",
                            value=dim_name,
                            suggestion="只有时间维度才能使用时间粒度后缀，如 日期__按月"
                        ))

                # 检查后缀是否合法
                if suffix not in self.TIME_SUFFIXES:
                    result.add_warning(self.warning(
                        "UNKNOWN_TIME_SUFFIX",
                        f"时间粒度后缀 '{suffix}' 不是标准后缀",
                        "dimensions",
                        value=dim_name,
                        suggestion=f"可选后缀：{', '.join(self.TIME_SUFFIXES)}"
                    ))

        return result
