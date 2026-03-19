# backend/app/agents/state/query_state.py

from typing import TypedDict, Optional, List, Dict, Any
from typing_extensions import Annotated
from langgraph.graph import add_messages


class QueryState(TypedDict):
    """查询状态
    
    定义了整个查询流程中需要维护的所有状态信息。
    
    Attributes:
        # 输入
        natural_language: 用户的自然语言查询
        context: 上下文信息（可选）
        
        # 元数据
        metadata: 检索到的元数据（指标、维度、可过滤字段）
        suggested_metrics: 建议的指标列表
        suggested_dimensions: 建议的维度列表
        
        # 意图
        intent: 意图分析结果
        intent_type: 意图类型（trend、comparison、drilldown、attribution、aggregation）
        complexity: 查询复杂度（low、medium、high）
        
        # MQL
        mql: 生成的MQL对象
        mql_attempts: MQL生成尝试次数
        mql_errors: MQL验证错误列表
        
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
        
        # LangGraph 消息
        messages: LangGraph内部使用的消息列表
    """
    
    # 输入
    natural_language: str
    context: Optional[Dict[str, Any]]
    
    # 元数据
    metadata: Dict[str, Any]
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
    
    # LangGraph 消息
    messages: Annotated[list, add_messages]
