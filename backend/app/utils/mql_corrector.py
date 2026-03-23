"""
mql_corrector.py - MQL 纠错器（策略模式）

根据校验错误自动修正 MQL，覆盖全部 49 个错误码。

策略模式架构：
- BaseCorrectionStrategy: 基础策略抽象类
- 每个 MQL 字段的错误码对应一个或多个修正策略
- MQLCorrector: 纠错编排器，将错误码分发到对应策略

支持的字段：metrics, metricDefinitions, dimensions, timeConstraint,
           filters, having, orderBy, distinct, limit,
           windowFunctions, union, cte
"""

import json
import re
import copy
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Type
from sqlalchemy.orm import Session

from app.utils.mql_validator.base import ValidationError, ValidationContext
from app.utils.mql_validator.composite_validator import MQLCompositeValidator

logger = logging.getLogger(__name__)


# ============================================================
# 基础策略
# ============================================================

class BaseCorrectionStrategy(ABC):
    """修正策略基类"""

    @abstractmethod
    def correct(
        self,
        mql: Dict[str, Any],
        error: ValidationError,
        context: ValidationContext,
    ) -> Dict[str, Any]:
        """
        修正 MQL

        Args:
            mql: 当前 MQL（已深拷贝）
            error: 待修正的错误
            context: 校验上下文（含元数据）

        Returns:
            修正后的 MQL
        """
        ...

    @abstractmethod
    def can_handle(self, error_code: str) -> bool:
        """是否能处理该错误码"""
        ...


# ============================================================
# Metrics 相关策略
# ============================================================

class CompleteMetricDefStrategy(BaseCorrectionStrategy):
    """补全缺失的 metricDefinitions"""

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "METRIC_MISSING_METRIC_DEF",
            "METRIC_INVALID_METRIC_DEF_TYPE",
            "METRIC_MISSING_REF_METRIC",
            "METRIC_INVALID_REF_METRIC",
        )

    def correct(self, mql, error, context):
        metrics = mql.get("metrics", [])
        metric_defs = mql.get("metricDefinitions", {})
        if not isinstance(metric_defs, dict):
            metric_defs = {}

        for metric_name in metrics:
            if metric_name in metric_defs:
                defn = metric_defs[metric_name]
                if isinstance(defn, dict) and defn.get("refMetric"):
                    continue

            # 查找指标定义
            found = False
            for name, defn in context.metric_definitions.items():
                display_name = defn.get("display_name", "")
                if display_name == metric_name or name == metric_name:
                    metric_defs[metric_name] = {
                        "refMetric": name,
                        "aggregation": defn.get("aggregation", "SUM"),
                    }
                    found = True
                    break

            if not found:
                # 模糊匹配指标名
                best_match = self._fuzzy_match(metric_name, context)
                if best_match:
                    defn = context.metric_definitions[best_match]
                    metric_defs[metric_name] = {
                        "refMetric": best_match,
                        "aggregation": defn.get("aggregation", "SUM"),
                    }
                else:
                    metric_defs[metric_name] = {
                        "refMetric": metric_name,
                        "aggregation": "SUM",
                    }

        mql["metricDefinitions"] = metric_defs
        return mql

    def _fuzzy_match(self, name: str, context: ValidationContext) -> Optional[str]:
        """模糊匹配指标名"""
        name_lower = name.lower().replace(" ", "").replace("_", "")
        candidates = []
        for m_name, m_def in context.metric_definitions.items():
            m_display = m_def.get("display_name", m_name)
            m_lower = m_display.lower().replace(" ", "").replace("_", "")
            if name_lower in m_lower or m_lower in name_lower:
                candidates.append((m_name, len(m_lower)))
        if candidates:
            candidates.sort(key=lambda x: -x[1])
            return candidates[0][0]
        return None


class FixAggregationStrategy(BaseCorrectionStrategy):
    """修正 aggregation 值"""

    VALID_AGGS = {"SUM", "COUNT", "AVG", "MAX", "MIN", "COUNT_DISTINCT"}

    def can_handle(self, error_code: str) -> bool:
        return error_code == "METRIC_INVALID_AGGREGATION"

    def correct(self, mql, error, context):
        metric_name = error.value if isinstance(error.value, str) else None
        if not metric_name:
            return mql

        metric_defs = mql.get("metricDefinitions", {})
        defn = metric_defs.get(metric_name, {})
        agg = defn.get("aggregation", "")

        # 标准化聚合类型
        normalized = self._normalize_aggregation(agg)
        if normalized:
            defn["aggregation"] = normalized
            metric_defs[metric_name] = defn
            mql["metricDefinitions"] = metric_defs

        return mql

    def _normalize_aggregation(self, agg: str) -> Optional[str]:
        """标准化聚合类型"""
        if not agg:
            return "SUM"
        upper = agg.upper().replace(" ", "_")
        if upper in self.VALID_AGGS:
            return upper
        mapping = {
            "COUNTDISTINCT": "COUNT_DISTINCT",
            "COUNT_DISTINCTINCT": "COUNT_DISTINCT",
            "AVERAGE": "AVG",
            "MEAN": "AVG",
            "TOTAL": "SUM",
        }
        return mapping.get(upper)


class FixIndirectionsStrategy(BaseCorrectionStrategy):
    """修正 indirections 类型"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "METRIC_INVALID_INDIRECTIONS"

    def correct(self, mql, error, context):
        metric_name = error.value if isinstance(error.value, str) else None
        if not metric_name:
            return mql

        metric_defs = mql.get("metricDefinitions", {})
        defn = metric_defs.get(metric_name, {})
        indirections = defn.get("indirections")

        if not isinstance(indirections, list):
            defn["indirections"] = []
        else:
            # 标准化 indirections 中的每一项
            defn["indirections"] = [str(i) for i in indirections]

        metric_defs[metric_name] = defn
        mql["metricDefinitions"] = metric_defs
        return mql


class EmptyMetricsStrategy(BaseCorrectionStrategy):
    """处理空的 metrics"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "METRIC_EMPTY_METRICS"

    def correct(self, mql, error, context):
        # 如果有维度但没有指标，设置为空列表（纯维度查询）
        if mql.get("dimensions"):
            mql["metrics"] = []
        else:
            # 尝试使用 suggestion 中的指标
            if error.suggestion and error.suggestion != mql.get("metrics"):
                try:
                    suggested = json.loads(error.suggestion) if isinstance(error.suggestion, str) else error.suggestion
                    if isinstance(suggested, list):
                        mql["metrics"] = suggested
                except (json.JSONDecodeError, TypeError):
                    pass
        return mql


# ============================================================
# Dimensions 相关策略
# ============================================================

class DimensionNotFoundStrategy(BaseCorrectionStrategy):
    """修正不存在的维度"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "DIMENSION_DIMENSION_NOT_FOUND"

    def correct(self, mql, error, context):
        dim_name = error.value if isinstance(error.value, str) else None
        if not dim_name:
            return mql

        dims = mql.get("dimensions", [])
        idx = None
        for i, d in enumerate(dims):
            if d == dim_name:
                idx = i
                break

        if idx is None:
            return mql

        # 尝试模糊匹配
        actual_name = self._fuzzy_match(dim_name, context)
        if actual_name:
            dims[idx] = actual_name
        else:
            # 移除不存在的维度
            dims.pop(idx)

        mql["dimensions"] = dims
        return mql

    def _fuzzy_match(self, name: str, context: ValidationContext) -> Optional[str]:
        name_lower = name.lower().replace(" ", "").replace("_", "")
        candidates = []
        for d_name in context.dimension_names | context.dimension_display_names:
            d_lower = d_name.lower().replace(" ", "").replace("_", "")
            if name_lower in d_lower or d_lower in name_lower:
                candidates.append((d_name, len(d_lower)))
        if candidates:
            candidates.sort(key=lambda x: -x[1])
            return candidates[0][0]
        return None


class FixDimensionTypeStrategy(BaseCorrectionStrategy):
    """修正维度类型（非字符串→字符串）"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "DIMENSION_INVALID_DIMENSION_TYPE"

    def correct(self, mql, error, context):
        dims = mql.get("dimensions", [])
        if not isinstance(dims, list):
            dims = [dims] if dims else []

        dims = [str(d) for d in dims]
        mql["dimensions"] = dims
        return mql


class RemoveInvalidTimeSuffixStrategy(BaseCorrectionStrategy):
    """移除非时间维度上的时间后缀"""

    VALID_SUFFIXES = {"按天", "按周", "按月", "按季度", "按年",
                      "day", "week", "month", "quarter", "year"}

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "DIMENSION_INVALID_TIME_SUFFIX",
            "DIMENSION_UNKNOWN_TIME_SUFFIX",
        )

    def correct(self, mql, error, context):
        dim_name = error.value if isinstance(error.value, str) else None
        if not dim_name:
            return mql

        dims = mql.get("dimensions", [])
        idx = None
        for i, d in enumerate(dims):
            if d == dim_name:
                idx = i
                break

        if idx is None:
            return mql

        if "__" in dim_name:
            base, suffix = dim_name.split("__", 1)
            if error.code == "DIMENSION_UNKNOWN_TIME_SUFFIX":
                # 非标准后缀，移除后缀
                dims[idx] = base
            else:
                # 非时间维度不能用时间后缀
                dims[idx] = base

        mql["dimensions"] = dims
        return mql


# ============================================================
# Filters 相关策略
# ============================================================

class MoveFilterToHavingStrategy(BaseCorrectionStrategy):
    """将指标过滤从 filters 移到 having"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "FILTER_FILTER_METRIC_IN_WHERE"

    def correct(self, mql, error, context):
        filters = mql.get("filters", [])
        if not filters:
            return mql

        metric_fields = context.metric_names | context.metric_display_names

        if isinstance(filters, dict):
            # 结构化格式：提取指标字段名并从结构化树中移除
            metric_field_names = self._extract_metric_field_names_from_structured(filters, metric_fields)
            if not metric_field_names:
                return mql
            # 对结构化格式，移除包含指标字段的叶子条件
            new_filters = self._remove_conditions_by_fields(filters, metric_field_names)
            # 生成 having 条件字符串
            metric_filters = [f"[{f}] > 0" for f in metric_field_names]
            mql["filters"] = new_filters
            existing_having = mql.get("having")
            if existing_having:
                if isinstance(existing_having, str):
                    existing_having = [existing_having]
                mql["having"] = existing_having + metric_filters
            else:
                mql["having"] = metric_filters[0] if len(metric_filters) == 1 else metric_filters
            return mql

        if not isinstance(filters, list):
            return mql

        metric_filters = []
        remaining_filters = []

        for f in filters:
            if isinstance(f, dict):
                # 结构化条件在列表中：提取字段名判断
                fields = self._extract_fields_from_structured(f)
                if any(ref in metric_fields for ref in fields):
                    metric_filters.append(str(f))
                else:
                    remaining_filters.append(f)
            else:
                refs = re.findall(r"\[([^\]]+)\]", str(f))
                if any(ref in metric_fields for ref in refs):
                    metric_filters.append(f)
                else:
                    remaining_filters.append(f)

        if metric_filters:
            mql["filters"] = remaining_filters
            existing_having = mql.get("having")
            if existing_having:
                if isinstance(existing_having, str):
                    existing_having = [existing_having]
                mql["having"] = existing_having + metric_filters
            else:
                mql["having"] = metric_filters[0] if len(metric_filters) == 1 else metric_filters

        return mql

    def _extract_metric_field_names_from_structured(self, condition: dict, metric_fields: set) -> List[str]:
        """从结构化条件中提取属于指标的字段名"""
        result = []
        if "field" in condition:
            if condition["field"] in metric_fields:
                result.append(condition["field"])
        else:
            for sub in condition.get("conditions", []):
                result.extend(self._extract_metric_field_names_from_structured(sub, metric_fields))
        return result

    def _extract_fields_from_structured(self, condition: dict) -> List[str]:
        """从结构化条件中提取所有字段名"""
        result = []
        if "field" in condition:
            result.append(condition["field"])
        else:
            for sub in condition.get("conditions", []):
                result.extend(self._extract_fields_from_structured(sub))
        return result

    def _remove_conditions_by_fields(self, condition: dict, field_names: set) -> Optional[dict]:
        """从结构化条件树中移除包含指定字段的叶子条件，返回修剪后的树（空则返回 None）"""
        if "field" in condition:
            if condition["field"] in field_names:
                return None
            return condition
        # 分组条件：递归修剪
        new_conditions = []
        for sub in condition.get("conditions", []):
            trimmed = self._remove_conditions_by_fields(sub, field_names)
            if trimmed is not None:
                new_conditions.append(trimmed)
        if not new_conditions:
            return None
        new_cond = dict(condition)
        new_cond["conditions"] = new_conditions
        return new_cond


class FixFilterTypeStrategy(BaseCorrectionStrategy):
    """修正 filter 类型"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "FILTER_INVALID_FILTER_TYPE"

    def correct(self, mql, error, context):
        filters = mql.get("filters", [])
        if isinstance(filters, dict):
            # 已经是结构化格式，保持不变
            return mql
        elif isinstance(filters, str):
            mql["filters"] = [filters]
        elif isinstance(filters, list):
            # 将非字符串元素转为字符串
            new_filters = []
            for f in filters:
                if isinstance(f, str):
                    new_filters.append(f)
                elif isinstance(f, dict):
                    # 保留结构化条件
                    new_filters.append(f)
                else:
                    new_filters.append(str(f))
            mql["filters"] = new_filters
        else:
            mql["filters"] = []
        return mql


class FixFilterFieldNotFoundStrategy(BaseCorrectionStrategy):
    """修正 filter 中不存在的字段"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "FILTER_FIELD_NOT_FOUND"

    def correct(self, mql, error, context):
        filters = mql.get("filters", [])
        if not filters:
            return mql

        # 提取错误中引用的字段名
        field_name = error.value if isinstance(error.value, str) else None
        if not field_name:
            return mql

        # 模糊匹配字段
        all_fields = context.metric_names | context.metric_display_names | context.dimension_names | context.dimension_display_names
        best_match = self._fuzzy_match(field_name, all_fields)

        if not best_match:
            return mql

        if isinstance(filters, dict):
            # 结构化格式：递归替换字段名
            mql["filters"] = self._replace_field_in_structured(filters, field_name, best_match)
        elif isinstance(filters, list):
            new_filters = []
            for f in filters:
                if isinstance(f, dict):
                    new_filters.append(self._replace_field_in_structured(f, field_name, best_match))
                elif isinstance(f, str):
                    new_f = f.replace(f"[{field_name}]", f"[{best_match}]")
                    new_filters.append(new_f)
                else:
                    new_filters.append(f)
            mql["filters"] = new_filters

        return mql

    def _replace_field_in_structured(self, condition: dict, old_field: str, new_field: str) -> Optional[dict]:
        """在结构化条件中递归替换字段名"""
        if "field" in condition:
            if condition["field"] == old_field:
                new_cond = dict(condition)
                new_cond["field"] = new_field
                return new_cond
            return condition
        # 分组条件
        new_conditions = []
        for sub in condition.get("conditions", []):
            new_conditions.append(self._replace_field_in_structured(sub, old_field, new_field))
        new_cond = dict(condition)
        new_cond["conditions"] = new_conditions
        return new_cond

    def _fuzzy_match(self, name: str, all_fields: Set[str]) -> Optional[str]:
        name_lower = name.lower().replace(" ", "").replace("_", "")
        candidates = []
        for f in all_fields:
            f_lower = f.lower().replace(" ", "").replace("_", "")
            if name_lower in f_lower or f_lower in name_lower:
                candidates.append((f, len(f_lower)))
        if candidates:
            candidates.sort(key=lambda x: -x[1])
            return candidates[0][0]
        return None


class FixFilterParenthesesStrategy(BaseCorrectionStrategy):
    """修正 IN/NOT IN 表达式括号不匹配"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "FILTER_UNBALANCED_PARENTHESES"

    def correct(self, mql, error, context):
        # 结构化格式不需要括号修复
        filters = mql.get("filters", [])
        if isinstance(filters, dict):
            return mql
        if not isinstance(filters, list):
            return mql

        filter_expr = error.value if isinstance(error.value, str) else None
        if not filter_expr:
            return mql

        new_filters = []
        for f in filters:
            if isinstance(f, dict):
                new_filters.append(f)
            elif f == filter_expr:
                new_f = self._fix_parentheses(f)
                new_filters.append(new_f)
            else:
                new_filters.append(f)

        mql["filters"] = new_filters
        return mql

    def _fix_parentheses(self, expr: str) -> str:
        """修复括号匹配"""
        # 统计括号
        opens = expr.count("(")
        closes = expr.count(")")
        if opens > closes:
            expr = expr + ")" * (opens - closes)
        elif closes > opens:
            expr = "(" * (closes - opens) + expr
        return expr


# ============================================================
# Having 相关策略
# ============================================================

class FixHavingTypeStrategy(BaseCorrectionStrategy):
    """修正 having 类型"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "HAVING_INVALID_HAVING_TYPE"

    def correct(self, mql, error, context):
        having = mql.get("having")
        if isinstance(having, str):
            mql["having"] = having
        elif isinstance(having, list):
            mql["having"] = [str(h) for h in having]
        elif having:
            mql["having"] = str(having)
        return mql


# ============================================================
# OrderBy 相关策略
# ============================================================

class FixOrderByTypeStrategy(BaseCorrectionStrategy):
    """修正 orderBy 类型和结构"""

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "ORDERBY_INVALID_ORDERBY_TYPE",
            "ORDERBY_INVALID_ORDER_SPEC_TYPE",
            "ORDERBY_MISSING_FIELD",
        )

    def correct(self, mql, error, context):
        order_by = mql.get("orderBy")

        if error.code == "ORDERBY_INVALID_ORDERBY_TYPE":
            # orderBy 必须是列表
            if isinstance(order_by, dict):
                mql["orderBy"] = [order_by]
            elif isinstance(order_by, str):
                mql["orderBy"] = [{"field": order_by, "direction": "ASC"}]
            else:
                mql["orderBy"] = []

        elif error.code == "ORDERBY_INVALID_ORDER_SPEC_TYPE":
            # 元素必须是对象
            if isinstance(order_by, list):
                new_order = []
                for item in order_by:
                    if isinstance(item, str):
                        new_order.append({"field": item, "direction": "ASC"})
                    elif isinstance(item, dict):
                        new_order.append(item)
                mql["orderBy"] = new_order

        elif error.code == "ORDERBY_MISSING_FIELD":
            # 元素缺少 field
            if isinstance(order_by, list):
                for item in order_by:
                    if isinstance(item, dict) and not item.get("field"):
                        item["field"] = "metrics"  # 默认按指标排序

        return mql


class FixOrderByDirectionStrategy(BaseCorrectionStrategy):
    """修正 orderBy direction"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "ORDERBY_INVALID_DIRECTION"

    def correct(self, mql, error, context):
        order_by = mql.get("orderBy", [])
        if not isinstance(order_by, list):
            return mql

        for item in order_by:
            if isinstance(item, dict):
                direction = str(item.get("direction", "ASC")).upper()
                if direction not in ("ASC", "DESC"):
                    item["direction"] = "ASC"

        mql["orderBy"] = order_by
        return mql


# ============================================================
# Distinct / Limit 相关策略
# ============================================================

class FixDistinctTypeStrategy(BaseCorrectionStrategy):
    """修正 distinct 类型"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "DISTINCT_INVALID_DISTINCT_TYPE"

    def correct(self, mql, error, context):
        mql["distinct"] = bool(mql.get("distinct", False))
        return mql


class FixLimitStrategy(BaseCorrectionStrategy):
    """修正 limit 值"""

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "LIMIT_INVALID_LIMIT_TYPE",
            "LIMIT_INVALID_LIMIT_VALUE",
            "LIMIT_LIMIT_TOO_LARGE",
        )

    def correct(self, mql, error, context):
        limit = mql.get("limit")

        if error.code == "LIMIT_INVALID_LIMIT_TYPE":
            try:
                mql["limit"] = int(limit) if limit else 1000
            except (TypeError, ValueError):
                mql["limit"] = 1000

        elif error.code == "LIMIT_INVALID_LIMIT_VALUE":
            mql["limit"] = 1000

        elif error.code == "LIMIT_LIMIT_TOO_LARGE":
            # 警告级别，自动限制为 10000
            try:
                if limit is not None and int(limit) > 100000:
                    mql["limit"] = 10000
            except (TypeError, ValueError):
                mql["limit"] = 1000

        return mql


# ============================================================
# WindowFunctions 相关策略
# ============================================================

VALID_WINDOW_FUNCS = {
    "SUM", "AVG", "COUNT", "MAX", "MIN",
    "ROW_NUMBER", "RANK", "DENSE_RANK",
    "LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE",
}


class FixWindowFunctionsTypeStrategy(BaseCorrectionStrategy):
    """修正 windowFunctions 类型和结构"""

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "WINDOW_INVALID_WINDOW_FUNCTIONS_TYPE",
            "WINDOW_INVALID_WINDOW_SPEC_TYPE",
            "WINDOW_MISSING_WINDOW_ALIAS",
            "WINDOW_MISSING_WINDOW_FUNC",
            "WINDOW_INVALID_WINDOW_FUNC",
        )

    def correct(self, mql, error, context):
        wf = mql.get("windowFunctions")

        if error.code == "WINDOW_INVALID_WINDOW_FUNCTIONS_TYPE":
            if isinstance(wf, list):
                mql["windowFunctions"] = [w for w in wf if isinstance(w, dict)]
            else:
                mql["windowFunctions"] = []

        elif error.code == "WINDOW_INVALID_WINDOW_SPEC_TYPE":
            if isinstance(wf, list):
                mql["windowFunctions"] = [
                    w if isinstance(w, dict) else {"func": "SUM", "field": str(w)}
                    for w in wf
                ]

        elif error.code == "WINDOW_MISSING_WINDOW_ALIAS":
            if isinstance(wf, list):
                for i, w in enumerate(wf):
                    if isinstance(w, dict) and not w.get("alias"):
                        w["alias"] = f"window_{i+1}"

        elif error.code == "WINDOW_MISSING_WINDOW_FUNC":
            if isinstance(wf, list):
                for w in wf:
                    if isinstance(w, dict) and not w.get("func"):
                        w["func"] = "SUM"

        elif error.code == "WINDOW_INVALID_WINDOW_FUNC":
            func_name = error.value if isinstance(error.value, str) else None
            if func_name and isinstance(wf, list):
                normalized = func_name.upper().replace(" ", "_")
                for w in wf:
                    if isinstance(w, dict) and w.get("func", "").upper() == func_name.upper():
                        if normalized not in VALID_WINDOW_FUNCS:
                            w["func"] = "SUM"

        return mql


class FixWindowFieldStrategy(BaseCorrectionStrategy):
    """修正窗口函数字段不存在"""

    def can_handle(self, error_code: str) -> bool:
        return error_code == "WINDOW_WINDOW_FIELD_NOT_FOUND"

    def correct(self, mql, error, context):
        field_name = error.value if isinstance(error.value, str) else None
        if not field_name:
            return mql

        wf_list = mql.get("windowFunctions", [])
        if not isinstance(wf_list, list):
            return mql

        # 模糊匹配
        all_fields = context.metric_names | context.metric_display_names | context.dimension_names | context.dimension_display_names
        best_match = None
        fl = field_name.lower().replace(" ", "").replace("_", "")
        for f in all_fields:
            if fl in f.lower().replace(" ", "").replace("_", ""):
                best_match = f
                break

        if best_match:
            for w in wf_list:
                if isinstance(w, dict) and w.get("field") == field_name:
                    w["field"] = best_match

        return mql


# ============================================================
# Union 相关策略
# ============================================================

class FixUnionStrategy(BaseCorrectionStrategy):
    """修正 union 相关错误"""

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "UNION_INVALID_UNION_TYPE",
            "UNION_INVALID_UNION_TYPE_VALUE",
            "UNION_INVALID_UNION_QUERIES_TYPE",
            "UNION_UNION_TOO_FEW_QUERIES",
        )

    def correct(self, mql, error, context):
        union = mql.get("union")

        if error.code == "UNION_INVALID_UNION_TYPE":
            if not isinstance(union, dict):
                mql["union"] = None

        elif error.code == "UNION_INVALID_UNION_TYPE_VALUE":
            if isinstance(union, dict):
                union_type = union.get("type", "")
                if union_type not in ("", "ALL"):
                    union["type"] = "ALL"
                mql["union"] = union

        elif error.code == "UNION_INVALID_UNION_QUERIES_TYPE":
            if isinstance(union, dict):
                queries = union.get("queries", [])
                if not isinstance(queries, list):
                    union["queries"] = []
                mql["union"] = union

        elif error.code == "UNION_UNION_TOO_FEW_QUERIES":
            # 子查询不足 2 个，移除 union
            mql["union"] = None

        return mql


# ============================================================
# CTE 相关策略
# ============================================================

class FixCTEStrategy(BaseCorrectionStrategy):
    """修正 cte 相关错误"""

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "CTE_INVALID_CTE_TYPE",
            "CTE_INVALID_CTE_ITEM_TYPE",
            "CTE_MISSING_CTE_NAME",
            "CTE_DUPLICATE_CTE_NAME",
            "CTE_MISSING_CTE_QUERY",
            "CTE_INVALID_CTE_QUERY_TYPE",
        )

    def correct(self, mql, error, context):
        cte = mql.get("cte")

        if error.code == "CTE_INVALID_CTE_TYPE":
            if not isinstance(cte, list):
                mql["cte"] = None

        elif error.code == "CTE_INVALID_CTE_ITEM_TYPE":
            if isinstance(cte, list):
                mql["cte"] = [c for c in cte if isinstance(c, dict)]

        elif error.code == "CTE_MISSING_CTE_NAME":
            if isinstance(cte, list):
                for i, c in enumerate(cte):
                    if isinstance(c, dict) and not c.get("name"):
                        c["name"] = f"cte_{i+1}"

        elif error.code == "CTE_DUPLICATE_CTE_NAME":
            if isinstance(cte, list):
                seen_names = set()
                for c in cte:
                    if isinstance(c, dict):
                        name = c.get("name", "")
                        if name in seen_names:
                            counter = 1
                            while f"{name}_{counter}" in seen_names:
                                counter += 1
                            c["name"] = f"{name}_{counter}"
                        seen_names.add(c.get("name", ""))

        elif error.code == "CTE_MISSING_CTE_QUERY":
            if isinstance(cte, list):
                mql["cte"] = [c for c in cte if isinstance(c, dict) and c.get("query")]

        elif error.code == "CTE_INVALID_CTE_QUERY_TYPE":
            if isinstance(cte, list):
                mql["cte"] = [c for c in cte if isinstance(c, dict) and isinstance(c.get("query"), dict)]

        return mql


# ============================================================
# TimeConstraint 相关策略
# ============================================================

VALID_TIME_FUNCTIONS = {
    "TODAY", "YESTERDAY", "LAST_N_DAYS", "THIS_MONTH", "LAST_MONTH",
    "THIS_YEAR", "LAST_YEAR", "DateTrunc", "AddMonths", "DateAdd",
    "DateDiff", "NOW", "CURRENT_DATE", "CURRENT_TIMESTAMP",
}


class FixTimeConstraintStrategy(BaseCorrectionStrategy):
    """修正 timeConstraint 相关错误"""

    def can_handle(self, error_code: str) -> bool:
        return error_code in (
            "TIME_CONSTRAINT_INVALID_TIME_CONSTRAINT_TYPE",
            "TIME_CONSTRAINT_INVALID_TIME_FUNCTION",
        )

    def correct(self, mql, error, context):
        tc = mql.get("timeConstraint")

        if error.code == "TIME_CONSTRAINT_INVALID_TIME_CONSTRAINT_TYPE":
            mql["timeConstraint"] = str(tc) if tc else None

        elif error.code == "TIME_CONSTRAINT_INVALID_TIME_FUNCTION":
            # 尝试将 filters 中的时间条件移到 timeConstraint
            filters = mql.get("filters", [])
            if isinstance(filters, list):
                remaining = []
                for f in filters:
                    f_str = str(f)
                    # 检测是否包含时间函数
                    func_match = re.search(r'(\w+)\s*\(', f_str)
                    if func_match:
                        func_name = func_match.group(1).upper()
                        if func_name in VALID_TIME_FUNCTIONS:
                            mql["timeConstraint"] = f_str
                            continue
                    remaining.append(f)
                mql["filters"] = remaining

        return mql


# ============================================================
# 纠错编排器
# ============================================================

# 自动注册所有策略
_ALL_STRATEGIES: List[BaseCorrectionStrategy] = [
    # Metrics
    CompleteMetricDefStrategy(),
    FixAggregationStrategy(),
    FixIndirectionsStrategy(),
    EmptyMetricsStrategy(),
    # Dimensions
    DimensionNotFoundStrategy(),
    FixDimensionTypeStrategy(),
    RemoveInvalidTimeSuffixStrategy(),
    # Filters
    MoveFilterToHavingStrategy(),
    FixFilterTypeStrategy(),
    FixFilterFieldNotFoundStrategy(),
    FixFilterParenthesesStrategy(),
    # Having
    FixHavingTypeStrategy(),
    # OrderBy
    FixOrderByTypeStrategy(),
    FixOrderByDirectionStrategy(),
    # Distinct / Limit
    FixDistinctTypeStrategy(),
    FixLimitStrategy(),
    # WindowFunctions
    FixWindowFunctionsTypeStrategy(),
    FixWindowFieldStrategy(),
    # Union
    FixUnionStrategy(),
    # CTE
    FixCTEStrategy(),
    # TimeConstraint
    FixTimeConstraintStrategy(),
]

# 构建错误码 → 策略列表的映射
_STRATEGY_MAP: Dict[str, List[BaseCorrectionStrategy]] = {}
_ALL_ERROR_CODES = [
    # Metrics
    "METRIC_EMPTY_METRICS", "METRIC_MISSING_METRIC_DEF",
    "METRIC_INVALID_METRIC_DEF_TYPE", "METRIC_MISSING_REF_METRIC",
    "METRIC_INVALID_REF_METRIC", "METRIC_INVALID_AGGREGATION",
    "METRIC_INVALID_INDIRECTIONS",
    # Dimensions
    "DIMENSION_INVALID_DIMENSION_TYPE", "DIMENSION_DIMENSION_NOT_FOUND",
    "DIMENSION_INVALID_TIME_SUFFIX", "DIMENSION_UNKNOWN_TIME_SUFFIX",
    # Filters
    "FILTER_INVALID_FILTER_TYPE", "FILTER_FILTER_METRIC_IN_WHERE",
    "FILTER_FIELD_NOT_FOUND", "FILTER_UNBALANCED_PARENTHESES",
    # Having
    "HAVING_INVALID_HAVING_TYPE",
    # OrderBy
    "ORDERBY_INVALID_ORDERBY_TYPE", "ORDERBY_INVALID_ORDER_SPEC_TYPE",
    "ORDERBY_MISSING_FIELD", "ORDERBY_INVALID_DIRECTION",
    # Distinct / Limit
    "DISTINCT_INVALID_DISTINCT_TYPE",
    "LIMIT_INVALID_LIMIT_TYPE", "LIMIT_INVALID_LIMIT_VALUE",
    "LIMIT_LIMIT_TOO_LARGE",
    # WindowFunctions
    "WINDOW_INVALID_WINDOW_FUNCTIONS_TYPE", "WINDOW_INVALID_WINDOW_SPEC_TYPE",
    "WINDOW_MISSING_WINDOW_ALIAS", "WINDOW_MISSING_WINDOW_FUNC",
    "WINDOW_INVALID_WINDOW_FUNC", "WINDOW_WINDOW_FIELD_NOT_FOUND",
    # Union
    "UNION_INVALID_UNION_TYPE", "UNION_INVALID_UNION_TYPE_VALUE",
    "UNION_INVALID_UNION_QUERIES_TYPE", "UNION_UNION_TOO_FEW_QUERIES",
    # CTE
    "CTE_INVALID_CTE_TYPE", "CTE_INVALID_CTE_ITEM_TYPE",
    "CTE_MISSING_CTE_NAME", "CTE_DUPLICATE_CTE_NAME",
    "CTE_MISSING_CTE_QUERY", "CTE_INVALID_CTE_QUERY_TYPE",
    # TimeConstraint
    "TIME_CONSTRAINT_INVALID_TIME_CONSTRAINT_TYPE",
    "TIME_CONSTRAINT_INVALID_TIME_FUNCTION",
]
for _s in _ALL_STRATEGIES:
    for _c in _ALL_ERROR_CODES:
        if _s.can_handle(_c):
            _STRATEGY_MAP.setdefault(_c, []).append(_s)


class MQLCorrector:
    """
    MQL 纠错器（策略模式）

    将校验错误分发到对应的修正策略，支持全部 49 个错误码。
    覆盖 12 个 MQL 字段：metrics, metricDefinitions, dimensions,
    timeConstraint, filters, having, orderBy, distinct, limit,
    windowFunctions, union, cte
    """

    def __init__(self, db: Session):
        self.db = db
        self.validator = MQLCompositeValidator(db)
        self.context = self.validator.context

    def correct(
        self,
        mql: Dict[str, Any],
        errors: List[ValidationError],
    ) -> Dict[str, Any]:
        """
        根据校验错误修正 MQL

        Args:
            mql: 原始 MQL
            errors: 校验错误列表

        Returns:
            修正后的 MQL
        """
        corrected = copy.deepcopy(mql)
        corrections_made = []

        for error in errors:
            # WARNING 级别仅提供 suggestion，不自动修正
            if error.severity.value == "WARNING":
                continue

            strategies = _STRATEGY_MAP.get(error.code, [])
            for strategy in strategies:
                try:
                    corrected = strategy.correct(corrected, error, self.context)
                    corrections_made.append({
                        "code": error.code,
                        "message": error.message,
                        "strategy": strategy.__class__.__name__,
                    })
                except Exception as e:
                    logger.warning(f"Correction strategy {strategy.__class__.__name__} "
                                   f"failed for {error.code}: {e}")

        if corrections_made:
            logger.info(f"MQL correction applied {len(corrections_made)} fixes: "
                        f"{[c['code'] for c in corrections_made]}")

        return corrected

    def correct_and_validate(
        self,
        mql: Dict[str, Any],
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        迭代纠错：修正后重新校验，直到没有错误或达到最大迭代次数

        Args:
            mql: 原始 MQL
            max_iterations: 最大迭代次数

        Returns:
            修正后的 MQL
        """
        current_mql = copy.deepcopy(mql)

        for i in range(max_iterations):
            result = self.validator.validate(current_mql)
            if result.is_valid:
                logger.info(f"MQL correction converged after {i} iteration(s)")
                break

            # 仅修正 ERROR 级别的错误
            errors = [e for e in result.errors if e.severity.value == "ERROR"]
            if not errors:
                break

            current_mql = self.correct(current_mql, errors)

        return current_mql

    def get_unfixable_errors(
        self,
        mql: Dict[str, Any],
    ) -> List[ValidationError]:
        """
        获取无法自动修正的错误列表（需要 LLM 介入）

        Args:
            mql: 当前 MQL

        Returns:
            无法自动修正的错误列表
        """
        result = self.validator.validate(mql)
        # 先尝试自动修正
        corrected = self.correct(mql, result.errors)
        # 重新验证
        final_result = self.validator.validate(corrected)
        return [e for e in final_result.errors if e.severity.value == "ERROR"]


def correct_mql(mql: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """
    便捷函数：自动修正 MQL

    Args:
        mql: MQL 对象
        db: 数据库会话

    Returns:
        修正后的 MQL
    """
    corrector = MQLCorrector(db)
    return corrector.correct_and_validate(mql)
