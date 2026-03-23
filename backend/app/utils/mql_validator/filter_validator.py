"""
filter_validator.py - 过滤字段校验器

⚠️ 核心规则：指标字段不能在 filters（WHERE）中！

filters 中的过滤是在聚合之前执行的，所以只能过滤维度/时间字段。
如果需要对指标（聚合结果）进行过滤，应该使用 having。

示例：
- ✅ 正确：filters: ["[渠道] = '线上'"]  （维度过滤，聚合前生效）
- ❌ 错误：filters: ["[立案数] > 1"]  （指标过滤，应该在 having 中）
- ✅ 正确：having: "[立案数] > 1"  （聚合后过滤）
"""

import re
from typing import Any, Dict, List, Set
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
)


class FilterValidator(BaseMQLValidator):
    """
    校验 filters

    规则：
    1. 字段引用格式必须正确：[字段名]
    2. 字段必须是维度/时间，不能是指标
    3. 操作符必须合法
    4. 值格式必须正确
    """

    field_name = "filters"
    error_code_prefix = "FILTER_"

    # 合法的过滤操作符
    VALID_OPERATORS = {
        "=", "!=", "==", "<>", "<", ">", "<=", ">=",
        "LIKE", "NOT LIKE",
        "IN", "NOT IN",
        "IS NULL", "IS NOT NULL",
    }

    VALID_STRUCTURED_OPERATORS = {
        "=", "!=", "<>", "<", ">", "<=", ">=",
        "LIKE", "IN", "NOT IN", "IS NULL", "IS NOT NULL",
    }

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        filters = value
        if filters is None:
            filters = mql.get("filters", [])
        if not filters:
            return result

        # 获取指标列表（用于判断）
        metrics = set(mql.get("metrics", []))
        metric_defs = mql.get("metricDefinitions", {})
        if self.context:
            metrics = metrics | self.context.metric_names | self.context.metric_display_names

        if isinstance(filters, dict):
            # 新结构化格式
            self._validate_structured_filter(filters, result, metrics, mql)
        elif isinstance(filters, list):
            for filter_expr in filters:
                if isinstance(filter_expr, dict):
                    # 列表中的结构化条件
                    self._validate_structured_filter(filter_expr, result, metrics, mql)
                elif isinstance(filter_expr, str):
                    self._validate_string_filter(filter_expr, result, metrics)
                else:
                    result.add_error(self.error(
                        "INVALID_FILTER_TYPE",
                        f"filter 必须是字符串或结构化对象类型",
                        "filters",
                        value=type(filter_expr).__name__,
                        suggestion="filters 格式：{\"field\": \"字段名\", \"op\": \"=\", \"value\": \"值\"} 或 [\"[渠道] = '线上'\"]"
                    ))
        else:
            result.add_error(self.error(
                "INVALID_FILTER_TYPE",
                f"filters 必须是数组或结构化对象",
                "filters",
                value=type(filters).__name__,
                suggestion="filters 格式：{\"operator\": \"AND\", \"conditions\": [...]} 或 [\"[渠道] = '线上'\"]"
            ))

        return result

    def _validate_string_filter(self, filter_expr: str, result: ValidationResult, metrics: set):
        """校验字符串格式的 filter（旧格式，向后兼容）"""
        # 1. 检查字段引用格式
        field_refs = self.extract_field_refs(filter_expr)
        if not field_refs:
            result.add_warning(self.warning(
                "MISSING_FIELD_REF",
                f"filter 缺少字段引用格式，应使用 [字段名]",
                "filters",
                value=filter_expr,
                suggestion="正确格式：[渠道] = '线上'"
            ))

        # 2. 检查字段是否为指标（核心校验！）
        for field_ref in field_refs:
            if self.context:
                if self.context.is_metric(field_ref):
                    metric_alias = field_ref
                    if not self.context.is_metric(metric_alias):
                        for name, defn in self.context.metric_definitions.items():
                            if defn.get("display_name") == metric_alias:
                                metric_alias = name
                                break

                    result.add_error(self.error(
                        "FILTER_METRIC_IN_WHERE",
                        f"字段 '{field_ref}' 是指标，不能放在 filters（WHERE）中。"
                        f"WHERE 中过滤是在聚合之前执行的，指标是聚合结果，无法在聚合前过滤。"
                        f"应该将 '[{field_ref}] > N' 移到 having 字段中。",
                        "filters",
                        value=filter_expr,
                        suggestion=f"将 '[{field_ref}]' 相关的过滤条件从 filters 移到 having 字段。"
                        f"例如：having: \"[{field_ref}] > N\""
                    ))

                # 3. 检查字段是否在可过滤字段列表中
                if field_ref not in self.context.filterable_fields:
                    result.add_error(self.error(
                        "FIELD_NOT_FOUND",
                        f"字段 '{field_ref}' 不可用于过滤或不存在",
                        "filters",
                        value=filter_expr,
                        suggestion=f"可过滤字段：{list(self.context.filterable_fields)[:10]}..."
                    ))

        # 4. 检查操作符
        filter_upper = filter_expr.upper()
        for op in self.VALID_OPERATORS:
            if op.upper() in filter_upper:
                pattern = r"\[.*?\]\s*" + re.escape(op) + r"\s*"
                if re.search(pattern, filter_expr, re.IGNORECASE):
                    break
        else:
            result.add_warning(self.warning(
                "UNKNOWN_OPERATOR",
                f"filter 中可能包含不支持的操作符",
                "filters",
                value=filter_expr,
                suggestion=f"支持的操作符：{', '.join(self.VALID_OPERATORS)}"
            ))

        # 5. 检查 IN/NOT IN 语法
        if " IN " in filter_upper or " NOT IN " in filter_upper:
            paren_count = filter_expr.count("(") - filter_expr.count(")")
            if paren_count != 0:
                result.add_error(self.error(
                    "UNBALANCED_PARENTHESES",
                    f"IN/NOT IN 表达式括号不匹配",
                    "filters",
                    value=filter_expr,
                    suggestion="检查括号是否正确配对，如：IN ('A', 'B', 'C')"
                ))

    def _validate_structured_filter(self, condition: Dict[str, Any], result: ValidationResult, metrics: set, mql: Dict[str, Any]):
        """递归校验结构化 filter 条件"""
        if "field" in condition:
            # 叶子条件校验
            field = condition["field"]
            op = condition.get("op", "=").upper()
            value = condition.get("value")

            # 1. 检查字段是否为指标
            if self.context and self.context.is_metric(field):
                result.add_error(self.error(
                    "FILTER_METRIC_IN_WHERE",
                    f"字段 '{field}' 是指标，不能放在 filters（WHERE）中。"
                    f"应该将此条件移到 having 字段中。",
                    "filters",
                    value=f"{{\"field\": \"{field}\", \"op\": \"{op}\", \"value\": {value!r}}}",
                    suggestion=f"将 '{field}' 相关的过滤条件从 filters 移到 having 字段。"
                ))

            # 2. 检查字段是否在可过滤字段列表中
            if self.context and field not in self.context.filterable_fields:
                result.add_error(self.error(
                    "FIELD_NOT_FOUND",
                    f"字段 '{field}' 不可用于过滤或不存在",
                    "filters",
                    value=field,
                    suggestion=f"可过滤字段：{list(self.context.filterable_fields)[:10]}..."
                ))

            # 3. 检查操作符是否合法
            if op not in self.VALID_STRUCTURED_OPERATORS:
                result.add_warning(self.warning(
                    "UNKNOWN_OPERATOR",
                    f"结构化 filter 中不支持的操作符 '{op}'",
                    "filters",
                    value=op,
                    suggestion=f"支持的操作符：{', '.join(self.VALID_STRUCTURED_OPERATORS)}"
                ))

            # 4. 检查 value 格式
            if op not in ("IS NULL", "IS NOT NULL") and value is None:
                result.add_error(self.error(
                    "INVALID_FILTER_TYPE",
                    f"操作符 '{op}' 需要提供 value",
                    "filters",
                    value=condition,
                    suggestion=f"请为字段 '{field}' 提供过滤值"
                ))

            if op in ("IN", "NOT IN") and not isinstance(value, list):
                result.add_error(self.error(
                    "INVALID_FILTER_TYPE",
                    f"操作符 '{op}' 的 value 必须是数组",
                    "filters",
                    value=type(value).__name__,
                    suggestion=f"IN/NOT IN 的 value 应为列表，如 [\"值1\", \"值2\"]"
                ))

        else:
            # 分组条件 - 递归校验子条件
            operator = condition.get("operator", "AND").upper()
            if operator not in ("AND", "OR"):
                result.add_warning(self.warning(
                    "UNKNOWN_OPERATOR",
                    f"结构化 filter 中的分组运算符 '{operator}' 不支持",
                    "filters",
                    value=operator,
                    suggestion="分组运算符只支持 AND 或 OR"
                ))

            for sub in condition.get("conditions", []):
                if isinstance(sub, dict):
                    self._validate_structured_filter(sub, result, metrics, mql)
                else:
                    result.add_error(self.error(
                        "INVALID_FILTER_TYPE",
                        f"结构化 filter 的 conditions 中每个元素必须是对象",
                        "filters",
                        value=type(sub).__name__,
                        suggestion="conditions 中每个元素应为 {\"field\": \"...\", \"op\": \"...\", \"value\": \"...\"}"
                    ))
