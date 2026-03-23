# backend/app/agents/mql_agent.py

"""
MQL 查询智能体（完全基于 Deep Agents）

完全基于 LangChain Deep Agents + LangGraph 重新实现
参考：https://docs.langchain.com/oss/python/deepagents/overview

使用 create_deep_agent 创建智能体，不保留旧的架构
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.agents.deep_agents import (
    DeepAgentsManager,
    get_deep_agents_manager,
    DeepAgentState,
    create_initial_state,
    deep_agents_config
)


logger = logging.getLogger(__name__)


class MQLAgent:
    """MQL 查询智能体（基于 Deep Agents）
    
    完全基于 LangChain Deep Agents 实现的智能体
    
    架构：
    - Deep Agents Manager：管理智能体实例和工具
    - LangGraph Workflow：状态管理和流程编排（可选）
    - Deep Agents Tools：标准化工具（替代 Skills）
    
    参考：https://docs.langchain.com/oss/python/deepagents/quickstart
    
    Example:
        >>> from app.database import SessionLocal
        >>> from app.agents.mql_agent import MQLAgent
        >>> 
        >>> db = SessionLocal()
        >>> agent = MQLAgent(db)
        >>> 
        >>> result = await agent.execute_query(
        ...     natural_language="查询最近7天的销售额",
        ...     context={}
        ... )
    """
    
    def __init__(
        self,
        db_session: Session,
        query_id: str = None,
        conversation_id: str = None
    ):
        """初始化 Agent
        
        Args:
            db_session: 数据库会话
            query_id: 查询ID（用于步骤回调）
            conversation_id: 对话ID（用于保存查询历史）
        """
        self.db_session = db_session
        self.query_id = query_id
        self.conversation_id = conversation_id
        
        # 创建 Deep Agents Manager
        self.manager = get_deep_agents_manager(db_session=db_session)
        
        # 步骤回调（用于 SSE）
        if query_id:
            from app.api.v1.agent import _query_steps_store
            self.step_callback = lambda step: self._store_step(query_id, step)
        else:
            self.step_callback = None
        
        logger.info(f"[MQLAgent] 初始化完成，Deep Agents 启用: {self.manager.is_enabled()}")
    
    def _store_step(self, query_id: str, step: dict):
        """存储步骤到全局变量（用于 SSE）"""
        from app.api.v1.agent import _query_steps_store
        
        logger.info(f"[MQLAgent._store_step] Storing step for query {query_id}")
        
        if query_id not in _query_steps_store:
            _query_steps_store[query_id] = []
        
        _query_steps_store[query_id].append(step)
        
        logger.info(f"[MQLAgent._store_step] Total steps for query {query_id}: {len(_query_steps_store[query_id])}")
    
    async def execute_query(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """执行查询（主入口）
        
        使用 Deep Agents 执行完整的查询流程
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: MQL 生成最大重试次数
        
        Returns:
            查询结果字典，包含：
            - natural_language: 原始查询
            - mql: 生成的 MQL
            - sql: 转换的 SQL
            - result: 查询结果
            - interpretation: 结果解释
            - insights: 洞察列表
            - steps: 执行步骤
        """
        logger.info(f"[MQLAgent] 开始执行查询: {natural_language}")
        
        # 检查 Deep Agents 是否启用
        if not self.manager.is_enabled():
            logger.warning("[MQLAgent] Deep Agents 未启用，请检查配置")
            return {
                "success": False,
                "error": "Deep Agents 未启用，请在 .env.deep_agents 中设置 DEEP_AGENTS_ENABLED=true",
                "natural_language": natural_language
            }
        
        # 记录开始步骤
        if self.step_callback:
            self._store_step(self.query_id, {
                "title": "开始处理查询",
                "content": f"自然语言查询: {natural_language}",
                "status": "processing",
                "timestamp": datetime.now().isoformat()
            })
        
        try:
            # 使用 Deep Agents Manager 执行查询
            result = await self.manager.execute(
                natural_language=natural_language,
                context=context,
                max_retries=max_retries
            )
            
            # 添加步骤记录
            if self.step_callback and result.get("success"):
                self._store_step(self.query_id, {
                    "title": "查询执行完成",
                    "content": "成功生成并执行查询",
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"[MQLAgent] 查询执行失败: {e}")
            
            # 记录错误步骤
            if self.step_callback:
                self._store_step(self.query_id, {
                    "title": "查询执行失败",
                    "content": f"错误: {str(e)}",
                    "status": "error",
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                "success": False,
                "error": str(e),
                "natural_language": natural_language
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
        logger.info(f"[MQLAgent] 执行工具: {tool_name}")
        
        return await self.manager.execute_tool(tool_name, **kwargs)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return self.manager.get_agent_info()
    
    async def explain_result(
        self,
        query_result: Dict[str, Any],
        natural_language: str
    ) -> Dict[str, Any]:
        """解释查询结果
        
        Args:
            query_result: 查询结果
            natural_language: 原始查询
        
        Returns:
            解释结果
        """
        logger.info(f"[MQLAgent] 解释查询结果")
        
        # 使用结果分析工具
        result = await self.manager.execute_tool(
            "analyze_result",
            query_result=query_result,
            natural_language=natural_language
        )
        
        return result.get("result", {
            "interpretation": None,
            "insights": []
        })
