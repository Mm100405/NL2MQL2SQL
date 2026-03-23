# backend/app/agents/deep_agents/tools.py

"""
Deep Agents 工具定义

基于 LangChain Tools 和 Deep Agents 规范的工具定义
参考：https://docs.langchain.com/oss/python/deepagents/tools

将现有的 Skills 转换为 Deep Agents 兼容的工具
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from sqlalchemy.orm import Session
import asyncio
import json
import re


# ============== 意图分析工具 ==============

@tool
async def analyze_intent(
    natural_language: str,
    metadata: Dict[str, Any],
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """分析用户查询意图
    
    这是 Deep Agents 的标准工具，替代 IntentAnalysisSkill
    使用 LLM 分析查询意图、复杂度并推荐相关指标和维度
    
    Args:
        natural_language: 用户的自然语言查询
        metadata: 元数据（包含指标和维度）
        db_session: 数据库会话（可选）
    
    Returns:
        意图分析结果：
        - intent: 完整的意图对象
        - intent_type: 意图类型（trend、comparison、drilldown、attribution、aggregation）
        - complexity: 复杂度（low、medium、high）
        - suggested_metrics: 建议的指标
        - suggested_dimensions: 建议的维度
    """
    try:
        # 获取模型配置
        model_config = _get_model_config(db_session)
        
        if not model_config["api_key"]:
            print(f"[analyze_intent] WARN 未配置 API Key，返回默认意图")
            return {
                "success": True,
                "intent": {
                    "intent_type": "aggregation",
                    "description": "聚合查询",
                    "suggested_metrics": [],
                    "suggested_dimensions": [],
                    "complexity": "low"
                },
                "intent_type": "aggregation",
                "complexity": "low"
            }
        
        # 构建意图分析 Prompt
        prompt = _build_intent_analysis_prompt(natural_language, metadata)
        
        # 调用 LLM
        from app.services.llm_client import call_llm
        
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params={"temperature": 0.2, "max_tokens": 512}
        )
        
        # 解析意图
        intent = _parse_intent_response(response)
        
        print(f"[analyze_intent] OK 意图分析完成: {intent.get('intent_type')}, 复杂度: {intent.get('complexity')}")
        
        return {
            "success": True,
            "intent": intent,
            "intent_type": intent.get("intent_type", "aggregation"),
            "complexity": intent.get("complexity", "low")
        }
    except Exception as e:
        print(f"[analyze_intent] WARN 意图分析失败: {e}")
        import traceback
        traceback.print_exc()
        # 失败时返回默认意图
        return {
            "success": True,
            "intent": {
                "intent_type": "aggregation",
                "description": "聚合查询",
                "suggested_metrics": [],
                "suggested_dimensions": [],
                "complexity": "low"
            },
            "intent_type": "aggregation",
            "complexity": "low"
        }


# ============== 元数据检索工具 ==============

@tool
def retrieve_metadata(
    natural_language: str,
    context: Optional[Dict[str, Any]] = None,
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """检索查询相关的元数据（指标、维度、可过滤字段）
    
    这是 Deep Agents 的标准工具，替代 MetadataRetrievalSkill
    
    Args:
        natural_language: 用户的自然语言查询
        context: 上下文信息（可选）
        db_session: 数据库会话（可选）
    
    Returns:
        包含元数据的字典：
        - metrics: 指标列表
        - dimensions: 维度列表
        - filterable_fields: 可过滤字段列表
        - time_formats: 时间格式列表
        - suggested_metrics: 建议的指标名称列表
        - suggested_dimensions: 建议的维度名称列表
    """
    # 复用现有的元数据检索逻辑
    try:
        if db_session:
            from app.models.metric import Metric
            from app.models.dimension import Dimension
            from sqlalchemy import or_

            # 检索指标
            metrics = db_session.query(Metric).all()
            metrics_list = [
                {
                    "name": m.name,
                    "display_name": m.display_name,
                    "measure_column": m.measure_column,
                    "aggregation": m.aggregation,
                    "description": m.description or "",
                    "view_id": m.view_id,
                    "synonyms": m.synonyms or [],
                }
                for m in metrics
            ]

            # 检索维度
            dimensions = db_session.query(Dimension).all()
            dimensions_list = [
                {
                    "name": d.name,
                    "display_name": d.display_name,
                    "physical_column": d.physical_column,
                    "data_type": d.data_type,
                    "dimension_type": d.dimension_type,
                    "description": d.description or "",
                    "view_id": d.view_id,
                    "synonyms": d.synonyms or [],
                    "format_config": d.format_config,
                }
                for d in dimensions
            ]

            # 识别时间维度
            time_dimensions = {
                d["name"] for d in dimensions_list
                if d.get("dimension_type") == "time"
                or str(d.get("data_type", "")).lower() in ("date", "datetime", "timestamp")
            }

            # 指标字段名（聚合后字段，只能用于 having）
            metric_field_names = {m["name"] for m in metrics_list}

            # 维度字段名（非聚合字段，只能用于 filters/w group by）
            dimension_field_names = {d["name"] for d in dimensions_list}

            # 聚合上下文
            agg_context = {
                m["name"]: m["aggregation"] or "SUM"
                for m in metrics_list
            }

            metadata = {
                "metrics": metrics_list,
                "dimensions": dimensions_list,
            }

            # 预构建 prompt 字符串（直接传入已查询的 ORM 对象，避免重复查 DB）
            from app.services.nl_parser import _build_metadata_strings
            metrics_str, dimensions_str, filterable_fields_str = _build_metadata_strings(
                db_session, 
                metrics_objs=metrics,
                dimensions_objs=dimensions
            )

            return {
                "success": True,
                "metadata": metadata,
                "metadata_prompt_strings": {
                    "metrics_str": metrics_str,
                    "dimensions_str": dimensions_str,
                    "filterable_fields_str": filterable_fields_str,
                },
                "suggested_metrics": [m["display_name"] for m in metrics_list[:10]],
                "suggested_dimensions": [d["display_name"] for d in dimensions_list[:10]],
                "metadata_classification": {
                    "metric_names": metric_field_names,
                    "dimension_names": dimension_field_names,
                    "metric_fields": metric_field_names,
                    "dimension_fields": dimension_field_names,
                    "time_dimensions": time_dimensions,
                    "aggregation_context": agg_context,
                },
            }
        else:
            return {
                "success": True,
                "metadata": {},
                "suggested_metrics": [],
                "suggested_dimensions": [],
                "metadata_classification": {},
            }
    except Exception as e:
        return {
            "success": False,
            "metadata": {},
            "suggested_metrics": [],
            "suggested_dimensions": [],
            "metadata_classification": {},
            "error": str(e)
        }


# ============== MQL 生成工具 ==============

@tool
async def generate_mql(
    natural_language: str,
    context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    prompt_strings: Optional[Dict[str, str]] = None,
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """根据自然语言生成 MQL（Metrics Query Language）
    
    这是 Deep Agents 的标准工具，替代 MQLGenerationSkill
    
    Args:
        natural_language: 用户的自然语言查询
        context: 上下文信息（可选）
        metadata: 元数据（可选）
        db_session: 数据库会话（可选）
    
    Returns:
        包含 MQL 的字典：
        - mql: 生成的 MQL 对象
        - confidence: 生成置信度
        - interpretation: MQL 解释
    """
    if not db_session:
        return {
            "success": False,
            "mql": None,
            "error": "需要数据库会话"
        }
    
    try:
        # 获取模型配置
        model_config = _get_model_config(db_session)
        
        if not model_config["api_key"]:
            return {
                "success": False,
                "mql": None,
                "error": "未配置模型API Key"
            }
        
        # 调用自然语言解析服务
        from app.services.nl_parser import parse_natural_language
        
        # 构建预构建的 prompt_strings 元组（如果有的话）
        prebuilt_prompt = None
        if prompt_strings:
            prebuilt_prompt = (
                prompt_strings.get("metrics_str", ""),
                prompt_strings.get("dimensions_str", ""),
                prompt_strings.get("filterable_fields_str", ""),
            )
        
        # MQL 生成任务需要较长时间，配置 300 秒超时
        generation_config = model_config["config_params"] or {}
        generation_config["timeout"] = 300.0
        
        result = await parse_natural_language(
            natural_language=natural_language,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params=generation_config,
            db=db_session,  # 用于校验器，不再用于元数据查询
            context=context,
            prompt_strings=prebuilt_prompt
        )
        
        # 返回结果
        return {
            "success": True,
            "mql": result.get("mql"),
            "confidence": result.get("confidence", 0.8),
            "interpretation": result.get("interpretation", f"生成的 MQL 用于查询: {natural_language}")
        }
    except Exception as e:
        print(f"generate_mql 错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "mql": None,
            "error": str(e)
        }


# ============== MQL 验证工具 ==============

@tool
def validate_mql(
    mql: Dict[str, Any],
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """验证 MQL 的正确性

    这是 Deep Agents 的标准工具，替代 MQLValidationSkill
    使用新的模块化校验器（MQLCompositeValidator）

    Args:
        mql: MQL 对象
        db_session: 数据库会话（可选）

    Returns:
        验证结果：
        - valid: 是否有效
        - errors: 错误列表
        - warnings: 警告列表
        - validation_result: 完整校验结果（包含所有 ValidationError）
    """
    try:
        if not db_session:
            return {
                "success": True,
                "valid": False,
                "errors": ["需要数据库会话"],
                "warnings": [],
                "validation_result": None
            }

        # 使用新的模块化校验器
        from app.utils.mql_validator.composite_validator import MQLCompositeValidator

        validator = MQLCompositeValidator(db_session)
        result = validator.validate(mql)

        # 转换错误为字典格式
        errors = [e.to_dict() for e in result.errors]
        warnings = [w.to_dict() for w in result.warnings]

        return {
            "success": True,
            "valid": result.is_valid,
            "errors": errors,
            "warnings": warnings,
            "validation_result": result.to_dict()
        }
    except Exception as e:
        return {
            "success": False,
            "valid": False,
            "errors": [str(e)],
            "warnings": [],
            "validation_result": None
        }


# ============== MQL 修正工具 ==============

@tool
async def correct_mql_auto(
    mql: Dict[str, Any],
    validation_result: Optional[Dict[str, Any]] = None,
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """自动修正 MQL 错误（使用 MQLCorrector）

    这是 Deep Agents 的标准工具，替代 MQLCorrectionSkill
    使用 MQLCorrector 自动修正校验错误

    Args:
        mql: 原始 MQL 对象
        validation_result: 校验结果（可选，如果不提供则先校验）
        db_session: 数据库会话（可选）

    Returns:
        修正后的 MQL：
        - mql: 修正后的 MQL 对象
        - corrections: 修正说明列表
        - success: 是否成功
    """
    # 如果 MQL 为 None 或空，跳过修正
    if not mql or not isinstance(mql, dict):
        print(f"[correct_mql_auto] MQL 为空或无效，跳过修正")
        return {
            "success": False,
            "mql": {},
            "corrections": [],
            "error": "MQL 为空或无效"
        }

    try:
        if not db_session:
            return {
                "success": False,
                "mql": mql,
                "corrections": [],
                "error": "需要数据库会话"
            }

        # 如果没有提供校验结果，先进行校验
        if not validation_result:
            from app.utils.mql_validator.composite_validator import MQLCompositeValidator
            validator = MQLCompositeValidator(db_session)
            val_result = validator.validate(mql)
            validation_result = val_result.to_dict()

        # 检查是否有错误需要修正
        errors_data = validation_result.get("errors", [])
        if not errors_data:
            return {
                "success": True,
                "mql": mql,
                "corrections": [],
                "message": "没有错误需要修正"
            }

        # 将字典转换回 ValidationError 对象
        from app.utils.mql_validator.base import ValidationError, Severity
        errors = []
        for e in errors_data:
            errors.append(ValidationError(
                code=e["code"],
                message=e["message"],
                severity=Severity(e["severity"]),
                field=e["field"],
                value=e.get("value"),
                suggestion=e.get("suggestion", "")
            ))

        # 使用 MQLCorrector 自动纠错
        from app.utils.mql_corrector import MQLCorrector
        corrector = MQLCorrector(db_session)
        corrected_mql = corrector.correct(mql, errors)

        # 生成修正说明
        corrections = [f"{e.code}: {e.message} -> {e.suggestion}" for e in errors if e.suggestion]

        print(f"[correct_mql_auto] 修正完成，修正项: {len(corrections)}")

        return {
            "success": True,
            "mql": corrected_mql,
            "corrections": corrections,
            "validation_result": validation_result
        }
    except Exception as e:
        print(f"[correct_mql_auto] 修正失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "mql": mql,
            "corrections": [],
            "error": str(e)
        }


# ============== MQL 修正工具 ==============

@tool
async def correct_mql(
    mql: Dict[str, Any],
    errors: List[str],
    prompt_strings: Optional[Dict[str, str]] = None,
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """修正 MQL 错误
    
    这是 Deep Agents 的标准工具，替代 MQLCorrectionSkill
    使用 LLM 智能分析错误并修正 MQL
    
    Args:
        mql: 原始 MQL 对象
        errors: 错误列表
        prompt_strings: 预构建的元数据 prompt 字符串（可选，来自准备阶段）
        db_session: 数据库会话（可选）
    
    Returns:
        修正后的 MQL：
        - mql: 修正后的 MQL 对象
        - corrections: 修正说明列表
    """
    # 如果没有错误，直接返回
    if not errors:
        return {
            "success": True,
            "mql": mql,
            "corrections": []
        }
    
    # 如果 MQL 为 None 或空，跳过修正
    if not mql or not isinstance(mql, dict):
        print(f"[correct_mql] WARN MQL 为空或无效，跳过修正")
        return {
            "success": True,
            "mql": {},
            "corrections": [],
            "error": "MQL 为空或无效"
        }
    
    try:
        # 获取模型配置
        model_config = _get_model_config(db_session)
        
        if not model_config["api_key"]:
            print(f"[correct_mql] WARN 未配置 API Key，返回原始 MQL")
            return {
                "success": True,
                "mql": mql,
                "corrections": [],
                "error": "未配置模型API Key"
            }
        
        # 构建修正 Prompt（复用预构建的元数据字符串）
        prompt = _build_correction_prompt(mql, errors, db_session, prompt_strings)
        
        # 调用 LLM 进行智能修正（MQL 修正需要较长时间，配置 300 秒超时）
        from app.services.llm_client import call_llm
        
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params={"temperature": 0.2, "max_tokens": 2048, "timeout": 300.0}
        )
        
        # 解析修正后的 MQL
        corrected_mql, corrections = _parse_correction_response(response)
        
        print(f"[correct_mql] OK 修正完成，修正项: {len(corrections)}")
        
        return {
            "success": True,
            "mql": corrected_mql or mql,
            "corrections": corrections
        }
    except Exception as e:
        print(f"[correct_mql] WARN 修正失败: {e}")
        import traceback
        traceback.print_exc()
        # 失败时返回原始 MQL
        return {
            "success": False,
            "mql": mql,
            "corrections": [],
            "error": str(e)
        }


# ============== SQL 转换工具 ==============

@tool
async def translate_to_sql(
    mql: Dict[str, Any],
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """将 MQL 转换为 SQL
    
    这是 Deep Agents 的标准工具，替代 SQLTranslationSkill
    
    Args:
        mql: MQL 对象
        db_session: 数据库会话（可选）
    
    Returns:
        SQL 转换结果：
        - sql: 生成的 SQL 语句
        - datasources: 数据源列表
        - lineage: 数据血缘
    """
    if not mql or not isinstance(mql, dict):
        return {
            "success": False,
            "sql": "",
            "datasources": [],
            "lineage": {},
            "error": "MQL 为空或无效"
        }
    
    try:
        if not db_session:
            return {
                "success": False,
                "sql": "",
                "datasources": [],
                "lineage": {},
                "error": "需要数据库会话"
            }
        
        # 调用 MQL 转换服务（V2 引擎）
        from app.services.mql_translator import MQLTranslator

        try:
            translator = MQLTranslator(db_session)
            result = translator.translate(mql)
            sql = result.get("sql", "")

            # SQL 有效性基本检查
            if not sql or " FROM " not in sql.upper():
                raise ValueError(f"V2 引擎生成的 SQL 无效（无 FROM）: {sql}")

            return {
                "success": True,
                "sql": sql,
                "datasources": [result.get("datasource_id")] if result.get("datasource_id") else [],
                "lineage": {
                    "metrics": list(result.get("mql", {}).get("metricDefinitions", {}).keys()),
                    "dimensions": list(result.get("mql", {}).get("dimensions", [])),
                },
            }
        except Exception as v2_err:
            print(f"[translate_to_sql] V2 引擎失败: {v2_err}")
            raise
    except Exception as e:
        print(f"translate_to_sql 错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "sql": "",
            "datasources": [],
            "lineage": {},
            "error": str(e)
        }


# ============== 查询执行工具 ==============

@tool
async def execute_query(
    sql: str,
    db_session: Optional[Any] = None,
    datasources: Optional[list] = None
) -> Dict[str, Any]:
    """执行 SQL 查询
    
    这是 Deep Agents 的标准工具，替代 QueryExecutionSkill
    
    Args:
        sql: SQL 语句
        db_session: 数据库会话（可选）
        datasources: 数据源 ID 列表（可选，优先使用）
    
    Returns:
        查询结果：
        - columns: 列名列表
        - data: 数据行列表
        - total_count: 总行数
    """
    if not sql:
        return {
            "success": False,
            "columns": [],
            "data": [],
            "total_count": 0,
            "error": "SQL 为空"
        }
    
    try:
        if not db_session:
            return {
                "success": False,
                "columns": [],
                "data": [],
                "total_count": 0,
                "error": "需要数据库会话"
            }
        
        # 优先使用传入的 datasources
        datasource_id = None
        
        if datasources and len(datasources) > 0:
            # 使用传入的 datasources
            datasource_id = datasources[0]
            print(f"[execute_query] 使用传入的数据源 ID: {datasource_id}")
        else:
            # 回退到查询数据库获取第一个数据源
            from app.models.datasource import DataSource
            datasource = db_session.query(DataSource).first()
            
            if not datasource:
                print(f"[execute_query] 没有可用的数据源")
                return {
                    "success": False,
                    "columns": [],
                    "data": [],
                    "total_count": 0,
                    "error": "没有可用的数据源，请先配置数据源"
                }
            
            datasource_id = datasource.id
            print(f"[execute_query] 使用数据库查询的数据源: {datasource.name} (ID: {datasource.id})")
        
        # 调用查询执行服务
        from app.services.query_executor import execute_query as exec_query
        
        result = await exec_query(
            sql=sql,
            datasource_id=datasource_id,
            limit=1000,
            db=db_session
        )
        
        # 检查执行结果
        if not result.get("success", True):
            error_msg = result.get("error", "查询执行失败")
            print(f"[execute_query] 查询执行失败: {error_msg}")
            return {
                "success": False,
                "columns": [],
                "data": [],
                "total_count": 0,
                "error": error_msg
            }
        
        return {
            "success": True,
            "columns": result.get("columns", []),
            "data": result.get("data", []),
            "total_count": result.get("total_count", 0)
        }
    except Exception as e:
        print(f"[execute_query] 错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "columns": [],
            "data": [],
            "total_count": 0,
            "error": str(e)
        }


# ============== 结果分析工具 ==============

@tool
async def analyze_result(
    query_result: Dict[str, Any],
    natural_language: str,
    intent: Optional[Dict[str, Any]] = None,
    db_session: Optional[Any] = None
) -> Dict[str, Any]:
    """分析查询结果并生成洞察
    
    这是 Deep Agents 的标准工具，替代 ResultAnalysisSkill
    使用 LLM 进行智能分析，生成洞察和可视化建议
    
    Args:
        query_result: 查询结果
        natural_language: 原始自然语言查询
        intent: 查询意图（可选）
        db_session: 数据库会话（可选）
    
    Returns:
        分析结果：
        - interpretation: 结果解释
        - insights: 洞察列表
        - visualization_suggestion: 可视化建议
    """
    try:
        if not query_result or query_result.get("error"):
            return {
                "success": True,
                "interpretation": "无有效查询结果",
                "insights": [],
                "visualization_suggestion": {"type": "table"}
            }
        
        # 获取模型配置
        model_config = _get_model_config(db_session)
        
        if not model_config["api_key"]:
            # 未配置 API Key，返回简单分析
            return {
                "success": True,
                "interpretation": f"查询返回 {query_result.get('total_count', 0)} 条结果",
                "insights": [f"共{query_result.get('total_count', 0)}条数据"],
                "visualization_suggestion": {"type": "table"}
            }
        
        # 构建分析 Prompt
        prompt = _build_analysis_prompt(query_result, natural_language, intent)
        
        # 调用 LLM
        from app.services.llm_client import call_llm
        
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params={"temperature": 0.3, "max_tokens": 1024}
        )
        
        # 解析结果
        summary, insights, visualization = _parse_analysis_response(response)
        
        return {
            "success": True,
            "interpretation": summary,
            "insights": insights,
            "visualization_suggestion": visualization
        }
    except Exception as e:
        print(f"[analyze_result] 分析失败: {e}")
        import traceback
        traceback.print_exc()
        # 失败时返回简单总结
        return {
            "success": True,
            "interpretation": f"查询返回 {query_result.get('total_count', 0)} 条结果",
            "insights": [f"共{query_result.get('total_count', 0)}条数据"],
            "visualization_suggestion": {"type": "table"},
            "error": str(e)
        }


# ============== 辅助函数 ==============

def _get_model_config(db_session: Optional[Any]) -> Dict[str, Any]:
    """获取模型配置（使用系统配置）"""
    if not db_session:
        print(f"[_get_model_config] WARN 数据库会话为空，返回默认配置")
        return {
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "api_key": None,
            "api_base": None,
            "config_params": None
        }
    
    try:
        from app.models.model_config import ModelConfig
        from app.utils.encryption import decrypt_api_key
        
        # 查询默认且激活的模型配置（系统配置）
        model_config = db_session.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()
        
        if model_config:
            print(f"[_get_model_config] OK 找到系统配置模型: {model_config.provider}/{model_config.model_name}")
            
            # 解密 API Key
            api_key = None
            if model_config.api_key:
                try:
                    api_key = decrypt_api_key(model_config.api_key)
                    print(f"[_get_model_config] OK API Key 解密成功")
                except Exception as e:
                    print(f"[_get_model_config] WARN 解密 API Key 失败: {e}")
            
            config = {
                "provider": model_config.provider,
                "model_name": model_config.model_name,
                "api_key": api_key,
                "api_base": model_config.api_base,
                "config_params": model_config.config_params
            }
            
            # 打印配置信息（隐藏敏感信息）
            print(f"[_get_model_config] 模型配置: provider={config['provider']}, model={config['model_name']}, api_key={'已设置' if api_key else '未设置'}, api_base={config['api_base']}")
            
            return config
        else:
            print(f"[_get_model_config] WARN 未找到默认且激活的模型配置，返回默认配置")
    except Exception as e:
        print(f"[_get_model_config] WARN 获取模型配置失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 返回默认配置
    return {
        "provider": "openai",
        "model_name": "gpt-3.5-turbo",
        "api_key": None,
        "api_base": None,
        "config_params": None
    }


def _build_analysis_prompt(query_result: dict, natural_language: str, intent: Optional[Dict[str, Any]]) -> str:
    """构建分析 Prompt"""
    columns = query_result.get("columns", [])
    data = query_result.get("data", [])[:5]  # 只取前5行
    total_count = query_result.get("total_count", 0)
    intent_type = intent.get("intent_type", "aggregation") if intent else "aggregation"
    
    return f"""分析查询结果并生成洞察。

## 用户查询
{natural_language}

## 查询意图
{intent_type}

## 查询结果

### 数据列
{', '.join(columns)}

### 数据样本（前5行）
{json.dumps(data, ensure_ascii=False, indent=2)}

### 总记录数
{total_count}

## 要求
1. 用1-2句话概括查询结果
2. 从数据中发现3-5个有价值的洞察
3. 推荐最适合的可视化类型

## 可视化类型说明
- line: 折线图，适合趋势分析
- bar: 柱状图，适合对比分析
- pie: 饼图，适合占比分析
- table: 表格，适合详细数据展示

## 输出格式

请返回JSON格式：
```json
{{
  "summary": "结果总结",
  "insights": ["洞察1", "洞察2", "洞察3"],
  "visualization": {{
    "type": "line",
    "description": "为什么选择这个可视化类型"
  }}
}}
```

请分析并返回："""


def _parse_analysis_response(response: str) -> tuple:
    """解析 LLM 返回的分析结果"""
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            
            summary = data.get("summary", "")
            insights = data.get("insights", [])
            visualization = data.get("visualization", {"type": "table"})
            
            # 转换为标准格式
            viz_suggestion = {
                "type": visualization.get("type", "table"),
                "description": visualization.get("description", "")
            }
            
            return summary, insights, viz_suggestion
    except Exception as e:
        print(f"[_parse_analysis_response] 解析失败: {e}")
    
    # 解析失败，返回默认值
    return "", [], {"type": "table", "description": ""}


def _build_correction_prompt(mql: dict, errors: list, db_session, prompt_strings: dict = None) -> str:
    """构建 MQL 修正 Prompt，复用 nl_parser 的标准 prompt"""
    from app.services.nl_parser import NL_TO_MQL_PROMPT
    
    # 优先使用预构建的元数据字符串，避免重复查 DB
    if prompt_strings:
        metrics_str = prompt_strings.get("metrics_str", "")
        dimensions_str = prompt_strings.get("dimensions_str", "")
        filterable_fields_str = prompt_strings.get("filterable_fields_str", "")
    else:
        # 兜底：如果没有预构建的，从 DB 查询
        from app.services.nl_parser import _build_metadata_strings
        metrics_str, dimensions_str, filterable_fields_str = _build_metadata_strings(db_session)
    
    # 格式化错误信息
    errors_str = "\n".join([f"- {err}" for err in errors])
    
    # 错误上下文
    error_info = f"""## 需要修正的 MQL
```json
{json.dumps(mql, ensure_ascii=False, indent=2)}
```

## 错误信息
{errors_str}

请根据以上错误信息修正该 MQL，保持原始查询意图不变。"""

    # 复用 NL_TO_MQL_PROMPT 的完整标准格式、规则和示例
    # 将 error_info 嵌入到 NL_TO_MQL_PROMPT 的 {error_info} 占位符中
    return NL_TO_MQL_PROMPT.format(
        metrics=metrics_str,
        dimensions=dimensions_str,
        filterable_fields=filterable_fields_str,
        query="（修正模式：请根据上方错误信息修正 MQL，输出修正后的完整 MQL JSON）",
        error_info=error_info
    )


def _parse_correction_response(response: str) -> tuple:
    """解析 LLM 返回的修正结果"""
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            
            corrected_mql = data.get("mql", {})
            corrections = data.get("corrections", [])
            
            print(f"[_parse_correction_response] 解析成功")
            print(f"  - 修正项数量: {len(corrections)}")
            print(f"  - 修正内容: {corrections}")
            
            return corrected_mql, corrections
    except Exception as e:
        print(f"[_parse_correction_response] 解析失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 解析失败，返回原始 MQL
    return {}, []


def _build_intent_analysis_prompt(natural_language: str, metadata: dict) -> str:
    """构建意图分析 Prompt"""
    # 获取指标和维度
    metrics = metadata.get("metrics", [])[:10]
    dimensions = metadata.get("dimensions", [])[:10]
    
    metrics_str = ", ".join([m.get("display_name", m.get("name", "")) for m in metrics])
    dimensions_str = ", ".join([d.get("display_name", d.get("name", "")) for d in dimensions])
    
    return f"""分析用户查询意图并返回JSON。

用户查询：{natural_language}

可用指标：{metrics_str}
可用维度：{dimensions_str}

## 意图类型说明
- trend: 趋势分析（如"销售额变化趋势"、"本月销售额走势"）
- comparison: 对比分析（如"本月vs上月"、"今年与去年对比"）
- drilldown: 下钻分析（如"查看某个省份的详细数据"、"北京市的数据"）
- attribution: 归因分析（如"为什么销售额下降"、"变化原因"）
- aggregation: 聚合统计（如"总销售额"、"平均销售额"）

## 复杂度说明
- low: 单一指标、单一维度、简单过滤
- medium: 多指标或多维度、复杂过滤
- high: 多指标多维度、复杂逻辑、需要计算

## 返回格式
请返回JSON格式：
```json
{{
  "intent_type": "trend|comparison|drilldown|attribution|aggregation",
  "description": "意图描述，简要说明用户的查询意图",
  "suggested_metrics": ["建议的指标1", "建议的指标2"],
  "suggested_dimensions": ["建议的维度1", "建议的维度2"],
  "complexity": "low|medium|high"
}}
```

请分析并返回JSON格式的意图分析结果："""


def _parse_intent_response(response: str) -> dict:
    """解析 LLM 返回的意图分析结果"""
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            
            intent = {
                "intent_type": data.get("intent_type", "aggregation"),
                "description": data.get("description", ""),
                "suggested_metrics": data.get("suggested_metrics", []),
                "suggested_dimensions": data.get("suggested_dimensions", []),
                "complexity": data.get("complexity", "low")
            }
            
            print(f"[_parse_intent_response] 解析成功")
            print(f"  - 意图类型: {intent['intent_type']}")
            print(f"  - 复杂度: {intent['complexity']}")
            print(f"  - 建议指标: {intent['suggested_metrics']}")
            print(f"  - 建议维度: {intent['suggested_dimensions']}")
            
            return intent
    except Exception as e:
        print(f"[_parse_intent_response] 解析失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 返回默认值
    return {
        "intent_type": "aggregation",
        "description": "聚合查询",
        "suggested_metrics": [],
        "suggested_dimensions": [],
        "complexity": "low"
    }


# ============== 工具集合 ==============

def get_all_tools() -> List:
    """获取所有工具
    
    返回所有 Deep Agents 工具的列表
    用于 create_deep_agent 的 tools 参数
    
    Returns:
        工具列表
    """
    return [
        analyze_intent,
        retrieve_metadata,
        generate_mql,
        validate_mql,
        correct_mql,
        translate_to_sql,
        execute_query,
        analyze_result
    ]


# ============== 工具注册表 ==============

TOOL_REGISTRY = {
    "analyze_intent": analyze_intent,
    "retrieve_metadata": retrieve_metadata,
    "generate_mql": generate_mql,
    "validate_mql": validate_mql,
    "correct_mql": correct_mql,
    "translate_to_sql": translate_to_sql,
    "execute_query": execute_query,
    "analyze_result": analyze_result
}


def get_tool_by_name(tool_name: str):
    """根据名称获取工具
    
    Args:
        tool_name: 工具名称
    
    Returns:
        工具函数，如果不存在则返回 None
    """
    return TOOL_REGISTRY.get(tool_name)
