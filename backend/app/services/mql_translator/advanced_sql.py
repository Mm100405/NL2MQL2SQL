"""
advanced_sql.py - MQL 高级 SQL 特性

支持：
- 窗口函数：ROW_NUMBER, RANK, DENSE_RANK, SUM OVER, AVG OVER, LAG, LEAD
- 子查询：WHERE 子查询、FROM 子查询（派生表）
- CTE：WITH 子句（公共表表达式）
- UNION / UNION ALL

与基础 ast_builder.py 的区别：
- ast_builder.py: 核心 SELECT/FROM/WHERE/GROUP BY/LIMIT
- advanced_sql.py: 高级特性扩展，通过 MQL 扩展字段触发
"""

from typing import Dict, List, Optional, Any, Tuple
from sqlglot import exp

from app.services.mql_translator.semantic import SemanticContext
from app.services.mql_translator.expression_parser import ExpressionParser


class AdvancedSQLBuilder:
    """
    MQL 高级 SQL 特性构建器

    MQL 扩展字段：
    {
        "windowFunctions": [
            {
                "alias": "累计销售额",
                "func": "SUM",
                "field": "销售额",
                "partition": ["渠道"],      # 可选，PARTITION BY
                "orderBy": "日期",          # 可选，ORDER BY
                "rows": "UNBOUNDED PRECEDING TO CURRENT ROW"  # 可选，窗口框架
            }
        ],
        "subquery": {                       # FROM 子查询
            "name": "sales_summary",
            "query": { /* MQL */ }
        },
        "union": {                          # UNION 查询
            "type": "ALL",                  # ALL 或空
            "queries": [ /* MQL 列表 */ ]
        },
        "cte": [                            # CTE (WITH)
            {
                "name": "monthly_sales",
                "query": { /* MQL */ }
            }
        ],
        "having": "销售额 > 10000"         # 已在 ast_builder 中实现
    }
    """

    def __init__(self, semantic: SemanticContext, dialect: str = "mysql"):
        self.semantic = semantic
        self.dialect = dialect
        self.expr_parser = ExpressionParser(semantic, dialect)

    def build_window_function(
        self,
        window_spec: Dict[str, Any],
        field_resolver: Optional[callable] = None,
    ) -> Tuple[exp.Expression, str]:
        """
        构建窗口函数表达式

        Args:
            window_spec: 窗口函数定义
                {
                    "alias": "累计销售额",
                    "func": "SUM",          # SUM/AVG/COUNT/MAX/MIN/ROW_NUMBER/RANK/DENSE_RANK
                    "field": "销售额",      # 聚合函数适用的字段
                    "partition": ["渠道"],   # 可选，PARTITION BY
                    "orderBy": [            # 可选，ORDER BY（数组格式，与主查询一致）
                        {"field": "上报数", "direction": "DESC"}
                    ],  # 也支持字符串格式 "上报数 DESC"（兼容旧版）
                    "rows": "UNBOUNDED PRECEDING TO CURRENT ROW"  # 可选，窗口框架
                }
            field_resolver: 可选的字段解析函数，签名为 (field_name) -> exp.Expression
                           用于将指标别名解析为实际的 SQL 表达式

        Returns:
            (窗口函数 AST 节点, 别名)
        """
        func_name = window_spec.get("func", "SUM").upper()
        field = window_spec.get("field")
        alias = window_spec.get("alias", f"{func_name}_{field}")
        partition_by = window_spec.get("partition", [])
        order_by = window_spec.get("orderBy")
        rows_frame = window_spec.get("rows")  # 如 "UNBOUNDED PRECEDING TO CURRENT ROW"

        # 构建基础表达式
        # 如果提供了 field_resolver，使用它解析字段；否则直接使用列引用
        if field:
            if field_resolver:
                field_expr = field_resolver(field)
            else:
                field_expr = exp.column(field)
        else:
            field_expr = None

        # 构建聚合函数
        if func_name in ("SUM", "AVG", "COUNT", "MAX", "MIN"):
            agg_func = getattr(exp, func_name, exp.Sum)
            if field_expr:
                func_expr = agg_func(this=field_expr)
            else:
                func_expr = agg_func()
        elif func_name in ("ROW_NUMBER", "RANK", "DENSE_RANK"):
            # sqlglot中函数名使用PascalCase：RowNumber, Rank, DenseRank
            func_class_name = ''.join(word.capitalize() for word in func_name.split('_'))
            func_expr = getattr(exp, func_class_name)()
        elif func_name in ("LAG", "LEAD"):
            offset = window_spec.get("offset", 1)
            default = window_spec.get("default")
            args = [field_expr, exp.Literal.number(offset)]
            if default is not None:
                args.append(exp.Literal.number(default))
            func_expr = getattr(exp, func_name)(this=field_expr, offset=exp.Literal.number(offset))
        else:
            # 默认使用 SUM
            func_expr = exp.Sum(this=field_expr) if field_expr else exp.Sum()

        # 构建窗口规范
        window_spec_parts = []

        # 辅助函数：解析字段到表达式
        def resolve_field_expr(field_name: str) -> exp.Expression:
            """解析字段名到 SQL 表达式"""
            if field_resolver:
                resolved = field_resolver(field_name)
                if resolved:
                    return resolved
            return exp.column(field_name)

        # PARTITION BY（支持数组格式 ["字段"] 和字符串格式 "字段"）
        if partition_by:
            if isinstance(partition_by, str):
                partition_by = [partition_by]
            partition_exprs = [resolve_field_expr(p) for p in partition_by]
            window_spec_parts.append(exp.Partition(expressions=partition_exprs))

        # ORDER BY（支持数组格式 [{field, direction}] 和字符串格式 "field DESC"）
        if order_by:
            if isinstance(order_by, list):
                # 数组格式：[{"field": "上报数", "direction": "DESC"}, ...]
                for item in order_by:
                    if isinstance(item, dict):
                        order_field = item.get("field")
                        direction = item.get("direction", "ASC").upper()
                    else:
                        order_field = str(item)
                        direction = "ASC"
                    if order_field:
                        window_spec_parts.append(exp.Ordered(
                            this=resolve_field_expr(order_field),
                            desc=direction == "DESC"
                        ))
            elif isinstance(order_by, str):
                # 字符串格式（兼容旧版）："上报数 DESC" 或 "日期"
                direction = "ASC"
                order_field = order_by.strip()
                if order_field.upper().endswith(" DESC"):
                    direction = "DESC"
                    order_field = order_field[:order_field.upper().rfind(" DESC")].strip()
                elif order_field.upper().endswith(" ASC"):
                    direction = "ASC"
                    order_field = order_field[:order_field.upper().rfind(" ASC")].strip()
                if order_field:
                    window_spec_parts.append(exp.Ordered(
                        this=resolve_field_expr(order_field),
                        desc=direction == "DESC"
                    ))

        # 窗口框架 (ROWS / RANGE)
        if rows_frame:
            window_frame = self._parse_window_frame(rows_frame)
            if window_frame:
                window_spec_parts.append(window_frame)

        # 构建 Window 节点
        # 注意：
        # 1. sqlglot 的 order 需要 exp.Order(expressions=[Ordered1, Ordered2, ...])
        #    而不是直接设置 exp.Ordered，否则会生成错误的 SQL 如 OVER ("字段" ORDER BY )
        # 2. sqlglot 的 key 是 partition_by（列表），不是 partition
        partition_columns = []
        order_exprs = []
        frame_expr = None

        for part in window_spec_parts:
            if isinstance(part, exp.Partition):
                # 从 Partition 对象提取列列表
                partition_columns = list(part.expressions) if part.expressions else []
            elif isinstance(part, exp.Ordered):
                order_exprs.append(part)
            elif hasattr(exp, 'WindowFrame') and isinstance(part, exp.WindowFrame):
                frame_expr = part

        window_node = exp.Window(this=func_expr)
        if partition_columns:
            window_node.set("partition_by", partition_columns)
        if order_exprs:
            window_node.set("order", exp.Order(expressions=order_exprs))
        if frame_expr:
            window_node.set("frame", frame_expr)

        return window_node, alias



    def build_subquery_from(
        self,
        subquery_mql: Dict[str, Any],
        subquery_name: str,
    ) -> exp.Subquery:
        """
        构建 FROM 子查询（派生表）

        Args:
            subquery_mql: 子查询的 MQL
            subquery_name: 子查询别名

        Returns:
            exp.Subquery
        """
        # 使用主 AST builder 构建子查询（递归）
        from app.services.mql_translator.ast_builder import MQLASTBuilder

        builder = MQLASTBuilder(self.semantic, self.dialect)
        subquery_ast = builder.build(subquery_mql)

        return exp.Subquery(
            this=subquery_ast,
            alias=exp.Identifier(this=subquery_name)
        )

    def build_union(
        self,
        mqls: List[Dict[str, Any]],
        union_type: str = "",
    ) -> exp.Union:
        """
        构建 UNION / UNION ALL 查询

        Args:
            mqls: MQL 列表
            union_type: "ALL" 或 "" (空 = DISTINCT)

        Returns:
            exp.Union
        """
        if not mqls:
            raise ValueError("UNION requires at least one query")

        from app.services.mql_translator.ast_builder import MQLASTBuilder

        builder = MQLASTBuilder(self.semantic, self.dialect)

        # 构建第一个查询
        first_ast = builder.build(mqls[0])

        if len(mqls) == 1:
            return first_ast

        # 构建剩余查询并组合
        union_expr = exp.Union(
            this=first_ast,
            expression=builder.build(mqls[1]),
            distinct=union_type != "ALL"
        )

        # 添加更多查询
        for mql in mqls[2:]:
            union_expr = exp.Union(
                this=union_expr,
                expression=builder.build(mql),
                distinct=union_type != "ALL"
            )

        return union_expr

    def build_cte(
        self,
        cte_defs: List[Dict[str, Any]],
        main_mql: Dict[str, Any],
    ) -> exp.CTE:
        """
        构建 CTE (WITH 子句)

        Args:
            cte_defs: CTE 定义列表
                [
                    {
                        "name": "monthly_sales",
                        "query": { /* MQL */ }
                    }
                ]
            main_mql: 主查询 MQL

        Returns:
            exp.CTE
        """
        from app.services.mql_translator.ast_builder import MQLASTBuilder

        builder = MQLASTBuilder(self.semantic, self.dialect)

        cte_expressions = []
        for cte_def in cte_defs:
            name = cte_def.get("name")
            query_mql = cte_def.get("query")
            if not name or not query_mql:
                continue

            cte_query = builder.build(query_mql)
            cte_expr = exp.CTE(
                this=cte_query,
                alias=exp.Identifier(this=name)
            )
            cte_expressions.append(cte_expr)

        if not cte_expressions:
            # 没有 CTE，返回主查询
            return builder.build(main_mql)

        # 构建主查询
        main_ast = builder.build(main_mql)

        # 将 CTE 设置到主 Select 的 with_ 属性上（与 ast_builder._build_with_cte 一致）
        main_ast.set("with_", exp.With(expressions=cte_expressions))

        return main_ast



    def build_having_with_subquery(
        self,
        having_def: Dict[str, Any],
    ) -> Optional[exp.Having]:
        """
        构建带子查询的 HAVING 条件

        Args:
            having_def: HAVING 定义
                {
                    "type": "subquery",
                    "operator": ">",
                    "field": "销售额",
                    "subquery": { /* MQL */ }
                }

        Returns:
            exp.Having
        """
        if having_def.get("type") != "subquery":
            return None

        operator = having_def.get("operator", "=")
        field = having_def.get("field")
        subquery_mql = having_def.get("subquery")

        if not field or not subquery_mql:
            return None

        # 构建子查询
        from app.services.mql_translator.ast_builder import MQLASTBuilder

        builder = MQLASTBuilder(self.semantic, self.dialect)
        subquery_ast = builder.build(subquery_mql)

        # 构建字段引用
        field_expr = exp.column(field)

        # 构建操作符
        op_map = {
            "=": exp.EQ,
            "!=": exp.NEQ,
            ">": exp.GT,
            "<": exp.LT,
            ">=": exp.GTE,
            "<=": exp.LTE,
        }
        op_class = op_map.get(operator, exp.EQ)

        # 构建 HAVING 条件
        having_expr = op_class(
            this=field_expr,
            expression=exp.Subquery(this=subquery_ast)
        )

        return exp.Having(this=having_expr)


class WindowFunctions:
    """窗口函数工具类"""

    # 窗口函数名称映射
    FUNCTION_NAMES = {
        "ROW_NUMBER": "ROW_NUMBER",
        "RANK": "RANK",
        "DENSE_RANK": "DENSE_RANK",
        "SUM": "SUM",
        "AVG": "AVG",
        "COUNT": "COUNT",
        "MAX": "MAX",
        "MIN": "MIN",
        "LAG": "LAG",
        "LEAD": "LEAD",
        "FIRST_VALUE": "FIRST_VALUE",
        "LAST_VALUE": "LAST_VALUE",
    }

    @classmethod
    def is_window_function(cls, func_name: str) -> bool:
        """判断是否为窗口函数"""
        return func_name.upper() in cls.FUNCTION_NAMES

    @classmethod
    def get_window_func_class(cls, func_name: str):
        """获取窗口函数对应的 sqlglot 节点类"""
        return getattr(exp, func_name.upper(), None)
