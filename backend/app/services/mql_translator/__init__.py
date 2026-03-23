"""
MQL Translator V2 - 基于 sqlglot AST 的 MQL 到 SQL 转换引擎

架构：
- semantic.py: 语义上下文，从 DB 加载元数据
- expression_parser.py: 表达式解析器，[字段名] -> sqlglot AST
- ast_builder.py: AST 构建器，MQL -> sqlglot AST
- dialect.py: 方言转换，sqlglot AST -> 目标方言 SQL
- advanced_sql.py: 高级 SQL 特性（窗口函数、UNION、CTE、子查询）
- optimizer.py: 查询优化
- cache.py: LRU + TTL 缓存
- datasource_adapter.py: 多数据源适配器（ibis）
- access_control.py: 访问控制预留
- translator.py: 编排管线，串联所有组件
"""

from app.services.mql_translator.semantic import SemanticContext
from app.services.mql_translator.ast_builder import MQLASTBuilder
from app.services.mql_translator.translator import MQLTranslator
from app.services.mql_translator.advanced_sql import AdvancedSQLBuilder, WindowFunctions
from app.services.mql_translator.dialect import DialectConverter, get_dialect_name, transpile_sql
from app.services.mql_translator.optimizer import MQLOptimizer
from app.services.mql_translator.cache import MQLQueryCache, TranslationCache, get_translation_cache
from app.services.mql_translator.datasource_adapter import DataSourceAdapter, get_global_adapter
from app.services.mql_translator.access_control import (
    AccessControl,
    Permission,
    PermissionAction,
    ResourceType,
    AccessDecision,
    get_access_control,
)

__all__ = [
    # 核心
    "SemanticContext",
    "MQLASTBuilder",
    "MQLTranslator",
    # 高级 SQL
    "AdvancedSQLBuilder",
    "WindowFunctions",
    # 方言
    "DialectConverter",
    "get_dialect_name",
    "transpile_sql",
    # 优化
    "MQLOptimizer",
    # 缓存
    "MQLQueryCache",
    "TranslationCache",
    "get_translation_cache",
    # 多数据源
    "DataSourceAdapter",
    "get_global_adapter",
    # 访问控制
    "AccessControl",
    "Permission",
    "PermissionAction",
    "ResourceType",
    "AccessDecision",
    "get_access_control",
]
