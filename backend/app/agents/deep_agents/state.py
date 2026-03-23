# backend/app/agents/deep_agents/state.py

"""
Deep Agents 状态定义

基于 LangGraph StateGraph 规范的状态定义
参考：https://docs.langchain.com/oss/python/deepagents/overview
"""

from typing import TypedDict, Optional, List, Dict, Any
from typing_extensions import Annotated
from langgraph.graph import add_messages


class DeepAgentState(TypedDict):
    """Deep Agents 状态

    基于 LangGraph StateGraph 规范，使用 add_messages 进行消息管理

    参考：https://docs.langchain.com/oss/python/deepagents/state

    Attributes:
        # LangGraph 内置消息（必需）
        messages: LangGraph 内部使用的消息列表（自动管理）

        # 输入
        natural_language: 用户的自然语言查询
        context: 上下文信息（可选）

        # 元数据（Node 1 扩展）
        metadata: 检索到的元数据（指标、维度、可过滤字段）
        metadata_classification: 元数据分类信息
            - metric_names: 指标名称集合
            - dimension_names: 维度名称集合
            - metric_fields: 指标字段（只能在 having，不能在 filters）
            - dimension_fields: 维度字段（只能在 filters）
            - time_dimensions: 时间维度集合
            - aggregation_context: 每个指标的聚合类型映射
        suggested_metrics: 建议的指标列表
        suggested_dimensions: 建议的维度列表

        # 意图
        intent: 意图分析结果
        intent_type: 意图类型（trend、comparison、drilldown、attribution、aggregation）
        complexity: 查询复杂度（low、medium、high）

        # MQL V2
        mql: 生成的MQL对象（支持全部11个字段）
        mql_attempts: MQL生成尝试次数
        mql_errors: MQL验证错误列表（ValidationError 对象列表）
        mql_validation_result: MQL校验结果（完整 ValidationResult）

        # SQL
        sql: 转换后的SQL语句
        sql_datasources: SQL涉及的数据源列表

        # 查询结果
        query_result: 查询执行结果
        query_id: 查询ID

        # 结果解释
        interpretation: 结果解释
        insights: 洞察列表
        visualization_suggestion: 可视化建议

        # 执行步骤
        steps: 执行步骤列表（用于前端展示）

        # 控制状态
        retry_count: 当前重试次数
        max_retries: 最大重试次数
        current_step: 当前步骤名称

        # Deep Agents 特有字段
        todos: 任务列表（Deep Agents 规划器生成）
        current_task: 当前执行的任务
        files_created: 创建的文件列表
        files_read: 读取的文件列表
    """
    
    # LangGraph 内置消息（必需）
    messages: Annotated[list, add_messages]
    
    # 输入
    natural_language: str
    context: Optional[Dict[str, Any]]
    
    # 元数据
    metadata: Dict[str, Any]
    metadata_prompt_strings: Dict[str, str]  # 预构建的元数据 prompt 字符串（metrics_str, dimensions_str, filterable_fields_str）
    suggested_metrics: List[str]
    suggested_dimensions: List[str]
    
    # 意图
    intent: Dict[str, Any]
    intent_type: Optional[str]
    complexity: Optional[str]
    
    # MQL
    mql: Optional[Dict[str, Any]]
    mql_attempts: int
    mql_errors: List[str]
    
    # SQL
    sql: Optional[str]
    sql_datasources: List[str]
    
    # 查询结果
    query_result: Optional[Dict[str, Any]]
    query_id: Optional[str]
    
    # 结果解释
    interpretation: Optional[Dict[str, Any]]
    insights: List[str]
    visualization_suggestion: Optional[Dict[str, Any]]
    
    # 执行步骤
    steps: List[Dict[str, Any]]
    
    # 控制状态
    retry_count: int
    max_retries: int
    current_step: Optional[str]
    
    # Deep Agents 特有字段
    todos: List[Dict[str, Any]]
    current_task: Optional[str]
    files_created: List[str]
    files_read: List[str]


def create_initial_state(
    natural_language: str,
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> DeepAgentState:
    """创建初始状态

    Args:
        natural_language: 自然语言查询
        context: 上下文信息
        max_retries: 最大重试次数

    Returns:
        初始化的状态字典
    """
    return {
        # LangGraph 内置消息（必需）
        "messages": [],

        # 输入
        "natural_language": natural_language,
        "context": context or {},

        # 元数据（Node 1 扩展）
        "metadata": {},
        "metadata_classification": {
            "metric_names": set(),
            "dimension_names": set(),
            "metric_fields": set(),      # 指标字段（只能在 having，不能在 filters）
            "dimension_fields": set(),   # 维度字段（只能在 filters）
            "time_dimensions": set(),
            "aggregation_context": {},  # metric_name -> aggregation type
        },
        "suggested_metrics": [],
        "suggested_dimensions": [],

        # 意图
        "intent": {},
        "intent_type": None,
        "complexity": None,

        # MQL V2
        "mql": None,
        "mql_attempts": 0,
        "mql_errors": [],
        "mql_validation_result": None,

        # SQL
        "sql": None,
        "sql_datasources": [],

        # 查询结果
        "query_result": None,
        "query_id": None,

        # 结果解释
        "interpretation": None,
        "insights": [],
        "visualization_suggestion": None,

        # 执行步骤
        "steps": [],

        # 控制状态
        "retry_count": 0,
        "max_retries": max_retries,
        "current_step": None,

        # Deep Agents 特有字段
        "todos": [],
        "current_task": None,
        "files_created": [],
        "files_read": [],
    }
