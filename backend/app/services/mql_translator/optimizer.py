"""
optimizer.py - MQL 查询优化器

基于 sqlglot.optimizer 的查询优化。

优化规则：
1. eliminate_subqueries - 消除无用子查询
2. predicate_pushdown - 谓词下推
3. column_pruning - 列裁剪（减少 SELECT * 的列数）
4. normalize - 标准化表达式
5. unnest_subqueries - 展开子查询
6. merge_subqueries - 合并子查询

使用方式：
    optimizer = MQLOptimizer()
    optimized = optimizer.optimize(ast, schema={"table": {"col": "INT"}}, dialect="mysql")
"""

import logging
from typing import Dict, Optional
from sqlglot import exp
from sqlglot.optimizer import optimize, RULES

logger = logging.getLogger(__name__)

# 可用的优化规则
AVAILABLE_RULES = [
    "eliminate_subqueries",
    "predicate_pushdown",
    "column_pruning",
    "normalize",
    "unnest_subqueries",
    "merge_subqueries",
    "simplify",
    "flatten",
]


class MQLOptimizer:
    """
    MQL 查询优化器

    基于 sqlglot.optimizer 提供查询优化。
    默认启用以下规则：
    - predicate_pushdown: 将过滤条件下推到最深层子查询
    - column_pruning: 裁剪未使用的列
    - simplify: 简化表达式（如 1=1 -> TRUE）
    """

    def __init__(
        self,
        rules: Optional[list] = None,
        enable_collect: bool = True,
    ):
        """
        初始化优化器

        Args:
            rules: 优化规则列表（默认使用推荐规则）
            enable_collect: 是否收集优化统计信息
        """
        self.rules = rules or ["predicate_pushdown", "column_pruning", "simplify"]
        self.enable_collect = enable_collect
        self._validate_rules()

    def _validate_rules(self):
        """验证规则有效性"""
        for rule in self.rules:
            if rule not in AVAILABLE_RULES:
                logger.warning(f"Unknown optimization rule: {rule}, ignoring")

    def optimize(
        self,
        ast: exp.Expression,
        schema: Optional[Dict[str, Dict[str, str]]] = None,
        dialect: str = "mysql",
    ) -> exp.Expression:
        """
        优化 AST

        Args:
            ast: sqlglot AST
            schema: 表结构字典（可选）
            dialect: SQL 方言

        Returns:
            优化后的 AST
        """
        if not ast:
            return ast

        # 过滤有效规则
        valid_rules = [r for r in self.rules if r in AVAILABLE_RULES]

        try:
            # sqlglot.optimizer.optimize 需要 schema 参数
            # schema 格式: {table_name: {column_name: type}}
            optimized = optimize(
                ast,
                schema=schema or {},
                dialect=dialect,
                rules=valid_rules,
            )
            return optimized
        except Exception as e:
            logger.debug(f"Optimization skipped: {e}, returning original AST")
            return ast

    def optimize_sql(
        self,
        sql: str,
        schema: Optional[Dict[str, Dict[str, str]]] = None,
        dialect: str = "mysql",
    ) -> str:
        """
        优化 SQL 字符串

        Args:
            sql: SQL 字符串
            schema: 表结构
            dialect: SQL 方言

        Returns:
            优化后的 SQL
        """
        import sqlglot

        try:
            ast = sqlglot.parse_one(sql, dialect=dialect)
            optimized = self.optimize(ast, schema=schema, dialect=dialect)
            return optimized.sql(dialect=dialect)
        except Exception as e:
            logger.warning(f"SQL optimization failed: {e}, returning original SQL")
            return sql

    def get_optimization_stats(
        self,
        original: exp.Expression,
        optimized: exp.Expression,
    ) -> Dict[str, any]:
        """
        获取优化统计信息

        Returns:
            {
                "original_size": ...,
                "optimized_size": ...,
                "size_reduction": ...,
            }
        """
        original_sql = original.sql() if isinstance(original, exp.Expression) else str(original)
        optimized_sql = optimized.sql() if isinstance(optimized, exp.Expression) else str(optimized)

        return {
            "original_size": len(original_sql),
            "optimized_size": len(optimized_sql),
            "size_reduction": len(original_sql) - len(optimized_sql),
            "improvement_pct": (
                (len(original_sql) - len(optimized_sql)) / len(original_sql) * 100
                if original_sql else 0
            ),
        }
