# backend/app/agents/deep_agents/manager.py

"""
Deep Agents 管理器

基于 LangChain Deep Agents 规范的智能体管理
参考：https://docs.langchain.com/oss/python/deepagents/overview

使用 create_deep_agent 创建和管理智能体实例
"""

import os
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
import logging

from app.agents.deep_agents.config import deep_agents_config, DeepAgentsConfig
from app.agents.deep_agents.tools import get_all_tools, get_tool_by_name
from app.agents.deep_agents.state import DeepAgentState, create_initial_state


logger = logging.getLogger(__name__)


class DeepAgentsManager:
    """Deep Agents 管理器
    
    负责：
    1. 创建和管理 Deep Agents 实例
    2. 加载配置和工具
    3. 执行查询流程
    4. 管理状态和记忆
    
    参考：https://docs.langchain.com/oss/python/deepagents/quickstart
    """
    
    def __init__(
        self,
        config: Optional[DeepAgentsConfig] = None,
        db_session: Optional[Session] = None
    ):
        """初始化 Deep Agents 管理器
        
        Args:
            config: Deep Agents 配置（可选，默认使用全局配置）
            db_session: 数据库会话（可选）
        """
        self.config = config or deep_agents_config
        self.db_session = db_session
        self.agent = None
        self.checkpointer = None
        
        # 初始化智能体
        if self.config.enabled:
            self.agent = self._create_agent()
            logger.info(f"[DeepAgentsManager] Deep Agents 已启用，模型: {self.config.model}")
        else:
            logger.info("[DeepAgentsManager] Deep Agents 未启用")
    
    def _create_agent(self):
        """创建 LangGraph 工作流智能体
        
        使用 LangGraph StateGraph 创建工作流，不依赖 deepagents 包
        """
        try:
            # 使用 LangGraph 工作流
            from app.agents.deep_agents.workflow import get_mql_workflow
            
            # 获取工作流
            agent = get_mql_workflow()
            
            # 配置 checkpointer（记忆）
            if self.config.enable_memory:
                self.checkpointer = MemorySaver()
            
            logger.info(f"[DeepAgentsManager] LangGraph 工作流创建成功")
            
            return agent
            
        except Exception as e:
            logger.error(f"[DeepAgentsManager] 创建工作流失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def execute_stream(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        step_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """流式执行查询（支持实时输出中间步骤）
        
        使用 LangGraph 的 astream 方法实现流式输出
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: 最大重试次数
            step_callback: 步骤回调函数（可选）
        
        Returns:
            查询结果字典
        """
        if not self.agent:
            return {
                "success": False,
                "error": "工作流未启用或创建失败",
                "natural_language": natural_language
            }
        
        # 创建初始状态
        initial_state = create_initial_state(
            natural_language=natural_language,
            context=context,
            max_retries=max_retries
        )
        
        # 添加 db_session 到 context（用于工具）
        if self.db_session:
            context = context or {}
            context["db_session"] = self.db_session
            initial_state["context"] = context
        
        try:
            logger.info(f"[DeepAgentsManager] 开始流式执行工作流: {natural_language}")
            logger.info(f"[DeepAgentsManager] 初始状态: {list(initial_state.keys())}")
            
            # 使用 astream 流式执行工作流
            # astream 返回异步迭代器，每次迭代返回一个或多个节点的输出
            async for event in self.agent.astream(initial_state):
                logger.info(f"[DeepAgentsManager] 收到事件: {type(event)}, 内容: {event}")
                
                # event 格式: {节点名: 节点输出} 或 {__start__: ...}, {__end__: ...}
                if isinstance(event, dict):
                    for node_name, node_output in event.items():
                        # 跳过 __start__ 和 __end__ 等特殊节点
                        if node_name.startswith('__'):
                            continue
                        
                        logger.info(f"[DeepAgentsManager] 节点执行: {node_name}")
                        logger.info(f"[DeepAgentsManager] 节点输出类型: {type(node_output)}")
                        
                        # 更新状态
                        if isinstance(node_output, dict):
                            logger.info(f"[DeepAgentsManager] 更新状态: {list(node_output.keys())}")
                            initial_state.update(node_output)
                        
                        # 调用步骤回调
                        if step_callback:
                            step_info = self._create_step_info(
                                node_name, 
                                initial_state
                            )
                            step_callback(step_info)
            
            logger.info(f"[DeepAgentsManager] 工作流执行完成")
            logger.info(f"[DeepAgentsManager] 最终状态: {list(initial_state.keys())}")
            
            # 提取结果
            return self._extract_result(initial_state, natural_language)
            
        except Exception as e:
            logger.error(f"[DeepAgentsManager] 流式执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "natural_language": natural_language
            }
    
    def _create_step_info(self, node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """创建步骤信息
        
        Args:
            node_name: 节点名称
            state: 当前状态
        
        Returns:
            步骤信息字典
        """
        step_info = {
            "node": node_name,
            "title": "",
            "content": "",
            "status": "processing",
            "timestamp": None
        }
        
        # 根据节点名称创建步骤信息
        if node_name == "preparation":
            step_info.update({
                "title": "准备阶段",
                "content": "检索元数据",
                "metadata": state.get("metadata", {}),
                "suggested_metrics": state.get("suggested_metrics", []),
                "suggested_dimensions": state.get("suggested_dimensions", [])
            })
        elif node_name == "generation":
            step_info.update({
                "title": "MQL 生成",
                "content": "生成 Metrics Query Language",
                "mql": state.get("mql"),
                "mql_attempts": state.get("mql_attempts", 1),
                "mql_errors": state.get("mql_errors", [])
            })
        elif node_name == "validation":
            step_info.update({
                "title": "MQL 验证",
                "content": "验证 MQL 语法和语义",
                "mql_errors": state.get("mql_errors", []),
                "valid": len(state.get("mql_errors", [])) == 0
            })
        elif node_name == "correction":
            step_info.update({
                "title": "MQL 修正",
                "content": "修正 MQL 错误",
                "mql": state.get("mql")
            })
        elif node_name == "translation":
            step_info.update({
                "title": "SQL 转换",
                "content": "将 MQL 转换为 SQL",
                "sql": state.get("sql", ""),
                "sql_datasources": state.get("sql_datasources", [])
            })
        elif node_name == "execution":
            step_info.update({
                "title": "查询执行",
                "content": "执行 SQL 查询",
                "query_result": state.get("query_result")
            })
        elif node_name == "interpretation":
            step_info.update({
                "title": "结果分析",
                "content": "分析查询结果并生成洞察",
                "interpretation": state.get("interpretation"),
                "insights": state.get("insights", []),
                "visualization_suggestion": state.get("visualization_suggestion")
            })
        
        # 更新时间戳
        from datetime import datetime
        step_info["timestamp"] = datetime.now().isoformat()
        
        # 如果状态中有错误，标记为失败
        if node_name == "interpretation" and state.get("query_result") is None:
            step_info["status"] = "failed"
        
        return step_info

    async def execute(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """执行查询（非流式）
        
        这是主要的执行入口，使用 LangGraph 工作流执行完整的查询流程
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: 最大重试次数
        
        Returns:
            查询结果字典
        """
        # 使用流式执行，但不传入回调
        return await self.execute_stream(
            natural_language=natural_language,
            context=context,
            max_retries=max_retries,
            step_callback=None
        )
    
    def _extract_result(
        self,
        agent_result: Dict[str, Any],
        natural_language: str
    ) -> Dict[str, Any]:
        """从智能体结果中提取查询结果
        
        Args:
            agent_result: 智能体执行结果
            natural_language: 原始自然语言查询
        
        Returns:
            标准化的查询结果
        """
        # 从状态中提取数据
        state = agent_result if isinstance(agent_result, dict) else {}
        
        # 检查是否有错误
        error = state.get("error")
        if error:
            logger.error(f"[DeepAgentsManager] 查询执行失败: {error}")
            return {
                "success": False,
                "natural_language": natural_language,
                "mql": state.get("mql"),
                "sql": state.get("sql"),
                "result": None,
                "interpretation": None,
                "insights": [],
                "error": error
            }
        
        # 检查查询结果是否为 None
        query_result = state.get("query_result")
        if query_result is None:
            logger.warning(f"[DeepAgentsManager] 查询结果为空")
            return {
                "success": False,
                "natural_language": natural_language,
                "mql": state.get("mql"),
                "sql": state.get("sql"),
                "result": None,
                "interpretation": state.get("interpretation"),
                "insights": state.get("insights", []),
                "error": "查询结果为空，可能执行失败"
            }
        
        # 成功查询
        return {
            "success": True,
            "natural_language": natural_language,
            "mql": state.get("mql"),
            "sql": state.get("sql"),
            "result": state.get("query_result"),
            "interpretation": state.get("interpretation"),
            "insights": state.get("insights", []),
            "visualization": state.get("visualization_suggestion"),
            "steps": state.get("steps", []),
            "todos": state.get("todos", []),
            "files_created": state.get("files_created", []),
            "files_read": state.get("files_read", [])
        }
    
    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """直接执行单个工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
        
        Returns:
            工具执行结果
        """
        tool = get_tool_by_name(tool_name)
        
        if not tool:
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}"
            }
        
        try:
            # 添加 db_session 到参数
            if self.db_session and "db_session" not in kwargs:
                kwargs["db_session"] = self.db_session
            
            # 执行工具
            result = await tool.ainvoke(kwargs)
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"[DeepAgentsManager] 工具执行失败 ({tool_name}): {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def is_enabled(self) -> bool:
        """检查 Deep Agents 是否启用"""
        return self.config.enabled and self.agent is not None
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "enabled": self.config.enabled,
            "model": self.config.model,
            "enable_planning": self.config.enable_planning,
            "enable_file_system": self.config.enable_file_system,
            "enable_memory": self.config.enable_memory,
            "tools_count": len(get_all_tools())
        }


# ============== 全局管理器实例 ==============

_global_manager: Optional[DeepAgentsManager] = None


def get_deep_agents_manager(
    db_session: Optional[Session] = None,
    config: Optional[DeepAgentsConfig] = None
) -> DeepAgentsManager:
    """获取全局 Deep Agents 管理器实例
    
    Args:
        db_session: 数据库会话（可选）
        config: Deep Agents 配置（可选）
    
    Returns:
        Deep Agents 管理器实例
    """
    global _global_manager
    
    if _global_manager is None or db_session or config:
        _global_manager = DeepAgentsManager(
            config=config,
            db_session=db_session
        )
    
    return _global_manager
