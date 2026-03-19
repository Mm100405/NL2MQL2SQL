# backend/app/agents/nodes/execution_node.py

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.agents.skills.skill_loader import SkillLoader
from app.agents.routers.llm_router import LLMRouter


class ExecutionNode(BaseNode):
    """执行节点 - 动态选择并执行执行阶段的Skill
    
    职责：
    1. 将MQL转换为SQL
    2. 执行SQL查询
    3. 保存查询历史
    
    可用Skills：
    - sql_translation: MQL转SQL
    - query_execution: 执行查询
    """
    
    node_name = "execution"
    description = "转换SQL并执行查询"
    
    AVAILABLE_SKILLS = [
        "sql_translation",
        "query_execution"
    ]
    
    def __init__(self, db: Session = None, step_callback=None):
        """初始化执行节点"""
        super().__init__(db, step_callback=step_callback)
        self.skill_loader = SkillLoader(db)
        self.router = LLMRouter(self.skill_loader, db)
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """执行执行节点
        
        流程：
        1. 检查MQL是否有效
        2. LLM路由决策
        3. 执行Skills（SQL转换、查询执行）
        4. 保存查询历史
        
        Args:
            state: 当前查询状态
            config: 配置信息
        
        Returns:
            更新的状态字段字典
        """
        mql = state.get("mql")
        
        # 如果MQL无效，跳过执行
        if not mql or state.get("mql_errors"):
            self.add_step(state, "查询执行", "MQL无效，跳过执行", "error")
            return {"sql": None, "query_result": None}
        
        # 使用LLM路由器决定执行哪些Skills
        routing_decision = await self.router.decide_next_skills(
            current_state=state,
            available_skills=self.AVAILABLE_SKILLS,
            context={"phase": "execution"}
        )
        
        # 执行选择的Skills
        result = {"sql": "", "datasources": []}
        
        for skill_name in routing_decision["skills"]:
            skill = self.skill_loader.get_skill(skill_name)
            if not skill:
                continue
            
            try:
                skill_result = await skill.execute({
                    "mql": mql,
                    **result  # 传递前一个Skill的结果
                })
                
                # 合并结果
                result.update(skill_result)
                
                # 记录步骤
                self.add_step(
                    state,
                    title=skill_name.replace("_", " ").title(),
                    content="已完成",
                    status="success"
                )
            except Exception as e:
                print(f"⚠️  Skill '{skill_name}' 执行失败: {e}")
                self.add_step(
                    state,
                    skill_name.replace("_", " ").title(),
                    f"执行失败: {str(e)}",
                    "error"
                )
                result["error"] = str(e)
        
        # 注意：查询历史由前端统一保存，此处不再重复保存
        
        # 添加执行阶段完成步骤，传递 SQL 和查询结果
        self.add_step(
            state,
            "执行阶段",
            f"SQL转换和查询执行完成，返回 {result.get('query_result', {}).get('total_count', 0)} 条结果",
            "success" if not result.get("error") else "error",
            extra={
                "sql": result.get("sql"),
                "result_count": result.get('query_result', {}).get('total_count', 0)
            }
        )
        
        return {
            "sql": result.get("sql"),
            "sql_datasources": result.get("datasources", []),
            "query_result": result.get("query_result"),
            "query_id": result.get("query_id")
        }
