"""
translator.py - MQL 翻译器编排管线

串联 SemanticContext、AST Builder、Optimizer、Dialect Converter，
提供统一的 mql_to_sql 接口，替代旧版 mql_engine.py。

使用方式：
    translator = MQLTranslator(db)
    result = translator.translate(mql)
    # result = {"sql": "...", "datasource_id": "...", "dialect": "..."}
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.mql_translator.semantic import SemanticContext
from app.services.mql_translator.ast_builder import MQLASTBuilder
from app.services.mql_translator.dialect import DialectConverter
from app.services.mql_translator.optimizer import MQLOptimizer
from app.services.mql_translator.cache import get_translation_cache, TranslationCache
from app.config import settings

logger = logging.getLogger(__name__)


class MQLTranslator:
    """
    MQL 翻译器 - 统一的翻译管线

    流程：
    1. 检查缓存（命中则直接返回）
    2. 加载语义上下文（从 DB 加载元数据）
    3. 验证 MQL
    4. 构建 AST（使用 ExpressionParser + ASTBuilder）
    5. 优化 AST（可选，使用 sqlglot.optimizer）
    6. 转换为目标方言 SQL
    7. 写入缓存
    8. 返回结果
    """

    def __init__(self, db: Session, use_optimizer: bool = True):
        self.db = db
        self.use_optimizer = use_optimizer and settings.MQL_OPTIMIZER_ENABLED
        self.use_cache = settings.MQL_CACHE_ENABLED

        # 初始化组件（延迟加载）
        self._semantic: Optional[SemanticContext] = None
        self._optimizer: Optional[MQLOptimizer] = None
        self._cache: Optional[TranslationCache] = None

    def _get_semantic(self) -> SemanticContext:
        """获取语义上下文（延迟加载 + 缓存）"""
        if self._semantic is None:
            self._semantic = SemanticContext(self.db).load()
        return self._semantic

    def _get_optimizer(self) -> MQLOptimizer:
        """获取优化器（延迟加载）"""
        if self._optimizer is None:
            self._optimizer = MQLOptimizer()
        return self._optimizer

    def _get_cache(self) -> TranslationCache:
        """获取翻译缓存"""
        if self._cache is None:
            self._cache = get_translation_cache()
        return self._cache

    def translate(self, mql: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 MQL 翻译为 SQL

        Args:
            mql: MQL JSON 对象

        Returns:
            {
                "sql": SQL 字符串,
                "datasource_id": 数据源ID,
                "dialect": SQL 方言,
                "ast": sqlglot AST（可选）
            }
        """
        # 1. 确定方言（用于缓存键）
        semantic = self._get_semantic()
        used_view, datasource_id = semantic.get_used_view(mql)
        dialect = semantic.get_dialect(datasource_id)

        # 2. 检查缓存
        if self.use_cache:
            cached = self._get_cache().get_translation(mql, dialect)
            if cached is not None:
                logger.debug(f"Translation cache hit for dialect={dialect}")
                return cached

        # 3. 验证 MQL（基本验证，不通过则使用旧引擎）
        try:
            is_valid = self._validate_mql(mql)
        except Exception as e:
            logger.warning(f"MQL validation failed, will try best effort: {e}")
            is_valid = True  # 继续尝试

        # 3. 预处理 MQL：使用 mql_corrector 修正（补全 metricDefinitions、修正维度等）
        try:
            from app.utils.mql_corrector import MQLCorrector
            corrector = MQLCorrector(self.db)
            mql = corrector.correct_and_validate(mql)
        except Exception as e:
            logger.warning(f"MQL correction failed, using original MQL: {e}")

        # 4. 构建 AST（返回 Select / Union / CTE 等表达式）
        builder = MQLASTBuilder(semantic, dialect=dialect)
        try:
            ast = builder.build(mql)
        except Exception as e:
            logger.error(f"AST building failed: {e}")
            raise ValueError(f"MQL to AST conversion failed: {e}")

        # 5. 优化 AST（可选）
        if self.use_optimizer:
            try:
                optimizer = self._get_optimizer()
                schema = self._build_schema(semantic)
                ast = optimizer.optimize(ast, schema=schema, dialect=dialect)
            except Exception as e:
                logger.warning(f"Optimization failed, using unoptimized: {e}")

        # 6. 转换为 SQL
        dialect_converter = DialectConverter(default_dialect=dialect)

        # 先尝试获取 dialect-specific SQL
        try:
            # 生成最终 SQL
            sql = dialect_converter.to_dialect(ast, dialect)

            # 如果 AST 生成了通用 SQL（比如有 {DEFAULT} 这样的），再做方言转换
            if "{" in sql and "}" in sql:
                # 需要进一步处理占位符
                sql = dialect_converter.to_dialect(ast, dialect)
        except Exception as e:
            logger.warning(f"SQL generation failed: {e}")
            # 回退到基本 SQL 生成
            sql = ast.sql(dialect=dialect)

        # 7. 构建结果
        result = {
            "sql": sql,
            "mql": mql,
            "datasource_id": datasource_id,
            "dialect": dialect,
            "used_view_id": used_view.id if used_view else None,
            "used_view_name": used_view.name if used_view else None,
        }

        # 8. 写入缓存
        if self.use_cache:
            try:
                self._get_cache().set_translation(mql, dialect, result)
            except Exception as e:
                logger.warning(f"Failed to cache translation: {e}")

        return result

    def _validate_mql(self, mql: Dict[str, Any]) -> bool:
        """基本 MQL 验证"""
        if not mql:
            raise ValueError("MQL is empty")

        if "metrics" not in mql and "dimensions" not in mql:
            raise ValueError("MQL must have at least metrics or dimensions")

        # 检查指标定义是否完整
        metrics = mql.get("metrics", [])
        metric_defs = mql.get("metricDefinitions", {})
        for metric_name in metrics:
            if metric_name not in metric_defs:
                # 自动补全空的定义
                mql["metricDefinitions"][metric_name] = {"refMetric": metric_name}

        return True

    def _build_schema(self, semantic: SemanticContext) -> Dict[str, Dict[str, str]]:
        """
        构建 schema 字典供 sqlglot.optimizer 使用

        格式：
        {
            "table_name": {
                "column_name": "TYPE",
                ...
            },
            ...
        }
        """
        schema: Dict[str, Dict[str, str]] = {}

        # 从数据集构建 schema
        for ds_id, dataset in semantic.datasets.items():
            table_name = dataset.physical_name
            if dataset.schema_name:
                table_name = f"{dataset.schema_name}.{table_name}"

            schema[table_name] = {}
            for col in dataset.columns:
                col_name = col.get("name", "")
                col_type = col.get("type", "STRING").upper()
                schema[table_name][col_name] = col_type

        return schema

    def invalidate_cache(self, mql: Optional[Dict[str, Any]] = None, dialect: Optional[str] = None):
        """
        使缓存失效

        Args:
            mql: 指定的 MQL（None 表示清空所有）
            dialect: 指定的方言
        """
        if self._cache is None:
            self._cache = self._get_cache()

        if mql and dialect:
            self._cache.invalidate(mql, dialect)
        else:
            self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self._get_cache().get_stats()
