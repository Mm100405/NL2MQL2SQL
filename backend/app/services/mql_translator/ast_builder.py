"""
ast_builder.py - MQL AST 构建器

将 MQL JSON 对象转换为 sqlglot AST（SELECT 语句）。

核心改进（对比旧版 translate_mql_to_sql 字符串拼接）：
1. 使用 sqlglot AST 节点构建 SQL，避免字符串拼接错误
2. 支持 ORDER BY, HAVING, DISTINCT 等新 SQL 特性
3. 窗口函数、CTE、UNION 等高级特性在 advanced_sql.py 中实现
4. 修复 YoY/MoM 硬编码问题（使用真实 LAG 窗口函数）
5. 修复 COUNT_DISTINCT 语法错误

使用方式：
    builder = MQLASTBuilder(semantic_context, dialect="mysql")
    select = builder.build(mql)
    sql = select.sql(dialect="mysql")
"""

from typing import Dict, List, Optional, Any, Tuple
import sqlglot
from sqlglot import exp

from app.services.mql_translator.semantic import SemanticContext, ViewRef, DatasetRef
from app.services.mql_translator.expression_parser import ExpressionParser


class MQLASTBuilder:
    """
    MQL -> sqlglot AST 转换器

    将 MQL JSON 结构：
    {
        "metrics": ["销售额"],
        "metricDefinitions": {"销售额": {"refMetric": "gmv", "indirections": []}},
        "dimensions": ["日期__按月", "渠道"],
        "filters": ["[渠道] = '线上'"],
        "timeConstraint": "[日期] >= LAST_N_DAYS(30)",
        "limit": 1000
    }

    转换为 sqlglot SELECT AST。
    """

    def __init__(self, semantic: SemanticContext, dialect: str = "mysql"):
        self.semantic = semantic
        self.dialect = dialect
        self.expr_parser = ExpressionParser(semantic, dialect)

        # 当前构建状态
        self._current_view: Optional[ViewRef] = None
        self._used_view: Optional[ViewRef] = None
        self._is_cte_source: bool = False  # 主查询是否引用 CTE 作为数据源

    def build(self, mql: Dict[str, Any]) -> exp.Expression:
        """
        将 MQL 构建为 sqlglot AST

        支持基础查询和高级特性（CTE、UNION、窗口函数）：
        - 如果 MQL 包含 cte 字段，构建 WITH ... AS ... SELECT 语句
        - 如果 MQL 包含 union 字段，构建 UNION / UNION ALL 语句
        - 如果 MQL 包含 windowFunctions，在 SELECT 中添加窗口函数列

        Args:
            mql: MQL JSON 对象

        Returns:
            sqlglot 表达式（Select / Union / CTE）
        """
        # === 高级特性：CTE（最外层包裹） ===
        cte_defs = mql.get("cte")
        if cte_defs and isinstance(cte_defs, list) and len(cte_defs) > 0:
            return self._build_with_cte(mql, cte_defs)

        # === 构建（支持 UNION 和基础 SELECT，但不支持 CTE） ===
        return self._build_without_cte(mql)

    def _build_without_cte(self, mql: Dict[str, Any]) -> exp.Expression:
        """
        构建不包含 CTE 的查询（支持 UNION 和基础 SELECT）

        这个方法用于：
        1. 主查询构建（当没有 CTE 时）
        2. CTE 子查询构建（CTE 内部不能再有 CTE）

        当使用 UNION 时，与 union 同级的字段会被完全忽略
        只处理 union、limit、queryResultType、cte 等允许的字段

        Args:
            mql: MQL JSON 对象

        Returns:
            sqlglot 表达式（Select / Union）
        """
        # 检测是否使用 UNION
        has_union = mql.get("union") is not None

        # 当使用 UNION 时，构建临时MQL，只包含允许的字段
        if has_union:
            allowed_fields = {"union", "limit", "queryResultType", "cte"}
            filtered_mql = {k: v for k, v in mql.items() if k in allowed_fields}
            return self._build_union_query_or_select(filtered_mql)
        else:
            # 没有 UNION，正常处理
            return self._build_union_query_or_select(mql)

    def _build_union_query_or_select(self, mql: Dict[str, Any]) -> exp.Expression:
        """辅助方法：处理UNION或基础SELECT"""
        # === 高级特性：UNION ===
        union_def = mql.get("union")
        if union_def and isinstance(union_def, dict):
            queries = union_def.get("queries", [])
            union_type = union_def.get("type", "")
            if len(queries) >= 2:
                return self._build_union_query(queries, union_type)

        # === 基础 SELECT（含窗口函数） ===
        return self._build_base_select(mql)

    def _build_base_select(self, mql: Dict[str, Any]) -> exp.Select:
        """构建基础 SELECT 语句（含窗口函数支持）"""
        # 标记是否引用 CTE 作为数据源
        self._is_cte_source = bool(mql.get("from_cte"))

        # 确定使用的视图和数据源方言
        # 如果使用 from_cte，提前设置 _used_view（在构建SELECT子句之前）
        if self._is_cte_source:
            # CTE场景：_used_view 在 _build_from_clause 中设置
            # 但我们需要在这里先设置，因为 _build_select_clause 会用到
            from_cte = mql.get("from_cte")
            if isinstance(from_cte, str):
                self._used_view = type('ViewRef', (), {
                    'name': from_cte,
                    'id': None,
                    'display_name': from_cte,
                    'view_type': 'cte',
                    'datasource_id': None,
                    'base_table_id': None,
                    'join_config': None,
                    'custom_sql': None,
                    'columns': []
                })()
            datasource_id = None
        else:
            # 非CTE场景：从metricDefinitions中查找视图
            self._used_view, datasource_id = self.semantic.get_used_view(mql)

        if datasource_id is None and self._used_view and self._used_view.datasource_id:
            datasource_id = self._used_view.datasource_id

        # 更新方言（如果可能）
        if datasource_id:
            self.dialect = self.semantic.get_dialect(datasource_id)
            self.expr_parser.dialect = self.dialect

        # 构建 SELECT 语句
        select = exp.Select()

        # 1. SELECT 子句（维度 + 指标）
        select_expressions, group_by_expressions = self._build_select_clause(mql)
        for expr in select_expressions:
            select.append("expressions", expr)

        # 1.5 窗口函数（追加到 SELECT 子句）
        # 传入 select_expressions 用于解析指标别名到实际表达式
        window_expressions = self._build_window_function_expressions(mql, select_expressions)
        for expr in window_expressions:
            select.append("expressions", expr)

        # 2. FROM 子句 + JOIN
        from_clause, join_nodes = self._build_from_clause(mql)
        if from_clause:
            if isinstance(from_clause.this, exp.Subquery):
                select = select.from_(from_clause.this)
            elif isinstance(from_clause.this, exp.Table):
                select = select.from_(from_clause.this)
            else:
                select.set("from", from_clause)

        # 附加 JOIN 节点到 Select（sqlglot 30 中 JOIN 不属于 From，属于 Select）
        if join_nodes:
            select.set("joins", join_nodes)

        # 3. WHERE 子句
        where_clause = self._build_where_clause(mql)
        if where_clause:
            select.set("where", exp.Where(this=where_clause))

        # 4. GROUP BY 子句
        if group_by_expressions:
            select.set(
                "group",
                exp.Group(expressions=group_by_expressions)
            )

        # 5. HAVING 子句
        having_clause = self._build_having_clause(mql)
        if having_clause:
            select.set("having", exp.Having(this=having_clause))

        # 6. ORDER BY 子句
        all_select_exprs = select_expressions + window_expressions
        order_by_clause = self._build_order_by_clause(mql, all_select_exprs)
        if order_by_clause:
            select.set("order", order_by_clause)

        # 7. LIMIT 子句（使用 select.limit() 方法避免 sqlglot 30 bug）
        limit = mql.get("limit", 1000)
        select = select.limit(limit)

        # 8. DISTINCT
        if mql.get("distinct"):
            select.set("distinct", exp.Distinct())

        return select

    def _build_window_function_expressions(
        self, 
        mql: Dict[str, Any],
        select_exprs: List[exp.Expression] = None
    ) -> List[exp.Expression]:
        """从 MQL 的 windowFunctions 字段构建窗口函数 SELECT 表达式
        
        Args:
            mql: MQL 对象
            select_exprs: 已构建的 SELECT 表达式列表，用于解析指标别名到实际表达式
        """
        window_funcs = mql.get("windowFunctions")
        if not window_funcs or not isinstance(window_funcs, list):
            return []

        from app.services.mql_translator.advanced_sql import AdvancedSQLBuilder
        adv_builder = AdvancedSQLBuilder(self.semantic, self.dialect)

        # 构建字段解析器：从 select_exprs 中查找字段对应的表达式
        def field_resolver(field_name: str) -> Optional[exp.Expression]:
            """将字段名解析为 SQL 表达式
            
            对于指标别名（如"上报数"），返回完整的聚合表达式（如 SUM(t0.report_num)）
            对于维度或普通列，返回 None（由调用方处理为列引用）
            """
            if not select_exprs:
                return None
            
            # 在 select_exprs 中查找别名匹配的表达式
            for expr in select_exprs:
                alias = None
                # 获取表达式的别名
                if hasattr(expr, 'alias') and expr.alias:
                    alias = expr.alias
                elif hasattr(expr, 'this') and hasattr(expr.this, 'alias') and expr.this.alias:
                    alias = expr.this.alias
                
                if alias == field_name:
                    # 找到匹配的表达式，返回其内部表达式（去掉别名）
                    # 例如：SUM(t0.report_num) AS `上报数` -> SUM(t0.report_num)
                    if hasattr(expr, 'this'):
                        return expr.this
                    elif hasattr(expr, 'copy'):
                        # 对于复杂表达式，返回副本
                        inner = expr.copy()
                        # 清除别名
                        if hasattr(inner, 'set'):
                            inner.set("alias", None)
                        return inner
                    return expr
            
            return None

        expressions = []
        for idx, wf_spec in enumerate(window_funcs):
            if not isinstance(wf_spec, dict):
                continue
            try:
                window_node, alias = adv_builder.build_window_function(wf_spec, field_resolver)
                # 设置别名
                window_node = window_node.as_(alias)
                expressions.append(window_node)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to build window function: {wf_spec}, error: {e}")

        return expressions

    def _build_with_cte(self, mql: Dict[str, Any], cte_defs: list) -> exp.Expression:
        """
        构建 WITH ... AS ... 主查询

        注意：CTE 子查询中可以使用 UNION，但不能嵌套 CTE
        """
        cte_nodes = []  # 初始化CTE节点列表

        # 构建CTE时收集列信息
        for cte_def in cte_defs:
            name = cte_def.get("name")
            query_mql = cte_def.get("query")
            if not name or not query_mql:
                continue

            # 收集列信息并注册到SemanticContext
            metrics = query_mql.get("metrics", [])
            dimensions = query_mql.get("dimensions", [])
            constants = query_mql.get("constants", [])
            window_funcs = query_mql.get("windowFunctions", [])

            # 提取窗口函数别名
            window_function_aliases = []
            if window_funcs:
                for wf in window_funcs:
                    if isinstance(wf, dict):
                        alias = wf.get("alias")
                        if alias:
                            window_function_aliases.append(alias)

            if self.semantic:
                self.semantic.register_cte_columns(name, metrics, dimensions, constants, window_function_aliases)

            # 使用 _build_without_cte 构建 CTE 子查询（支持 UNION，但不支持 CTE）
            cte_select = self._build_without_cte(query_mql)
            cte_node = exp.CTE(
                this=cte_select,
                alias=exp.Identifier(this=name)
            )
            cte_nodes.append(cte_node)

        if not cte_nodes:
            # 没有 CTE，退化为普通查询
            return self._build_without_cte(mql)

        # 构建主查询（去掉 cte 字段避免递归）
        # 当使用 from_cte 时，主查询只引用CTE结果，不应该包含timeConstraint/filters等条件
        # 这些条件应该在CTE子查询中处理
        if mql.get("from_cte"):
            # from_cte场景：只保留显示和排序相关的字段
            # 允许 having（用于过滤 CTE 返回的窗口函数列，如 [rn] <= 10）
            allowed_main_fields = {"dimensions", "metrics", "limit", "orderBy", "from_cte", "distinct", "having"}
            main_mql = {k: v for k, v in mql.items() if k in allowed_main_fields}
        else:
            # 非from_cte场景：保留所有字段（除了cte）
            main_mql = {k: v for k, v in mql.items() if k != "cte"}

        main_select = self._build_without_cte(main_mql)

        # 将 CTE 设置到主 Select 的 with_ 属性上
        # sqlglot 中 WITH ... AS (...) SELECT ... 整体是 Select 类型，CTE 存储在 with_ 参数中
        main_select.set("with_", exp.With(expressions=cte_nodes))

        return main_select

    def _build_union_query(self, mqls: List[Dict[str, Any]], union_type: str) -> exp.Expression:
        """
        构建 UNION / UNION ALL 查询
        
        注意：
        - UNION 子查询不应该包含 LIMIT，LIMIT 应该在 UNION 的最外层应用
        - 子查询的 LIMIT 会在构建后被移除
        - UNION 的 LIMIT 取第一个子查询的 limit 值，如果没有则使用 1000
        """
        if not mqls:
            raise ValueError("UNION requires at least one query")

        # 获取 UNION 的 LIMIT（取第一个子查询的 limit）
        union_limit = mqls[0].get("limit", 1000) if mqls else 1000

        # 构建所有子查询（移除每个子查询的 LIMIT）
        selects = []
        for mql in mqls:
            select = self._build_base_select(mql)
            # 移除子查询的 LIMIT 节点
            select.set("limit", None)
            selects.append(select)

        # 组合为 UNION
        if len(selects) == 1:
            # 单个子查询，直接返回并应用 LIMIT
            return selects[0].limit(union_limit)

        is_distinct = union_type != "ALL"
        result = exp.Union(this=selects[0], expression=selects[1], distinct=is_distinct)

        for s in selects[2:]:
            result = exp.Union(this=result, expression=s, distinct=is_distinct)

        # 在 UNION 最外层应用 LIMIT
        # sqlglot 中，UNION 表达式不能直接应用 LIMIT
        # 解决方法：创建一个外层 SELECT 来包装 UNION 并应用 LIMIT
        from sqlglot import parse_one
        
        # 构建 UNION 的 SQL
        union_sql = result.sql(dialect=self.dialect)
        
        # 创建外层 SELECT：SELECT * FROM (UNION) LIMIT n
        wrapped_sql = f"SELECT * FROM ({union_sql}) AS union_result LIMIT {union_limit}"
        
        # 解析为 AST
        try:
            wrapped_ast = parse_one(wrapped_sql, dialect=self.dialect)
            return wrapped_ast
        except Exception:
            # 如果解析失败，直接返回 UNION（不带 LIMIT）
            return result

    def _build_select_clause(
        self, mql: Dict[str, Any]
    ) -> Tuple[List[exp.Expression], List[exp.Expression]]:
        """
        构建 SELECT 子句

        支持常量列（Constants）、维度（Dimensions）、指标（Metrics）
        支持CTE常量列引用

        Returns:
            (select_expressions, group_by_expressions)
        """
        select_exprs: List[exp.Expression] = []
        group_by_exprs: List[exp.Expression] = []

        # 1. 处理常量列（放在最前面）
        constants = mql.get("constants", [])
        for const in constants:
            const_name = const.get("name")
            const_value = const.get("value")
            const_type = const.get("type", "string")
            
            if const_type == "string":
                expr = exp.Literal.string(str(const_value))
            elif const_type == "number":
                expr = exp.Literal.number(float(const_value))
            else:
                expr = exp.Literal.string(str(const_value))
            
            select_exprs.append(expr.as_(const_name))
            # 常量列不加入 GROUP BY

        # 1.5. 处理CTE常量列（当from_cte时）
        if self._is_cte_source and self._used_view:
            cte_name = self._used_view.name
            cte_constants = self.semantic.get_cte_constants(cte_name) if self.semantic else []
            
            for const in cte_constants:
                const_name = const.get("name")
                const_value = const.get("value")
                const_type = const.get("type", "string")
                
                if const_type == "string":
                    expr = exp.Literal.string(str(const_value))
                elif const_type == "number":
                    expr = exp.Literal.number(float(const_value))
                else:
                    expr = exp.Literal.string(str(const_value))
                
                select_exprs.append(expr.as_(const_name))
                # CTE常量列不加入 GROUP BY

        # 2. 处理维度（维度是 GROUP BY 的基础）
        # 兼容 NL prompt 生成的 group_by 字段（与 dimensions 等价）
        # 使用 dict.fromkeys() 去重，保持顺序
        all_dims = list(dict.fromkeys(mql.get("dimensions", []) + mql.get("group_by", [])))
        for dim_name in all_dims:
            dim_expr, dim_group_by = self._build_dimension_expression(dim_name)
            if dim_expr:
                select_exprs.append(dim_expr)
                if dim_group_by:
                    group_by_exprs.append(dim_group_by)

        # 3. 处理指标
        metric_defs = mql.get("metricDefinitions", {})
        for metric_alias in mql.get("metrics", []):
            defn = metric_defs.get(metric_alias, {})
            metric_expr = self._build_metric_expression(metric_alias, defn)
            if metric_expr:
                select_exprs.append(metric_expr)
                # 指标不加入 GROUP BY

        return select_exprs, group_by_exprs

    def _build_dimension_expression(
        self, dim_name: str
    ) -> Tuple[Optional[exp.Expression], Optional[exp.Expression]]:
        """
        构建维度表达式

        处理逻辑：
        1. 解析后缀（__按月, __year 等）
        2. 查找维度元数据
        3. 应用时间格式化（如果适用）
        4. 返回列表达式和 GROUP BY 表达式
        """
        # 检查是否引用CTE列
        if self._is_cte_source and self._used_view:
            cte_name = self._used_view.name
            if self.semantic and self.semantic.is_cte_column(cte_name, dim_name):
                # 直接返回列引用（CTE的维度列），CTE返回的字段都可以用于GROUP BY
                return exp.column(dim_name).as_(dim_name), exp.column(dim_name)

        # 解析后缀
        actual_name = dim_name
        suffix = None
        if "__" in dim_name:
            actual_name, suffix = dim_name.split("__", 1)

        # 查找维度引用
        dim_ref = self.semantic.resolve_field(actual_name)
        if not dim_ref:
            # 找不到，返回原名字段
            return exp.column(dim_name).as_(dim_name), exp.column(dim_name)

        # 获取物理列表达式
        col_expr = dim_ref.physical_column
        if dim_ref.source_view_id:
            col_expr = self.semantic.get_view_column_expression(
                dim_ref.source_view_id, col_expr
            )

        # 解析为列节点
        if "." in col_expr:
            parts = col_expr.split(".", 1)
            col_node = exp.column(parts[1], table=parts[0])
        else:
            col_node = exp.column(col_expr)

        # 应用时间格式化（先格式化，再设置别名）
        time_fmt = self.semantic.get_time_format_for_field(dim_name)
        if time_fmt and dim_ref.dimension_type == "time":
            col_node = self._apply_date_format(col_node, time_fmt)
            # GROUP BY 也应该用格式化后的表达式
            group_by_node = col_node
        else:
            # 非时间维度：GROUP BY 用原始物理列
            if "." in col_expr:
                parts = col_expr.split(".", 1)
                group_by_node = exp.column(parts[1], table=parts[0])
            else:
                group_by_node = exp.column(col_expr)

        # 设置别名：确保 SELECT 输出的列名是语义名
        col_node = col_node.as_(dim_name)

        return col_node, group_by_node

    def _apply_date_format(self, col_node: exp.Column, fmt: str) -> exp.Expression:
        """应用日期格式化（不设置别名，由调用方设置）"""
        if self.dialect == "mysql":
            mysql_fmt = self._to_mysql_date_format(fmt)
            return exp.Anonymous(
                this="DATE_FORMAT", expressions=[col_node, exp.Literal.string(mysql_fmt)]
            )
        elif self.dialect == "postgresql":
            pg_fmt = self._to_postgresql_date_format(fmt)
            return exp.Anonymous(
                this="TO_CHAR", expressions=[col_node, exp.Literal.string(pg_fmt)]
            )
        elif self.dialect == "clickhouse":
            return exp.Anonymous(
                this="FORMAT", expressions=[col_node, exp.Literal.string(fmt.lower())]
            )
        return col_node

    def _to_mysql_date_format(self, fmt: str) -> str:
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
        mapping = {
            "YYYY-MM-DD": "YYYY-MM-DD",
            "YYYY-MM": "YYYY-MM",
            "YYYY": "YYYY",
            "YYYY-WW": "IYYY-IW",
            "YYYY-MM-DD HH:mm": "YYYY-MM-DD HH24:MI",
            "YYYY-MM-DD HH:mm:ss": "YYYY-MM-DD HH24:MI:SS",
        }
        return mapping.get(fmt, "YYYY-MM-DD")

    def _build_metric_expression(
        self, metric_alias: str, metric_def: Dict[str, Any]
    ) -> Optional[exp.Expression]:
        """
        构建指标表达式

        处理三种指标类型：
        - CTE列：直接返回列引用（无需metricDefinitions）
        - basic: 基础聚合（SUM, COUNT 等）
        - derived: 派生指标（YoY, MoM 等）
        - composite: 复合指标（[MetricA] + [MetricB] 等）
        """
        # 优先检查是否引用CTE列
        if self._is_cte_source and self._used_view:
            cte_name = self._used_view.name  # from_cte指定的CTE名
            if self.semantic and self.semantic.is_cte_column(cte_name, metric_alias):
                # CTE列：直接返回列引用（CTE已聚合，无需metricDefinitions）
                return exp.column(metric_alias).as_(metric_alias)

        # 非CTE列：需要metricDefinitions
        if not metric_def:
            # 没有metricDefinitions且不是CTE列，返回None或兜底
            return None

        ref_metric_name = metric_def.get("refMetric", metric_alias)
        indirections = metric_def.get("indirections", [])

        # 查找指标引用
        metric_ref = self.semantic.resolve_metric(ref_metric_name)
        if not metric_ref:
            # 指标在元数据中不存在时：
            # - 如果主查询引用 CTE，指标可能是 CTE 已聚合的列，直接用列名
            # - 否则返回 0（兜底）
            if self._is_cte_source:
                return exp.column(metric_alias).as_(metric_alias)
            return exp.Literal.number(0).as_(metric_alias)

        # 构建基础表达式
        base_expr = self._build_base_metric_expr(metric_ref)

        # 处理派生（YoY, MoM）
        if indirections:
            base_expr = self._apply_indirections(base_expr, indirections)

        # 处理派生指标类型
        if metric_ref.metric_type == "derived":
            if metric_ref.derivation_type in ("yoy", "yoy_growth"):
                base_expr = self._build_yoy_expr(base_expr, metric_ref.derivation_type)
            elif metric_ref.derivation_type in ("mom", "mom_growth"):
                base_expr = self._build_mom_expr(base_expr, metric_ref.derivation_type)

        return base_expr.as_(metric_alias)

    def _build_base_metric_expr(self, metric_ref) -> exp.Expression:
        """构建基础指标表达式"""
        if metric_ref.metric_type == "basic":
            if metric_ref.calculation_method == "expression" and metric_ref.calculation_formula:
                # 使用公式
                return self.expr_parser.parse(metric_ref.calculation_formula)
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

                agg = self._get_agg_func(metric_ref.aggregation)
                return agg(this=col_node)

        elif metric_ref.metric_type == "derived":
            # 需要找到基础指标
            base_metric = None
            for m in self.semantic.metrics.values():
                if hasattr(m, 'id') and m.id == metric_ref.base_metric_id:
                    base_metric = m
                    break
            if base_metric:
                return self._build_base_metric_expr(base_metric)
            return exp.Literal.number(0)

        elif metric_ref.metric_type == "composite":
            formula = metric_ref.calculation_formula or "0"
            return self.expr_parser.parse(formula)

        return exp.Literal.number(0)

    def _get_agg_func(self, agg_type: str):
        """获取聚合函数"""
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

    def _apply_indirections(
        self, base_expr: exp.Expression, indirections: List[str]
    ) -> exp.Expression:
        """应用间接修饰词（yoy_growth, mom_growth 等）"""
        for ind in indirections:
            if "yoy_growth" in ind or ind == "yoy_growth":
                base_expr = self._build_yoy_expr(base_expr, "yoy_growth")
            elif "yoy" in ind or ind == "yoy":
                base_expr = self._build_yoy_expr(base_expr, "yoy")
            elif "mom_growth" in ind or ind == "mom_growth":
                base_expr = self._build_mom_expr(base_expr, "mom_growth")
            elif "mom" in ind or ind == "mom":
                base_expr = self._build_mom_expr(base_expr, "mom")
        return base_expr

    def _build_yoy_expr(
        self, base_expr: exp.Expression, derivation_type: str
    ) -> exp.Expression:
        """
        构建同比表达式

        YoY Growth = (current - LAG(current, 12)) / NULLIF(LAG(current, 12), 0) * 100

        注意：这只是表达式结构，实际的窗口排序需要外部指定
        """
        # LAG(base_expr, 12)
        lag_expr = exp.Lag(this=base_expr, offset=exp.Literal.number(12))

        if derivation_type == "yoy_growth":
            # NULLIF(lag, 0)
            nullif_lag = exp.func("NULLIF", lag_expr, exp.Literal.number(0))
            # (base - lag) / NULLIF(lag, 0) * 100
            diff = exp.Sub(this=base_expr, expression=lag_expr)
            return exp.Mul(
                this=exp.Div(this=diff, expression=nullif_lag),
                expression=exp.Literal.number(100)
            )

        return base_expr

    def _build_mom_expr(
        self, base_expr: exp.Expression, derivation_type: str
    ) -> exp.Expression:
        """
        构建环比表达式

        MoM Growth = (current - LAG(current, 1)) / NULLIF(LAG(current, 1), 0) * 100
        """
        lag_expr = exp.Lag(this=base_expr, offset=exp.Literal.number(1))

        if derivation_type == "mom_growth":
            nullif_lag = exp.func("NULLIF", lag_expr, exp.Literal.number(0))
            diff = exp.Sub(this=base_expr, expression=lag_expr)
            return exp.Mul(
                this=exp.Div(this=diff, expression=nullif_lag),
                expression=exp.Literal.number(100)
            )

        return base_expr

    def _build_from_clause(self, mql: Dict[str, Any]) -> Tuple[Optional[exp.From], List[exp.Join]]:
        """
        构建 FROM 子句。

        支持：
        - 正常视图（单表/JOIN/SQL）
        - from_cte：引用 CTE 作为数据源

        Returns:
            (from_node, join_nodes) 元组
            join_nodes 仅在 joined 视图时非空
        """
        # 优先检查 from_cte（主查询引用 CTE）
        from_cte = mql.get("from_cte")
        if from_cte:
            return self._build_cte_from(from_cte)

        if not self._used_view:
            return None, []

        view = self._used_view

        if view.view_type == "single_table":
            dataset = self.semantic.resolve_dataset(view.base_table_id)
            if dataset:
                table_name = dataset.physical_name
                if dataset.schema_name:
                    table_name = f"{dataset.schema_name}.{table_name}"
                return exp.From(this=exp.Table(this=exp.Identifier(this=table_name))), []

        elif view.view_type == "joined":
            from_node, join_nodes = self._build_joined_from(view)
            if from_node is None and view.custom_sql:
                alias = f"view_{view.id[:8]}"
                return exp.From(
                    this=exp.Subquery(
                        this=sqlglot.parse_one(view.custom_sql, dialect=self.dialect),
                        alias=exp.Identifier(this=alias)
                    )
                ), []
            return from_node, join_nodes

        elif view.view_type == "sql":
            if view.custom_sql:
                alias = f"view_{view.id[:8]}"
                return exp.From(
                    this=exp.Subquery(
                        this=sqlglot.parse_one(view.custom_sql, dialect=self.dialect),
                        alias=exp.Identifier(this=alias)
                    )
                ), []

        return None, []

    def _build_cte_from(self, from_cte: Any) -> Tuple[Optional[exp.From], List[exp.Join]]:
        """
        构建 FROM CTE 子句。

        支持三种格式：
        - 字符串："CTE_名称" → FROM CTE_名称
        - 单个对象：{"table": "CTE_名称"} → FROM CTE_名称
        - 多 CTE JOIN：{"table": "CTE_A", "joins": [{"table": "CTE_B", "on": "..."}]}
          → FROM CTE_A JOIN CTE_B ON ...

        Returns:
            (from_node, join_nodes) 元组
        """
        if isinstance(from_cte, str):
            # 简单格式："CTE_名称"
            # 设置 _used_view 用于 CTE 列检查
            self._used_view = type('ViewRef', (), {
                'name': from_cte,
                'id': None,
                'display_name': from_cte,
                'view_type': 'cte',
                'datasource_id': None,
                'base_table_id': None,
                'join_config': None,
                'custom_sql': None,
                'columns': []
            })()
            return (
                exp.From(this=exp.Table(this=exp.Identifier(this=from_cte))),
                []
            )

        if isinstance(from_cte, dict):
            main_table = from_cte.get("table", "")
            if not main_table:
                return None, []

            from_node = exp.From(
                this=exp.Table(this=exp.Identifier(this=main_table))
            )

            join_nodes = []
            for join_def in from_cte.get("joins", []):
                right_table = join_def.get("table", "")
                join_type = join_def.get("type", "INNER").upper()
                on_clause = join_def.get("on", "")

                if not right_table:
                    continue

                # 解析 ON 条件
                on_expr = None
                if on_clause:
                    try:
                        on_expr = self.expr_parser.parse(on_clause)
                    except Exception:
                        on_expr = exp.true()

                join_node = exp.Join(
                    this=exp.Table(this=exp.Identifier(this=right_table)),
                    kind=join_type,
                    on=on_expr
                )
                join_nodes.append(join_node)

            return from_node, join_nodes

        return None, []

    def _build_joined_from(self, view: ViewRef) -> Tuple[Optional[exp.From], List[exp.Join]]:
        """
        构建 JOIN 视图的 FROM 子句和 JOIN 节点列表。

        Returns:
            (base_from_node, list_of_join_nodes)
            如果无法构建则返回 (None, [])
        """
        if not view.join_config:
            return None, []

        tables = view.join_config.get("tables", [])
        joins_config = view.join_config.get("joins", [])

        if not tables:
            return None, []

        # 构建表映射
        table_map: Dict[str, str] = {}
        for t in tables:
            dataset_id = t.get("id")
            alias = t.get("alias", f"t{len(table_map)}")
            dataset = self.semantic.resolve_dataset(dataset_id)
            if dataset:
                table_map[alias] = dataset.physical_name

        if not table_map:
            return None, []

        # 第一个表作为基础表
        first_table = tables[0]
        first_alias = first_table.get("alias", "t0")
        first_table_name = table_map.get(first_alias, "unknown")

        from_node = exp.From(
            this=exp.Table(
                this=exp.Identifier(this=first_table_name),
                alias=exp.Identifier(this=first_alias)
            )
        )

        # 构建 JOIN 节点列表
        join_nodes: List[exp.Join] = []
        for join in joins_config:
            left_alias = join.get("left_table")
            right_alias = join.get("right_table")
            join_type = join.get("join_type", "INNER").upper()
            conditions = join.get("conditions", [])

            if right_alias not in table_map:
                continue

            right_table_name = table_map[right_alias]

            # 构建 ON 条件
            on_parts = []
            for cond in conditions:
                left_col = cond.get("left_column")
                right_col = cond.get("right_column")
                operator = cond.get("operator", "=")
                on_parts.append(
                    exp.EQ(
                        this=exp.column(left_col, table=left_alias),
                        expression=exp.column(right_col, table=right_alias)
                    )
                )

            # 添加筛选条件到 JOIN
            filters = join.get("filters", [])
            for fc in filters:
                col = fc.get("column", "")
                op = fc.get("operator", "=")
                val = fc.get("value", "")
                if "." in col:
                    _, col_name = col.split(".", 1)
                else:
                    col_name = col
                on_parts.append(
                    exp.EQ(
                        this=exp.column(col_name, table=right_alias),
                        expression=exp.Literal.string(str(val)) if isinstance(val, str) else exp.Literal.number(val)
                    )
                )

            join_on = exp.And(expressions=on_parts) if len(on_parts) > 1 else on_parts[0] if on_parts else exp.true()

            join_node = exp.Join(
                this=exp.Table(
                    this=exp.Identifier(this=right_table_name),
                    alias=exp.Identifier(this=right_alias)
                ),
                kind=join_type,
                on=join_on
            )
            join_nodes.append(join_node)

        return from_node, join_nodes

    def _build_structured_filter(self, condition: Dict[str, Any], is_where: bool = True, skip_formatting: bool = True, parent_operator: str = None) -> Optional[exp.Expression]:
        """将结构化 filter 条件转为 sqlglot AST

        支持两种节点类型：
        - 叶子条件：{"field": "字段名", "op": "=", "value": "值"}
        - 分组条件：{"operator": "AND|OR", "conditions": [...]}

        关键修复：当父操作符是 OR 时，AND 子表达式需要用括号包裹，以避免优先级问题。
        例如：(A AND B) OR (C AND D) 而不是 A AND B OR C AND D
        """
        # 叶子条件
        if "field" in condition:
            field = condition["field"]
            op = condition.get("op", "=").upper()
            value = condition.get("value")

            # 用表达式解析器解析字段引用 [field_name]
            field_col = self.expr_parser.parse(f"[{field}]", is_where=is_where, skip_formatting=skip_formatting)

            # 构建 SQL 表达式
            if op == "LIKE":
                return exp.Like(this=field_col, expression=exp.Literal.string(value))
            elif op in ("IN", "NOT IN"):
                values = value if isinstance(value, list) else [value]
                in_expr = exp.In(
                    this=field_col,
                    expressions=[exp.Literal.string(v) for v in values]
                )
                if op == "NOT IN":
                    return exp.Not(this=in_expr)
                return in_expr
            elif op == "IS NULL":
                return exp.Is(this=field_col, expression=exp.Null())
            elif op == "IS NOT NULL":
                return exp.Not(this=exp.Is(this=field_col, expression=exp.Null()))
            else:
                # =, !=, <>, >, <, >=, <= 等
                op_map = {
                    "=": exp.EQ, "!=": exp.NEQ, "<>": exp.NEQ,
                    ">": exp.GT, "<": exp.LT, ">=": exp.GTE, "<=": exp.LTE,
                }
                cls = op_map.get(op)
                if cls:
                    # 检查 value 是否为 MQL 时间函数
                    if isinstance(value, str) and self.expr_parser.time_handler.is_mql_time_function(value):
                        # 解析时间函数为 SQL
                        time_sql = self.expr_parser.time_handler.parse_and_render(value)
                        # 解析为 sqlglot 表达式
                        try:
                            lit = sqlglot.parse_one(time_sql, dialect=self.dialect)
                        except:
                            lit = exp.Literal.string(time_sql)
                    # 检查是否为 Raw SQL 表达式（如 DATE_ADD(STR_TO_DATE(...), INTERVAL -1 DAY)）
                    elif isinstance(value, str) and self._is_sql_expression(value):
                        try:
                            lit = sqlglot.parse_one(value, dialect=self.dialect)
                        except:
                            lit = exp.Literal.string(value)
                    elif isinstance(value, str):
                        lit = exp.Literal.string(value)
                    else:
                        lit = exp.Literal.number(value)
                    return cls(this=field_col, expression=lit)
                # 兜底：拼接字符串让表达式解析器处理
                return self.expr_parser.parse(f"[{field}] {op} {value!r}", is_where=is_where, skip_formatting=skip_formatting)

        # 分组条件
        operator = condition.get("operator", "AND").upper()
        sub_conditions = condition.get("conditions", [])

        if not sub_conditions:
            return None

        exprs = []
        for sub in sub_conditions:
            sub_expr = self._build_structured_filter(sub, is_where, skip_formatting, parent_operator=operator)
            if sub_expr:
                exprs.append(sub_expr)

        if not exprs:
            return None
        if len(exprs) == 1:
            result = exprs[0]
        elif operator == "OR":
            result = exp.Or(expressions=exprs)
        else:
            result = exp.And(expressions=exprs)

        # 关键修复：如果父操作符是 OR，且当前是 AND，需要给整个 AND 表达式加括号
        # 确保生成的 SQL 是 (A AND B) OR (C AND D) 而不是 A AND B OR C AND D
        if parent_operator == "OR" and operator == "AND":
            result = exp.Paren(this=result)

        return result

    def _build_where_clause(self, mql: Dict[str, Any]) -> Optional[exp.Expression]:
        """构建 WHERE 子句
        
        时间过滤规则（V2 重构）：
        1. timeConstraint 字段已废弃，时间过滤统一使用 filters
        2. 如果 filters 中已包含时间类型字段的过滤，不做额外处理
        3. 如果 filters 中没有时间过滤，且视图有默认时间字段，自动添加默认时间过滤
        """
        conditions: List[exp.Expression] = []

        # === 处理 timeConstraint（向后兼容，已废弃） ===
        time_constraint = mql.get("timeConstraint")
        if time_constraint and time_constraint != "true":
            # 兼容旧的 timeConstraint 格式
            tc_expr = self.expr_parser.parse(time_constraint, is_where=True, skip_formatting=True)
            if tc_expr and not (isinstance(tc_expr, exp.Boolean) and tc_expr.this is True):
                conditions.append(tc_expr)
                # 如果使用了 timeConstraint，跳过 filters 中的时间过滤检查
                # 直接处理 filters 并返回
                filters = mql.get("filters", [])
                if filters:
                    if isinstance(filters, dict):
                        f_expr = self._build_structured_filter(filters, is_where=True, skip_formatting=True)
                        if f_expr and not (isinstance(f_expr, exp.Boolean) and f_expr.this is True):
                            conditions.append(f_expr)
                    elif isinstance(filters, list):
                        for filter_expr in filters:
                            if isinstance(filter_expr, dict):
                                f_expr = self._build_structured_filter(filter_expr, is_where=True, skip_formatting=True)
                            else:
                                f_expr = self.expr_parser.parse(filter_expr, is_where=True, skip_formatting=True)
                            if f_expr and not (isinstance(f_expr, exp.Boolean) and f_expr.this is True):
                                conditions.append(f_expr)
                
                if not conditions:
                    return None
                if len(conditions) == 1:
                    return conditions[0]
                return exp.And(expressions=conditions)

        # === 处理 filters（新逻辑：支持时间字段过滤） ===
        filters = mql.get("filters", [])
        has_time_filter = False
        
        if filters:
            if isinstance(filters, dict):
                # 检查是否包含时间过滤
                has_time_filter = self._check_has_time_filter_in_structured(filters)
                f_expr = self._build_structured_filter(filters, is_where=True, skip_formatting=True)
                if f_expr and not (isinstance(f_expr, exp.Boolean) and f_expr.this is True):
                    conditions.append(f_expr)
            elif isinstance(filters, list):
                # 旧字符串格式或混合格式
                for filter_expr in filters:
                    if isinstance(filter_expr, dict):
                        # 检查是否为时间字段过滤
                        field = filter_expr.get("field", "")
                        field_ref = self.semantic.resolve_field(field)
                        if field_ref and field_ref.dimension_type == "time":
                            has_time_filter = True
                        f_expr = self._build_structured_filter(filter_expr, is_where=True, skip_formatting=True)
                    else:
                        # 字符串格式，检查是否包含时间字段
                        import re
                        match = re.search(r'\[([^\]]+)\]', filter_expr)
                        if match:
                            field = match.group(1)
                            field_ref = self.semantic.resolve_field(field)
                            if field_ref and field_ref.dimension_type == "time":
                                has_time_filter = True
                        f_expr = self.expr_parser.parse(filter_expr, is_where=True, skip_formatting=True)
                    if f_expr and not (isinstance(f_expr, exp.Boolean) and f_expr.this is True):
                        conditions.append(f_expr)

        # === 默认时间过滤（如果 filters 中没有时间过滤） ===
        if not has_time_filter and not time_constraint:
            default_time_filter = self._build_default_time_filter(mql)
            if default_time_filter:
                conditions.insert(0, default_time_filter)

        if not conditions:
            return None

        if len(conditions) == 1:
            return conditions[0]

        return exp.And(expressions=conditions)

    def _check_has_time_filter_in_structured(self, filter_obj: Dict[str, Any]) -> bool:
        """检查结构化 filter 中是否包含时间字段过滤"""
        if "field" in filter_obj:
            # 叶子条件
            field = filter_obj.get("field", "")
            field_ref = self.semantic.resolve_field(field)
            return field_ref and field_ref.dimension_type == "time"
        
        # 分组条件
        conditions = filter_obj.get("conditions", [])
        for cond in conditions:
            if self._check_has_time_filter_in_structured(cond):
                return True
        return False

    def _build_default_time_filter(self, mql: Dict[str, Any]) -> Optional[exp.Expression]:
        """构建默认时间过滤
        
        当 filters 中没有时间过滤时，如果视图有默认时间字段，
        则自动添加默认时间范围过滤（如最近30天）。
        
        注意：此功能需要根据业务需求配置默认行为。
        当前实现：不做自动添加，保留扩展接口。
        """
        # 获取视图的默认时间字段
        if not self._used_view:
            return None
        
        view_id = self._used_view.id if hasattr(self._used_view, 'id') else None
        if not view_id:
            return None
        
        default_date_field = self.semantic.get_default_date_column(view_id)
        if not default_date_field:
            return None
        
        # TODO: 根据业务配置添加默认时间范围
        # 例如：最近30天、本月、本年等
        # 当前不自动添加，保留扩展接口
        return None

    def _build_having_clause(self, mql: Dict[str, Any]) -> Optional[exp.Expression]:
        """构建 HAVING 子句（新增）"""
        having = mql.get("having")
        if not having:
            return None

        if isinstance(having, str):
            return self.expr_parser.parse(having, is_where=True)
        elif isinstance(having, list):
            conditions = []
            for h in having:
                if isinstance(h, str):
                    c = self.expr_parser.parse(h, is_where=True)
                    if c:
                        conditions.append(c)
            if not conditions:
                return None
            return exp.And(expressions=conditions) if len(conditions) > 1 else conditions[0]

        return None

    def _build_order_by_clause(
        self,
        mql: Dict[str, Any],
        select_exprs: List[exp.Expression],
    ) -> Optional[exp.Order]:
        """构建 ORDER BY 子句（新增）"""
        order_by = mql.get("orderBy")
        if not order_by:
            return None

        order_exprs = []
        for order_spec in order_by:
            field = order_spec.get("field")
            direction = order_spec.get("direction", "ASC").upper()

            if not field:
                continue

            # 在 select_exprs 中查找对应的字段
            order_col = None
            for expr in select_exprs:
                alias = expr.alias if hasattr(expr, 'alias') and expr.alias else None
                if alias == field or (hasattr(expr, 'this') and hasattr(expr.this, 'alias') and expr.this.alias == field):
                    order_col = exp.column(alias)
                    break

            if not order_col:
                order_col = exp.column(field)

            order_exprs.append(
                exp.Ordered(
                    this=order_col,
                    desc=direction == "DESC"
                )
            )

        if not order_exprs:
            return None

        return exp.Order(expressions=order_exprs)

    def _is_sql_expression(self, value: str) -> bool:
        """
        检测字符串是否为 Raw SQL 表达式（而非普通字符串字面量）

        Raw SQL 表达式特征：
        - 包含 SQL 函数调用如 DATE_ADD, DATE_SUB, STR_TO_DATE, INTERVAL 等
        - 包含括号和运算符，不是简单的字符串

        这样可以区分：
        - 普通字符串值：如 "张三"（应作为字面量处理）
        - SQL 表达式：如 "DATE_ADD('2026-01-01', INTERVAL -1 DAY)"（应解析为表达式）
        """
        if not isinstance(value, str):
            return False

        # 常见 SQL 日期/时间函数关键词
        sql_funcs = [
            'DATE_ADD', 'DATE_SUB', 'DATE_FORMAT', 'STR_TO_DATE',
            'CURRENT_DATE', 'CURRENT_TIMESTAMP', 'NOW', 'TIMESTAMP',
            'INTERVAL', 'DAY', 'MONTH', 'YEAR', 'WEEK', 'QUARTER',
            'TIMESTAMPDIFF', 'DATE', 'DATETIME'
        ]

        # 检查是否包含 SQL 函数调用模式
        import re
        # 匹配函数调用模式：WORD(...) 或 WORD(..., ...)
        func_pattern = r'\b(' + '|'.join(sql_funcs) + r')\s*\('
        if re.search(func_pattern, value, re.IGNORECASE):
            return True

        # 检查是否包含 INTERVAL 表达式
        if re.search(r'\bINTERVAL\s+-?\d+\s+\w+', value, re.IGNORECASE):
            return True

        return False

    def to_sql(self, select: exp.Select) -> str:
        """将 AST 转换为 SQL 字符串"""
        return select.sql(dialect=self.dialect)
