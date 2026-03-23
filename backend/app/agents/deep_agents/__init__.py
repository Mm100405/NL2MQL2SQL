# backend/app/agents/deep_agents/__init__.py

"""
Deep Agents 模块

基于 LangChain Deep Agents 规范的智能体实现
参考：https://docs.langchain.com/oss/python/deepagents/overview

使用 create_deep_agent 创建标准化的智能体
"""

from app.agents.deep_agents.config import (
    DeepAgentsConfig,
    deep_agents_config
)

from app.agents.deep_agents.state import (
    DeepAgentState,
    create_initial_state
)

from app.agents.deep_agents.tools import (
    retrieve_metadata,
    generate_mql,
    validate_mql,
    correct_mql,
    translate_to_sql,
    execute_query,
    analyze_result,
    get_all_tools,
    get_tool_by_name,
    TOOL_REGISTRY
)

from app.agents.deep_agents.manager import (
    DeepAgentsManager,
    get_deep_agents_manager
)


__all__ = [
    # 配置
    "DeepAgentsConfig",
    "deep_agents_config",
    
    # 状态
    "DeepAgentState",
    "create_initial_state",
    
    # 工具
    "retrieve_metadata",
    "generate_mql",
    "validate_mql",
    "correct_mql",
    "translate_to_sql",
    "execute_query",
    "analyze_result",
    "get_all_tools",
    "get_tool_by_name",
    "TOOL_REGISTRY",
    
    # 管理器
    "DeepAgentsManager",
    "get_deep_agents_manager"
]
