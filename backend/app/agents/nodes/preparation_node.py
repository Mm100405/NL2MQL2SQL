# backend/app/agents/nodes/preparation_node.py

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.agents.skills.skill_loader import SkillLoader
from app.agents.routers.llm_router import LLMRouter


class PreparationNode(BaseNode):
    """准备节点 - 动态选择并执行准备阶段的Skill
    
    职责：
    1. 检索元数据（指标、维度、可过滤字段）
    2. 分析用户查询意图
    3. 丰富上下文信息
    
    可用Skills：
    - metadata_retrieval: 检索元数据
    - intent_analysis: 分析意图
    """
    
    node_name = "preparation"
    description = "准备查询所需的元数据和上下文"
    
    AVAILABLE_SKILLS = [
        "metadata_retrieval",
        "intent_analysis"
    ]
    
    def __init__(self, db: Session = None, step_callback=None):
        """初始化准备节点"""
        super().__init__(db, step_callback=step_callback)
        self.skill_loader = SkillLoader(db)
        self.router = LLMRouter(self.skill_loader, db)
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """执行准备节点
        
        流程：
        1. 使用LLM路由器决定执行哪些Skills
        2. 依次执行选择的Skills
        3. 合并结果并记录步骤
        
        Args:
            state: 当前查询状态
            config: 配置信息
        
        Returns:
            更新的状态字段字典
        """
        natural_language = state["natural_language"]
        
        # 使用LLM路由器决定执行哪些Skills
        routing_decision = await self.router.decide_next_skills(
            current_state=state,
            available_skills=self.AVAILABLE_SKILLS,
            context={"phase": "preparation"}
        )
        
        # 执行选择的Skills
        result = {}
        for skill_name in routing_decision["skills"]:
            skill = self.skill_loader.get_skill(skill_name)
            if not skill:
                print(f"⚠️  Skill '{skill_name}' 未找到")
                continue
            
            try:
                # 执行Skill
                skill_result = await skill.execute({
                    "natural_language": natural_language,
                    "context": state.get("context", {}),
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
                    title=skill_name.replace("_", " ").title(),
                    content=f"执行失败: {str(e)}",
                    status="error"
                )
        
        # 添加准备阶段完成步骤
        self.add_step(state, "准备阶段", "元数据和意图分析完成", "success")
        
        return result
