"""
DETAIL 模式校验器

校验 queryResultType=DETAIL 时的 fields / metrics / dimensions / having 约束。
"""

from typing import Any, Dict
from app.utils.mql_validator.base import BaseMQLValidator, ValidationResult


class DetailValidator(BaseMQLValidator):
    """校验 DETAIL 查询模式"""

    field_name = "queryResultType"
    error_code_prefix = "DETAIL_"

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        query_result_type = (value or mql.get("queryResultType") or "DATA").upper()
        if query_result_type != "DETAIL":
            return result

        fields = mql.get("fields", [])
        metrics = mql.get("metrics", [])
        dimensions = mql.get("dimensions", [])
        having = mql.get("having")
        metric_defs = mql.get("metricDefinitions")
        window_functions = mql.get("windowFunctions")

        if not isinstance(fields, list) or not fields:
            result.add_error(self.error(
                "EMPTY_FIELDS",
                "DETAIL 模式下 fields 列表不能为空",
                "fields",
                value=fields,
                suggestion="添加至少一个返回字段，如 fields: [\"case_id\", \"street_name\"]"
            ))
            return result

        for field_name in fields:
            if not isinstance(field_name, str):
                result.add_error(self.error(
                    "INVALID_FIELD_TYPE",
                    "DETAIL 模式下 fields 中的每个字段都必须是字符串",
                    "fields",
                    value=type(field_name).__name__,
                    suggestion="fields 格式：['字段1', '字段2']"
                ))
                continue

            if self.context and not self.context.is_detail_field(field_name):
                result.add_error(self.error(
                    "FIELD_NOT_FOUND",
                    f"DETAIL 返回字段 '{field_name}' 不存在或不可返回",
                    "fields",
                    value=field_name,
                    suggestion="请从视图字段或维度字段中选择返回列"
                ))

        if metrics:
            result.add_error(self.error(
                "DETAIL_WITH_METRICS",
                "DETAIL 模式不能使用 metrics，请改用 fields 返回明细字段",
                "metrics",
                value=metrics,
                suggestion="删除 metrics，改为 fields"
            ))

        if dimensions:
            result.add_error(self.error(
                "DETAIL_WITH_DIMENSIONS",
                "DETAIL 模式不能使用 dimensions，请改用 fields 返回明细字段",
                "dimensions",
                value=dimensions,
                suggestion="删除 dimensions，改为 fields"
            ))

        if metric_defs:
            result.add_error(self.error(
                "DETAIL_WITH_METRIC_DEFS",
                "DETAIL 模式不能使用 metricDefinitions",
                "metricDefinitions",
                value=metric_defs,
                suggestion="删除 metricDefinitions"
            ))

        if having:
            result.add_error(self.error(
                "DETAIL_WITH_HAVING",
                "DETAIL 模式不能使用 having，明细查询请改用 filters",
                "having",
                value=having,
                suggestion="删除 having，将条件写入 filters"
            ))

        if window_functions:
            result.add_error(self.error(
                "DETAIL_WITH_WINDOW_FUNCTIONS",
                "DETAIL 模式暂不支持 windowFunctions",
                "windowFunctions",
                value=window_functions,
                suggestion="删除 windowFunctions，或改用 DATA 模式"
            ))

        return result
