"""
metric_validator.py - 指标字段校验器
"""

from typing import Any, Dict, List, Set
from app.utils.mql_validator.base import (
    BaseMQLValidator,
    ValidationResult,
    ValidationError,
)


class MetricValidator(BaseMQLValidator):
    """
    校验 metrics 和 metricDefinitions

    规则：
    1. metrics 列表不能为空
    2. 每个指标必须有对应的 metricDefinitions
    3. metricDefinitions 中的 refMetric 必须存在
    4. aggregation 必须合法（SUM/COUNT/AVG/MAX/MIN/COUNT_DISTINCT）
    """

    field_name = "metrics"
    error_code_prefix = "METRIC_"

    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult()

        # 1. 校验 metrics 列表
        metrics = value if isinstance(value, list) else mql.get("metrics", [])
        if not metrics:
            result.add_error(self.error(
                "EMPTY_METRICS",
                "metrics 列表不能为空",
                "metrics",
                value=metrics,
                suggestion="添加至少一个指标，如 metrics: [\"销售额\"]"
            ))

        # 2. 获取 metricDefinitions
        metric_defs = mql.get("metricDefinitions")

        # 如果完全没有 metricDefinitions 字段，报错（MQL 格式不完整）
        if metric_defs is None:
            for metric_alias in metrics:
                result.add_error(self.error(
                    "MISSING_METRIC_DEF",
                    f"指标 '{metric_alias}' 没有对应的 metricDefinitions，MQL 必须包含 metricDefinitions 字段",
                    "metricDefinitions",
                    value=metric_alias,
                    suggestion=f"添加 metricDefinitions: {{\"{metric_alias}\": {{\"refMetric\": \"{metric_alias}\"}}}}"
                ))
            return result

        if not isinstance(metric_defs, dict):
            result.add_error(self.error(
                "INVALID_METRIC_DEF_TYPE",
                "metricDefinitions 必须是字典类型",
                "metricDefinitions",
                value=type(metric_defs).__name__,
                suggestion="metricDefinitions 格式：{\"指标名\": {\"refMetric\": \"基础指标名\"}}"
            ))
            return result

        # 3. 校验每个指标是否在 metricDefinitions 中定义
        metric_names = set()
        for metric_alias in metrics:
            metric_names.add(metric_alias)

            if metric_alias not in metric_defs:
                result.add_error(self.error(
                    "MISSING_METRIC_DEF",
                    f"指标 '{metric_alias}' 没有对应的 metricDefinitions",
                    "metricDefinitions",
                    value=metric_alias,
                    suggestion=f"添加 metricDefinitions: {{\"{metric_alias}\": {{\"refMetric\": \"{metric_alias}\"}}}}"
                ))

        # 4. 校验 metricDefinitions
        for alias, defn in metric_defs.items():
            if not isinstance(defn, dict):
                result.add_error(self.error(
                    "INVALID_METRIC_DEF_TYPE",
                    f"metricDefinitions['{alias}'] 必须是字典类型",
                    "metricDefinitions",
                    value=type(defn).__name__,
                    suggestion="metricDefinitions 格式：{\"指标名\": {\"refMetric\": \"基础指标名\"}}"
                ))
                continue

            ref_metric = defn.get("refMetric")
            if not ref_metric:
                result.add_error(self.error(
                    "MISSING_REF_METRIC",
                    f"metricDefinitions['{alias}'] 缺少 refMetric 字段",
                    "metricDefinitions",
                    value=alias,
                    suggestion=f"添加 refMetric，如 {{\"refMetric\": \"{alias}\"}}"
                ))
            elif self.context and not self.context.is_metric(ref_metric):
                # refMetric 必须是已存在的指标
                result.add_error(self.error(
                    "INVALID_REF_METRIC",
                    f"refMetric '{ref_metric}' 不是有效的指标名",
                    "metricDefinitions",
                    value=ref_metric,
                    suggestion=f"refMetric 必须是已存在的指标，可选：{list(self.context.metric_names)[:5]}..."
                ))

            # 校验 aggregation
            aggregation = defn.get("aggregation")
            if aggregation:
                valid_aggregations = {"SUM", "COUNT", "AVG", "MAX", "MIN", "COUNT_DISTINCT"}
                if aggregation.upper() not in valid_aggregations:
                    result.add_error(self.error(
                        "INVALID_AGGREGATION",
                        f"aggregation '{aggregation}' 不合法",
                        "metricDefinitions",
                        value=aggregation,
                        suggestion=f"可选值：{', '.join(valid_aggregations)}"
                    ))

            # 校验 indirections
            indirections = defn.get("indirections", [])
            if indirections and not isinstance(indirections, list):
                result.add_error(self.error(
                    "INVALID_INDIRECTIONS",
                    f"indirections 必须是列表",
                    "metricDefinitions",
                    value=type(indirections).__name__,
                    suggestion="indirections 格式：[\"yoy_growth\", \"mom_growth\"]"
                ))

        return result
