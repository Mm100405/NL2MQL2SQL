"""MQL Engine - Parse MQL and convert to SQL

已迁移到 V2 引擎（基于 sqlglot AST）
旧版字符串拼接引擎已移除（2026-03-26）
"""
from typing import Dict, Any
from sqlalchemy.orm import Session


async def mql_to_sql(mql: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Convert MQL to SQL using sqlglot AST engine (V2)

    Args:
        mql: MQL JSON 对象
        db: 数据库会话

    Returns:
        {
            "sql": SQL 字符串,
            "datasources": 数据源ID列表,
            "dialect": SQL 方言,
            "mql": 原始 MQL,
            "lineage": {
                "metrics": 指标列表,
                "dimensions": 维度列表
            }
        }
    """
    from app.config import settings
    from app.services.mql_translator import MQLTranslator

    # 使用 V2 引擎（sqlglot AST）
    translator = MQLTranslator(db, use_optimizer=settings.MQL_OPTIMIZER_ENABLED)
    result = translator.translate(mql)
    
    return {
        "sql": result["sql"],
        "datasources": [result["datasource_id"]] if result.get("datasource_id") else [],
        "dialect": result.get("dialect", "mysql"),
        "mql": mql,
        "lineage": {
            "metrics": list(result.get("mql", {}).get("metricDefinitions", {}).keys()),
            "dimensions": list(result.get("mql", {}).get("dimensions", [])),
        },
    }
