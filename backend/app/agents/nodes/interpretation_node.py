# backend/app/agents/nodes/interpretation_node.py

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.agents.skills.skill_loader import SkillLoader
from app.agents.routers.llm_router import LLMRouter


class InterpretationNode(BaseNode):
    """解释节点 - 根据意图类型动态选择分析Skill
    
    职责：
    1. 根据意图类型选择分析策略
    2. 执行分析Skills
    3. 生成洞察和可视化建议
    
    可用Skills：
    - trend_analysis: 趋势分析
    - comparison_analysis: 对比分析
    - result_analysis: 结果分析
    - result_interpretation: 结果解释（Markdown Skill）
    """
    
    node_name = "interpretation"
    description = "分析查询结果并生成洞察"
    
    AVAILABLE_SKILLS = [
        "trend_analysis",
        "comparison_analysis",
        "result_analysis",
        "result_interpretation"
    ]
    
    def __init__(self, db: Session = None, step_callback=None):
        """初始化解释节点"""
        super().__init__(db, step_callback=step_callback)
        self.skill_loader = SkillLoader(db)
        self.router = LLMRouter(self.skill_loader, db)
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """执行解释节点
        
        流程：
        1. 检查查询结果是否有效
        2. LLM路由决策（根据意图类型）
        3. 执行分析Skills
        4. 生成洞察和可视化建议
        
        Args:
            state: 当前查询状态
            config: 配置信息
        
        Returns:
            更新的状态字段字典
        """
        query_result = state.get("query_result")
        intent_type = state.get("intent_type", "aggregation")
        
        # 如果没有查询结果，跳过
        if not query_result or query_result.get("error"):
            self.add_step(state, "结果分析", "无有效查询结果", "warning")
            return {
                "interpretation": None,
                "insights": [],
                "visualization_suggestion": None
            }
        
        # 使用LLM路由器决定执行哪些Skills
        routing_decision = await self.router.decide_next_skills(
            current_state={
                **state,
                "intent_type": intent_type,
                "query_result": query_result
            },
            available_skills=self.AVAILABLE_SKILLS,
            context={
                "phase": "interpretation",
                "intent_type": intent_type
            }
        )
        
        # 执行选择的Skills
        result = {}
        
        for skill_name in routing_decision["skills"]:
            skill = self.skill_loader.get_skill(skill_name)
            if not skill:
                continue
            
            try:
                skill_result = await skill.execute({
                    "query_result": query_result,
                    "natural_language": state["natural_language"],
                    "intent_type": intent_type,
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
        
        # 添加解释阶段完成步骤，传递洞察信息
        summary = result.get("summary", "")
        insights = result.get("insights", [])
        insights_count = len(insights)

        self.add_step(
            state,
            "解释阶段",
            f"结果分析完成，生成 {insights_count} 条洞察",
            "success",
            extra={
                "summary": summary,
                "insights": insights
            }
        )
        
        return {
            "interpretation": {
                "summary": summary,
                "insights": result.get("insights", [])
            },
            "insights": result.get("insights", []),
            "visualization_suggestion": result.get("visualization", {})
        }
