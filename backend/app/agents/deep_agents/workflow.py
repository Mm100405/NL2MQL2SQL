# backend/app/agents/deep_agents/workflow.py

"""
LangGraph 工作流定义（可选）

基于 LangGraph StateGraph 规范的工作流定义
参考：https://docs.langchain.com/oss/python/langgraph

这是可选的实现，Deep Agents 已经内置了工作流。
此文件展示如何使用 LangGraph + Deep Agents 的组合方式。
"""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session
import logging

from app.agents.deep_agents.state import DeepAgentState
from app.agents.deep_agents.tools import (
    analyze_intent,
    retrieve_metadata,
    generate_mql,
    validate_mql,
    correct_mql,
    correct_mql_auto,  # 新增：基于 MQLCorrector 的自动修正
    translate_to_sql,
    execute_query,
    analyze_result
)


logger = logging.getLogger(__name__)


async def preparation_node(state: DeepAgentState) -> Dict[str, Any]:
    """准备节点 - 检索元数据并分析意图

    Args:
        state: 当前状态

    Returns:
        需要更新的状态字段
    """
    natural_language = state["natural_language"]
    context = state.get("context", {})

    logger.info(f"[PreparationNode] 开始处理: {natural_language}")

    # 1. 调用元数据检索工具
    metadata_result = await retrieve_metadata.ainvoke({
        "natural_language": natural_language,
        "context": context,
        "db_session": context.get("db_session")
    })

    metadata = metadata_result.get("metadata", {})
    suggested_metrics = metadata_result.get("suggested_metrics", [])
    suggested_dimensions = metadata_result.get("suggested_dimensions", [])
    metadata_prompt_strings = metadata_result.get("metadata_prompt_strings", {})

    # 始终提取 metrics_list 和 dimensions_list（用于日志和后续引用）
    metrics_list = metadata.get("metrics", [])
    dimensions_list = metadata.get("dimensions", [])

    # 2. 构建元数据分类信息（用于 MQL 校验器）
    # 优先使用 retrieve_metadata 返回的 classification，否则从 metadata 中提取
    metadata_classification = metadata_result.get("metadata_classification")
    if not metadata_classification:
        metadata_classification = {
            "metric_names": {m.get("name") for m in metrics_list if m.get("name")},
            "dimension_names": {d.get("name") for d in dimensions_list if d.get("name")},
            "metric_fields": {m.get("name") for m in metrics_list if m.get("name")},
            "dimension_fields": {d.get("name") for d in dimensions_list if d.get("name")},
            "time_dimensions": {
                d["name"] for d in dimensions_list
                if d.get("dimension_type") == "time"
                or str(d.get("data_type", "")).lower() in ("date", "datetime", "timestamp")
            },
            "aggregation_context": {
                m.get("name"): m.get("aggregation", "SUM")
                for m in metrics_list if m.get("name")
            },
        }

    # 3. 调用意图分析工具
    intent_result = await analyze_intent.ainvoke({
        "natural_language": natural_language,
        "metadata": metadata,
        "db_session": context.get("db_session")
    })

    intent = intent_result.get("intent", {})
    intent_type = intent_result.get("intent_type", "aggregation")
    complexity = intent_result.get("complexity", "low")

    logger.info(f"[PreparationNode] 意图分析完成: type={intent_type}, complexity={complexity}")

    steps = state.get("steps", [])
    steps.append({
        "step": "preparation",
        "status": "success",
        "detail": f"检索到 {len(metrics_list)} 个指标, {len(dimensions_list)} 个维度, 意图={intent_type}, 复杂度={complexity}"
    })

    return {
        "metadata": metadata,
        "metadata_prompt_strings": metadata_prompt_strings,
        "metadata_classification": metadata_classification,
        "suggested_metrics": suggested_metrics,
        "suggested_dimensions": suggested_dimensions,
        "intent": intent,
        "intent_type": intent_type,
        "complexity": complexity,
        "steps": steps,
        "current_step": "preparation"
    }


async def generation_node(state: DeepAgentState) -> Dict[str, Any]:
    """生成节点 - 生成 MQL
    
    Args:
        state: 当前状态
    
    Returns:
        需要更新的状态字段
    """
    natural_language = state["natural_language"]
    context = state.get("context", {})
    metadata = state.get("metadata", {})
    metadata_prompt_strings = state.get("metadata_prompt_strings", {})
    
    logger.info(f"[GenerationNode] 生成 MQL")
    
    # 调用 MQL 生成工具（复用预构建的元数据字符串）
    result = await generate_mql.ainvoke({
        "natural_language": natural_language,
        "context": context,
        "metadata": metadata,
        "prompt_strings": metadata_prompt_strings or None,
        "db_session": context.get("db_session")
    })

    generated_mql = result.get("mql")
    mql_fields = list(generated_mql.keys()) if generated_mql else []
    mql_field_summary = ", ".join(f for f in mql_fields if generated_mql.get(f))

    steps = state.get("steps", [])
    steps.append({
        "step": "generation",
        "status": "success" if generated_mql else "failed",
        "detail": f"生成的 MQL 字段: {mql_field_summary}",
        "fields": mql_fields
    })

    return {
        "mql": generated_mql,
        "mql_attempts": state.get("mql_attempts", 0) + 1,
        "steps": steps,
        "current_step": "generation"
    }


async def validation_node(state: DeepAgentState) -> Dict[str, Any]:
    """验证节点 - 验证 MQL

    Args:
        state: 当前状态

    Returns:
        需要更新的状态字段
    """
    mql = state.get("mql")
    context = state.get("context", {})

    if not mql:
        steps = state.get("steps", [])
        steps.append({"step": "validation", "status": "failed", "detail": "MQL 为空"})
        return {
            "mql_errors": ["MQL 为空"],
            "mql_validation_result": None,
            "steps": steps,
            "current_step": "validation"
        }

    logger.info(f"[ValidationNode] 验证 MQL")

    # 调用 MQL 验证工具
    result = await validate_mql.ainvoke({
        "mql": mql,
        "db_session": context.get("db_session")
    })

    # 获取验证结果
    validation_result = result.get("validation_result")
    is_valid = result.get("valid", False)

    if not is_valid:
        # MQL 无效，需要修正
        errors = result.get("errors", [])
        error_codes = [e.get("code", str(e)) if isinstance(e, dict) else str(e) for e in errors]
        logger.warning(f"[ValidationNode] MQL 校验失败: {len(errors)} 个错误 - {error_codes}")

        steps = state.get("steps", [])
        steps.append({
            "step": "validation",
            "status": "failed",
            "detail": f"{len(errors)} 个错误: {error_codes}",
            "error_codes": error_codes
        })

        return {
            "mql_errors": errors,
            "mql_validation_result": validation_result,
            "steps": steps,
            "current_step": "validation"
        }

    steps = state.get("steps", [])
    steps.append({"step": "validation", "status": "success", "detail": "MQL 校验通过"})

    return {
        "mql_errors": [],
        "mql_validation_result": validation_result,
        "steps": steps,
        "current_step": "validation"
    }


def should_correct(state: DeepAgentState) -> str:
    """判断是否需要修正 MQL

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    mql_errors = state.get("mql_errors", [])
    mql_attempts = state.get("mql_attempts", 0)
    max_retries = state.get("max_retries", 3)

    if mql_errors and mql_attempts < max_retries:
        return "correction"
    else:
        return "translation"


async def correction_node(state: DeepAgentState) -> Dict[str, Any]:
    """修正节点 - 修正 MQL（双模式：自动修正 + LLM 兜底）

    流程：
    1. 先调用 MQLCorrector 自动修正（基于规则的策略模式）
    2. 重新验证自动修正后的 MQL
    3. 如果仍有错误且还有重试次数，调用 LLM 智能修正兜底
    4. 清空错误，回到 validation 节点重新验证

    Args:
        state: 当前状态

    Returns:
        需要更新的状态字段
    """
    mql = state.get("mql", {})
    mql_validation_result = state.get("mql_validation_result")
    context = state.get("context", {})
    mql_attempts = state.get("mql_attempts", 0)
    max_retries = state.get("max_retries", 3)
    steps = state.get("steps", [])
    metadata_prompt_strings = state.get("metadata_prompt_strings", {})

    logger.info(f"[CorrectionNode] 修正 MQL (attempt {mql_attempts + 1}/{max_retries})")

    # 如果 MQL 为 None 或空，跳过修正
    if not mql or not isinstance(mql, dict):
        logger.warning("[CorrectionNode] MQL 为空或无效，跳过修正")
        steps.append({"step": "correction", "status": "skipped", "detail": "MQL 为空"})
        return {
            "mql": {},
            "mql_attempts": mql_attempts + 1,
            "mql_errors": [],
            "steps": steps,
            "current_step": "correction"
        }

    # === 阶段 1：自动修正（MQLCorrector 基于规则） ===
    logger.info("[CorrectionNode] 阶段1: 自动修正（策略模式）")
    auto_result = await correct_mql_auto.ainvoke({
        "mql": mql,
        "validation_result": mql_validation_result,
        "db_session": context.get("db_session")
    })

    corrected_mql = auto_result.get("mql", mql)
    auto_corrections = auto_result.get("corrections", [])

    # 重新验证自动修正后的 MQL
    val_result = await validate_mql.ainvoke({
        "mql": corrected_mql,
        "db_session": context.get("db_session")
    })

    is_valid = val_result.get("valid", False)
    remaining_errors = val_result.get("errors", [])

    if is_valid:
        logger.info(f"[CorrectionNode] 自动修正成功，修正项: {len(auto_corrections)}")
        steps.append({
            "step": "correction",
            "status": "success",
            "mode": "auto",
            "detail": f"自动修正 {len(auto_corrections)} 项",
            "corrections": auto_corrections
        })
        return {
            "mql": corrected_mql,
            "mql_attempts": mql_attempts + 1,
            "mql_errors": [],
            "mql_validation_result": None,
            "steps": steps,
            "current_step": "correction"
        }

    # === 阶段 2：LLM 兜底修正（如果自动修正未能完全修复） ===
    logger.info(f"[CorrectionNode] 自动修正后仍有 {len(remaining_errors)} 个错误，启用 LLM 兜底")
    error_messages = [e.get("message", str(e)) if isinstance(e, dict) else str(e) for e in remaining_errors]

    llm_result = await correct_mql.ainvoke({
        "mql": corrected_mql,
        "errors": error_messages,
        "prompt_strings": metadata_prompt_strings or None,
        "db_session": context.get("db_session")
    })

    llm_corrected_mql = llm_result.get("mql", corrected_mql)
    llm_corrections = llm_result.get("corrections", [])

    steps.append({
        "step": "correction",
        "status": "success" if llm_result.get("success") else "partial",
        "mode": "auto+llm",
        "detail": f"自动修正 {len(auto_corrections)} 项, LLM 修正 {len(llm_corrections)} 项",
        "auto_corrections": auto_corrections,
        "llm_corrections": llm_corrections
    })

    return {
        "mql": llm_corrected_mql,
        "mql_attempts": mql_attempts + 1,
        "mql_errors": [],
        "mql_validation_result": None,
        "steps": steps,
        "current_step": "correction"
    }


async def translation_node(state: DeepAgentState) -> Dict[str, Any]:
    """翻译节点 - 将 MQL 转换为 SQL
    
    Args:
        state: 当前状态
    
    Returns:
        需要更新的状态字段
    """
    mql = state.get("mql")
    context = state.get("context", {})
    
    if not mql:
        steps = state.get("steps", [])
        steps.append({"step": "translation", "status": "skipped", "detail": "MQL 为空"})
        return {
            "sql": "",
            "steps": steps,
            "current_step": "translation"
        }
    
    logger.info(f"[TranslationNode] 转换为 SQL")
    
    # 调用 SQL 转换工具
    result = await translate_to_sql.ainvoke({
        "mql": mql,
        "db_session": context.get("db_session")
    })
    
    sql = result.get("sql", "")
    datasources = result.get("datasources", [])

    mql_features = [k for k in ("windowFunctions", "union", "cte") if mql.get(k)]
    feature_info = f", 高级特性: {mql_features}" if mql_features else ""

    steps = state.get("steps", [])
    steps.append({
        "step": "translation",
        "status": "success" if sql else "failed",
        "detail": f"SQL 生成完成, 数据源: {datasources}, MQL 字段: {list(mql.keys())}{feature_info}"
    })
    
    return {
        "sql": sql,
        "sql_datasources": datasources,
        "steps": steps,
        "current_step": "translation"
    }


async def execution_node(state: DeepAgentState) -> Dict[str, Any]:
    """执行节点 - 执行 SQL 查询
    
    Args:
        state: 当前状态
    
    Returns:
        需要更新的状态字段
    """
    sql = state.get("sql", "")
    sql_datasources = state.get("sql_datasources", [])  # 获取数据源列表
    context = state.get("context", {})
    
    if not sql:
        logger.warning("[ExecutionNode] SQL 为空")
        steps = state.get("steps", [])
        steps.append({"step": "execution", "status": "skipped", "detail": "SQL 为空"})
        return {
            "query_result": None,
            "steps": steps,
            "current_step": "execution",
            "error": "SQL 为空"
        }
    
    logger.info(f"[ExecutionNode] 执行查询: {sql}")
    logger.info(f"[ExecutionNode] 可用数据源: {sql_datasources}")
    
    # 调用查询执行工具
    result = await execute_query.ainvoke({
        "sql": sql,
        "db_session": context.get("db_session"),
        "datasources": sql_datasources
    })
    
    steps = state.get("steps", [])

    # 检查执行结果
    if not result.get("success", True):
        error_msg = result.get("error", "查询执行失败")
        logger.error(f"[ExecutionNode] 查询执行失败: {error_msg}")
        steps.append({"step": "execution", "status": "failed", "detail": error_msg})
        return {
            "query_result": None,
            "steps": steps,
            "current_step": "execution",
            "error": error_msg
        }
    
    query_result = {
        "columns": result.get("columns", []),
        "data": result.get("data", []),
        "total_count": result.get("total_count", 0)
    }
    
    logger.info(f"[ExecutionNode] 查询执行成功，返回 {query_result['total_count']} 行数据")
    steps.append({
        "step": "execution",
        "status": "success",
        "detail": f"返回 {query_result['total_count']} 行, {len(query_result['columns'])} 列: {query_result['columns']}"
    })
    
    return {
        "query_result": query_result,
        "steps": steps,
        "current_step": "execution"
    }


async def interpretation_node(state: DeepAgentState) -> Dict[str, Any]:
    """解释节点 - 分析结果并生成洞察
    
    Args:
        state: 当前状态
    
    Returns:
        需要更新的状态字段
    """
    query_result = state.get("query_result")
    natural_language = state["natural_language"]
    intent = state.get("intent", {})
    context = state.get("context", {})
    
    # 如果查询结果为空，检查是否有错误信息
    if not query_result:
        error = state.get("error", "查询结果为空")
        logger.warning(f"[InterpretationNode] 查询结果为空: {error}")
        steps = state.get("steps", [])
        steps.append({"step": "interpretation", "status": "failed", "detail": error})

        return {
            "interpretation": f"查询执行失败: {error}",
            "insights": [],
            "steps": steps,
            "current_step": "interpretation",
            "error": error
        }
    
    logger.info(f"[InterpretationNode] 分析结果")
    
    # 调用结果分析工具
    result = await analyze_result.ainvoke({
        "query_result": query_result,
        "natural_language": natural_language,
        "intent": intent,
        "db_session": context.get("db_session")
    })

    insights = result.get("insights", [])
    viz = result.get("visualization_suggestion", {})

    steps = state.get("steps", [])
    steps.append({
        "step": "interpretation",
        "status": "success",
        "detail": f"生成 {len(insights)} 条洞察, 可视化建议: {viz.get('type', 'table') if viz else 'none'}"
    })
    
    return {
        "interpretation": result.get("interpretation"),
        "insights": insights,
        "visualization_suggestion": viz,
        "steps": steps,
        "current_step": "interpretation"
    }


def create_mql_workflow() -> StateGraph:
    """创建 MQL 查询工作流
    
    使用 LangGraph StateGraph 创建标准的查询流程
    
    Returns:
        编译后的工作流图
    """
    # 创建状态图
    workflow = StateGraph(DeepAgentState)
    
    # 添加节点
    workflow.add_node("preparation", preparation_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("correction", correction_node)
    workflow.add_node("translation", translation_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("interpretation", interpretation_node)
    
    # 添加边（线性流程）
    workflow.set_entry_point("preparation")
    workflow.add_edge("preparation", "generation")
    workflow.add_edge("generation", "validation")
    
    # 条件边：根据验证结果决定下一步
    workflow.add_conditional_edges(
        "validation",
        should_correct,
        {
            "correction": "correction",
            "translation": "translation"
        }
    )
    
    # 修正后重新验证
    workflow.add_edge("correction", "validation")
    
    # 继续后续流程
    workflow.add_edge("translation", "execution")
    workflow.add_edge("execution", "interpretation")
    workflow.add_edge("interpretation", END)
    
    # 编译工作流
    return workflow.compile()


# ============== 全局工作流实例 ==============

_mql_workflow = None


def get_mql_workflow() -> StateGraph:
    """获取全局 MQL 工作流实例
    
    Returns:
        编译后的工作流图
    """
    global _mql_workflow
    
    if _mql_workflow is None:
        _mql_workflow = create_mql_workflow()
    
    return _mql_workflow
