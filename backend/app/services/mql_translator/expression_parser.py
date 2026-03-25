"""
expression_parser.py - MQL 表达式解析器

将 MQL 中的 `[字段名]` 占位符表达式解析为 sqlglot AST 节点。
支持：
- 字段引用：[渠道] -> Column
- 带别名字段：[日期__按月] -> Column with alias
- 时间维度格式化：[日期__按月] -> DateFormat(Column, 'YYYY-MM')
- 指标引用：[MetricName] -> 聚合表达式
- 嵌套表达式：([字段] + [字段]) * 100
- 时间函数：TODAY(), LAST_N_DAYS(30), etc.

与旧版 process_mql_expression 的区别：
- 旧版：字符串拼接 + 正则替换
- 新版：递归下降解析器，生成 sqlglot AST 节点
- 新版：使用 ibis + sqlglot 实现多数据源时间函数适配
"""

import re
import sqlglot
from sqlglot import exp
from typing import Dict, Optional, Tuple, List, Any

from app.services.mql_translator.semantic import SemanticContext, FieldRef, MetricRef
from app.services.mql_translator.time_function_handler import TimeFunctionHandler, TimeFilterBuilder


class ExpressionParser:
    """
    MQL 表达式解析器

    将形如 `"[渠道] = '线上' AND [订单金额] > 1000"` 的表达式
    解析为 sqlglot AST。

    使用方式：
        parser = ExpressionParser(semantic_context, dialect="mysql")
        ast = parser.parse("[销售额] > 1000", is_where=True)
    """

    def __init__(self, semantic: SemanticContext, dialect: str = "mysql"):
        self.semantic = semantic
        self.dialect = dialect
        self.time_handler = TimeFunctionHandler(dialect)
        self.time_filter_builder = TimeFilterBuilder(dialect)

    def parse(
        self,
        expr: str,
        is_where: bool = False,
        skip_formatting: bool = False,
    ) -> exp.Expression:
        """
        解析 MQL 表达式为 sqlglot AST

        Args:
            expr: MQL 表达式字符串，如 "[渠道] = '线上'"
            is_where: 是否为 WHERE 子句（某些转换逻辑不同）
            skip_formatting: 是否跳过时间格式化（WHERE 中通常跳过）

        Returns:
            sqlglot Expression 节点
        """
        if not expr or expr in ("", "true", "1=1"):
            return exp.true()

        # 预处理：处理 MQL 时间函数
        processed = self._preprocess_time_functions(expr)

        # 解析方括号引用为占位符（避免与 sqlglot 冲突）
        processed = self._replace_field_refs(processed)

        # 解析为 sqlglot AST
        try:
            ast = sqlglot.parse_one(processed, dialect=self.dialect)
        except Exception:
            # 解析失败，返回原字符串（作为条件）
            return exp.column(processed)

        # 后处理：将占位符替换回字段引用
        ast = self._restore_field_refs(ast, is_where=is_where, skip_formatting=skip_formatting)

        return ast

    def _preprocess_time_functions(self, expr: str) -> str:
        """
        预处理 MQL 时间函数
        
        使用 TimeFunctionHandler 将 MQL 时间函数转换为目标方言 SQL。
        支持：TODAY(), YESTERDAY(), LAST_N_DAYS(n), THIS_MONTH(), etc.
        """
        result = expr
        
        # 使用 TimeFunctionHandler 的正则匹配所有 MQL 时间函数
        # 匹配格式：FUNC_NAME(args) 或 FUNC_NAME()
        time_func_pattern = r'\b(' + '|'.join([
            'TODAY', 'YESTERDAY', 'TOMORROW',
            'LAST_N_DAYS', 'LAST_N_MONTHS', 'LAST_N_YEARS',
            'NEXT_N_DAYS', 'NEXT_N_MONTHS',
            'THIS_WEEK', 'THIS_MONTH', 'THIS_QUARTER', 'THIS_YEAR',
            'ADD_MONTHS'
        ]) + r')\s*\([^)]*\)'
        
        def replace_time_func(match):
            func_str = match.group(0)
            try:
                # 使用 TimeFunctionHandler 转换
                return self.time_handler.parse_and_render(func_str)
            except Exception:
                # 转换失败，返回原值
                return func_str
        
        result = re.sub(time_func_pattern, replace_time_func, result, flags=re.IGNORECASE)
        
        return result

    # 占位符用于方括号引用
    FIELD_PLACEHOLDER_PREFIX = "__MQL_FIELD_REF_"
    _field_ref_counter = 0

    def _replace_field_refs(self, expr: str) -> str:
        """将 [字段名] 替换为占位符，避免与 sqlglot 解析冲突"""
        result = expr

        def replace_match(m):
            field_name = m.group(1)
            # 存储到列表供后续恢复
            idx = self._field_ref_counter
            self._field_ref_counter += 1
            self._field_ref_map[idx] = field_name
            return f"{self.FIELD_PLACEHOLDER_PREFIX}{idx}__"

        self._field_ref_map: Dict[int, str] = {}
        result = re.sub(r"\[([^\]]+)\]", replace_match, result)
        return result

    def _restore_field_refs(
        self,
        ast: exp.Expression,
        is_where: bool = False,
        skip_formatting: bool = False,
    ) -> exp.Expression:
        """将占位符恢复为字段引用（构建 sqlglot AST）"""

        def visit(node):
            if isinstance(node, exp.Column) and isinstance(node.this, exp.Identifier):
                col_name = node.this.this
                if col_name.startswith(self.FIELD_PLACEHOLDER_PREFIX):
                    idx_str = col_name.replace(self.FIELD_PLACEHOLDER_PREFIX, "").replace("__", "")
                    try:
                        idx = int(idx_str)
                        field_name = self._field_ref_map.get(idx, col_name)
                    except (ValueError, IndexError):
                        return node

                    # 构建字段 AST
                    field_ref = self.semantic.resolve_field(field_name)
                    if field_ref:
                        # 获取正确的列表达式（处理 JOIN 视图）
                        column_expr = field_ref.physical_column

                        # 如果有源视图，需要添加表别名
                        if field_ref.source_view_id:
                            column_expr = self.semantic.get_view_column_expression(
                                field_ref.source_view_id, column_expr
                            )

                        # 解析列名字段
                        if "." in column_expr:
                            parts = column_expr.split(".", 1)
                            new_node = exp.column(parts[1], table=parts[0])
                        else:
                            new_node = exp.column(column_expr)

                        # 如果需要应用时间格式化
                        if (
                            not skip_formatting
                            and field_ref.dimension_type == "time"
                            and field_ref.format_config
                        ):
                            fmt = field_ref.format_config.get("default_format")
                            if fmt:
                                new_node = self._apply_date_format(new_node, fmt)

                        return new_node
                    else:
                        # 无法解析为维度，检查是否为指标引用（用于 HAVING）
                        metric_ref = self.semantic.resolve_metric(field_name)
                        if metric_ref:
                            # HAVING 中引用指标别名，直接使用别名名
                            new_node = exp.column(field_name)
                            return new_node
                        # 最终 fallback：使用原始字段名作为列名
                        new_node = exp.column(field_name)
                        return new_node

            # 递归访问子节点
            for key, value in node.args.items():
                if value is None:
                    continue
                if isinstance(value, list):
                    new_list = []
                    changed = False
                    for item in value:
                        if isinstance(item, exp.Expression):
                            new_item = visit(item)
                            if new_item is not None and new_item is not item:
                                changed = True
                            new_list.append(new_item if new_item is not None else item)
                        else:
                            new_list.append(item)
                    if changed:
                        node.set(key, new_list)
                elif isinstance(value, exp.Expression):
                    new_value = visit(value)
                    if new_value is not None and new_value is not value:
                        node.set(key, new_value)

            return node

        return visit(ast)

    def _apply_date_format(self, col_node: exp.Column, fmt: str) -> exp.Expression:
        """应用日期格式化表达式"""
        if self.dialect == "mysql":
            mysql_fmt = self._to_mysql_date_format(fmt)
            return exp.Anonymous(this="DATE_FORMAT", expressions=[col_node, exp.Literal.string(mysql_fmt)])
        elif self.dialect == "postgresql":
            pg_fmt = self._to_postgresql_date_format(fmt)
            return exp.Anonymous(this="TO_CHAR", expressions=[col_node, exp.Literal.string(pg_fmt)])
        elif self.dialect == "clickhouse":
            return exp.Anonymous(this="FORMAT", expressions=[col_node, exp.Literal.string(fmt.lower())])
        return col_node

    def _to_mysql_date_format(self, fmt: str) -> str:
        """MQL 格式 -> MySQL DATE_FORMAT 格式"""
        mapping = {
            "YYYY-MM-DD": "%Y-%m-%d",
            "YYYY-MM": "%Y-%m",
            "YYYY": "%Y",
            "YYYY-WW": "%Y-%v",
            "YYYY-MM-DD HH:mm": "%Y-%m-%d %H:%i",
            "YYYY-MM-DD HH:mm:ss": "%Y-%m-%d %H:%i:%s",
        }
        return mapping.get(fmt, "%Y-%m-%d")

    def _to_postgresql_date_format(self, fmt: str) -> str:
        """MQL 格式 -> PostgreSQL to_char 格式"""
        mapping = {
            "YYYY-MM-DD": "YYYY-MM-DD",
            "YYYY-MM": "YYYY-MM",
            "YYYY": "YYYY",
            "YYYY-WW": "IYYY-IW",
            "YYYY-MM-DD HH:mm": "YYYY-MM-DD HH24:MI",
            "YYYY-MM-DD HH:mm:ss": "YYYY-MM-DD HH24:MI:SS",
        }
        return mapping.get(fmt, "YYYY-MM-DD")

    def parse_field_expression(
        self,
        field_name: str,
        is_where: bool = False,
    ) -> Tuple[exp.Expression, Optional[str]]:
        """
        解析字段名为 SQL 表达式

        Returns:
            (sqlglot Expression, alias) 元组
        """
        # 解析后缀
        actual_name = field_name
        alias = field_name
        if "__" in field_name:
            actual_name, suffix = field_name.split("__", 1)
            alias = field_name  # 别名保留原始形式

        # 查找字段引用
        field_ref = self.semantic.resolve_field(actual_name)
        if not field_ref:
            # 找不到，返回原名字段
            return exp.column(actual_name), alias

        # 获取物理列表达式
        col_expr = field_ref.physical_column
        if field_ref.source_view_id:
            col_expr = self.semantic.get_view_column_expression(
                field_ref.source_view_id, col_expr
            )

        # 解析列名字段
        if "." in col_expr:
            parts = col_expr.split(".", 1)
            node = exp.column(parts[1], table=parts[0])
        else:
            node = exp.column(col_expr)

        # 应用时间格式化
        time_fmt = self.semantic.get_time_format_for_field(field_name)
        if time_fmt and not is_where and field_ref.dimension_type == "time":
            node = self._apply_date_format(node, time_fmt)

        return node, alias

    def build_metric_expression(
        self,
        metric_name: str,
        metric_def: Dict[str, Any],
    ) -> exp.Expression:
        """
        构建指标表达式（SUM(col), AVG(col) 等）

        处理 indirectations 如 yoy_growth, mom_growth
        """
        ref_metric_name = metric_def.get("refMetric", metric_name)
        indirections = metric_def.get("indirections", [])

        # 查找指标引用
        metric_ref = self.semantic.resolve_metric(ref_metric_name)
        if not metric_ref:
            return exp.Literal.number(0)

        # 构建基础表达式
        if metric_ref.metric_type == "basic":
            if metric_ref.calculation_method == "expression" and metric_ref.calculation_formula:
                # 使用公式
                return self.parse(metric_ref.calculation_formula)
            else:
                # 使用聚合
                col = metric_ref.measure_column
                if metric_ref.source_view_id:
                    col = self.semantic.get_view_column_expression(
                        metric_ref.source_view_id, col
                    )

                # 拆分 table.column 格式
                if "." in col:
                    parts = col.split(".", 1)
                    col_node = exp.column(parts[1], table=parts[0])
                else:
                    col_node = exp.column(col)

                # COUNT_DISTINCT 需要特殊处理
                if metric_ref.aggregation == "COUNT_DISTINCT":
                    return exp.Count(
                        this=exp.Distinct(expressions=[col_node])
                    )
                else:
                    agg_func = self._get_agg_func(metric_ref.aggregation)
                    return agg_func(this=col_node)

        elif metric_ref.metric_type == "derived":
            base_ref = None
            if metric_ref.base_metric_id:
                for m in self.semantic.metrics.values():
                    if m.name == metric_ref.base_metric_id or (
                        hasattr(m, 'id') and m.name == metric_ref.base_metric_id
                    ):
                        base_ref = m
                        break

            base_expr = self.build_metric_expression(
                ref_metric_name,
                {"refMetric": ref_metric_name, "indirections": []}
            ) if base_ref else exp.Literal.number(0)

            # 处理派生类型
            if metric_ref.derivation_type in ("yoy", "yoy_growth"):
                # 使用 LAG 窗口函数实现真实同比
                return self._build_yoy_expression(base_expr, metric_ref.derivation_type)
            elif metric_ref.derivation_type in ("mom", "mom_growth"):
                return self._build_mom_expression(base_expr, metric_ref.derivation_type)

            return base_expr

        elif metric_ref.metric_type == "composite":
            formula = metric_ref.calculation_formula or "0"
            return self.parse(formula)

        return exp.Literal.number(0)

    def _get_agg_func(self, agg_type: str):
        """获取聚合函数节点"""
        agg_map = {
            "SUM": exp.Sum,
            "COUNT": exp.Count,
            "AVG": exp.Avg,
            "MAX": exp.Max,
            "MIN": exp.Min,
            "COUNT_DISTINCT": lambda **kwargs: exp.Count(
                this=exp.Distinct(expressions=[kwargs.get("this", exp.column("*"))])
            ),
        }
        return agg_map.get(agg_type, exp.Sum)

    def _build_yoy_expression(self, base_expr: exp.Expression, derivation_type: str) -> exp.Expression:
        """
        构建同比表达式：使用 LAG 窗口函数

        YoY Growth = (current - lag_12) / lag_12 * 100
        """
        # LAG(base_expr, 12) OVER (ORDER BY date_col)
        lag_expr = exp.Lag(this=base_expr, offset=exp.Literal.number(12))
        window_lag = exp.Window(this=lag_expr)

        if derivation_type == "yoy_growth":
            # (base - lag) / NULLIF(lag, 0) * 100
            nullif_lag = exp.func("NULLIF", lag_expr, exp.Literal.number(0))
            diff = exp.Sub(this=base_expr, expression=lag_expr)
            return exp.Mul(
                this=exp.Div(this=diff, expression=nullif_lag),
                expression=exp.Literal.number(100)
            )

        return base_expr

    def _build_mom_expression(self, base_expr: exp.Expression, derivation_type: str) -> exp.Expression:
        """
        构建环比表达式：使用 LAG 窗口函数

        MoM Growth = (current - lag_1) / lag_1 * 100
        """
        lag_expr = exp.Lag(this=base_expr, offset=exp.Literal.number(1))
        window_lag = exp.Window(this=lag_expr)

        if derivation_type == "mom_growth":
            nullif_lag = exp.func("NULLIF", lag_expr, exp.Literal.number(0))
            diff = exp.Sub(this=base_expr, expression=lag_expr)
            return exp.Mul(
                this=exp.Div(this=diff, expression=nullif_lag),
                expression=exp.Literal.number(100)
            )

        return base_expr