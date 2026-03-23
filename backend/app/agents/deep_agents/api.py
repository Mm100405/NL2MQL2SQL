# backend/app/agents/deep_agents/api.py

"""
Deep Agents API 辅助函数

提供 Deep Agents 相关的 API 辅助函数
"""

from typing import Dict, Any, List
from app.agents.deep_agents import (
    get_deep_agents_manager,
    get_all_tools,
    TOOL_REGISTRY
)


def get_deep_agents_status() -> Dict[str, Any]:
    """获取 Deep Agents 状态
    
    Returns:
        Deep Agents 状态信息
    """
    manager = get_deep_agents_manager()
    
    return {
        "enabled": manager.is_enabled(),
        "info": manager.get_agent_info()
    }


def get_deep_agents_tools() -> List[Dict[str, Any]]:
    """获取所有 Deep Agents 工具列表
    
    Returns:
        工具信息列表
    """
    tools = []
    
    for tool_name, tool_func in TOOL_REGISTRY.items():
        tools.append({
            "name": tool_name,
            "description": tool_func.description if hasattr(tool_func, 'description') else "",
            "args_schema": tool_func.args_schema.schema() if hasattr(tool_func, 'args_schema') else {}
        })
    
    return tools
