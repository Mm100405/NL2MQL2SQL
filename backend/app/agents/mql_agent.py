# backend/app/agents/mql_agent.py

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.agents.workflows.mql_query_workflow import create_mql_query_workflow
from app.agents.state.query_state import QueryState


class MQLAgent:
    """MQL查询智能体
    
    企业级4节点LangGraph智能体，支持：
    - LLM智能路由
    - 动态Skill选择
    - MQL自动修正
    - 结果智能分析
    
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
    
    def __init__(self, db_session: Session, query_id: str = None, conversation_id: str = None):
        """初始化Agent
        
        Args:
            db_session: 数据库会话
            query_id: 查询ID（用于步骤回调）
            conversation_id: 对话ID（用于保存查询历史）
        """
        self.db_session = db_session
        self.query_id = query_id
        self.conversation_id = conversation_id
        
        # 创建步骤回调
        if query_id:
            from app.api.v1.agent import _query_steps_store
            self.step_callback = lambda step: self._store_step(query_id, step)
        else:
            self.step_callback = None
        
        self.workflow = self._create_workflow()
    
    def _store_step(self, query_id: str, step: dict):
        """存储步骤到全局变量"""
        from app.api.v1.agent import _query_steps_store
        print(f"[MQLAgent._store_step] Storing step for query {query_id}")
        print(f"[MQLAgent._store_step] Step: {step}")
        if query_id not in _query_steps_store:
            _query_steps_store[query_id] = []
            print(f"[MQLAgent._store_step] Created new list for query {query_id}")
        _query_steps_store[query_id].append(step)
        print(f"[MQLAgent._store_step] Total steps for query {query_id}: {len(_query_steps_store[query_id])}")
        print(f"[Step] Query {query_id}: {step['title']} - {step['status']}")
    
    def _create_workflow(self):
        """创建工作流（带步骤回调）"""
        from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow
        workflow = MQLQueryWorkflow(self.db_session, step_callback=self.step_callback)
        
        return workflow.get_graph()
    
    async def execute_query(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """执行查询
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: MQL生成最大重试次数
        
        Returns:
            查询结果字典，包含：
            - natural_language: 原始查询
            - mql: 生成的MQL
            - sql: 转换的SQL
            - result: 查询结果
            - interpretation: 结果解释
            - insights: 洞察列表
            - steps: 执行步骤
        """
        # 初始化状态
        initial_state: QueryState = {
            "natural_language": natural_language,
            "context": context or {},
            "metadata": {},
            "suggested_metrics": [],
            "suggested_dimensions": [],
            "intent": {},
            "intent_type": None,
            "complexity": None,
            "mql": None,
            "mql_attempts": 0,
            "mql_errors": [],
            "sql": None,
            "sql_datasources": [],
            "query_result": None,
            "query_id": None,
            "interpretation": None,
            "insights": [],
            "visualization_suggestion": None,
            "steps": [],
            "retry_count": 0,
            "max_retries": max_retries,
            "messages": []
        }
        
        # 运行工作流
        final_state = await self.workflow.ainvoke(initial_state)
        
        # 返回结果
        return {
            "natural_language": natural_language,
            "mql": final_state.get("mql"),
            "sql": final_state.get("sql"),
            "result": final_state.get("query_result"),
            "interpretation": final_state.get("interpretation"),
            "insights": final_state.get("insights", []),
            "visualization": final_state.get("visualization_suggestion"),
            "steps": final_state.get("steps", []),
            "query_id": final_state.get("query_id"),
            "mql_attempts": final_state.get("mql_attempts", 0)
        }
    
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
        from app.agents.skills.skill_loader import SkillLoader
        
        loader = SkillLoader(self.db_session)
        skill = loader.get_skill("result_interpretation")
        
        if not skill:
            return {
                "summary": "结果解释功能不可用",
                "insights": []
            }
        
        result = await skill.execute({
            "query_result": query_result,
            "natural_language": natural_language
        })
        
        return result
