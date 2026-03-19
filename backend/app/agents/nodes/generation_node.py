# backend/app/agents/nodes/generation_node.py

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig

from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.agents.skills.skill_loader import SkillLoader
from app.agents.routers.llm_router import LLMRouter


class GenerationNode(BaseNode):
    """生成节点 - 动态选择并执行生成阶段的Skill（支持重试）
    
    职责：
    1. 生成MQL
    2. 验证MQL
    3. 修正MQL（如果验证失败）
    
    可用Skills：
    - mql_generation: 生成MQL
    - mql_validation: 验证MQL
    - mql_correction: 修正MQL
    """
    
    node_name = "generation"
    description = "生成并验证MQL（最多重试3次）"
    
    AVAILABLE_SKILLS = [
        "mql_generation",
        "mql_validation",
        "mql_correction"
    ]
    
    def __init__(self, db: Session = None, step_callback=None):
        """初始化生成节点"""
        super().__init__(db, step_callback=step_callback)
        self.skill_loader = SkillLoader(db)
        self.router = LLMRouter(self.skill_loader, db)
        self.max_retries = 3
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """执行生成节点（支持重试）
        
        流程：
        1. 最多重试3次
        2. 每次尝试：LLM路由决策 → 执行Skills → 检查验证结果
        3. 如果验证通过，退出循环
        4. 如果达到最大重试次数，返回最后的结果
        
        Args:
            state: 当前查询状态
            config: 配置信息
        
        Returns:
            更新的状态字段字典
        """
        mql = None
        errors = []
        attempt = 0
        max_retries = state.get("max_retries", self.max_retries)
        
        # 最多重试max_retries次
        while attempt < max_retries:
            attempt += 1
            
            # 使用LLM路由器决定执行哪些Skills
            routing_decision = await self.router.decide_next_skills(
                current_state={
                    **state,
                    "attempt": attempt,
                    "mql": mql,
                    "mql_errors": errors
                },
                available_skills=self.AVAILABLE_SKILLS,
                context={"phase": "generation", "attempt": attempt}
            )
            
            # 执行选择的Skills
            for skill_name in routing_decision["skills"]:
                skill = self.skill_loader.get_skill(skill_name)
                if not skill:
                    continue
                
                try:
                    # 构建skill输入参数
                    skill_inputs = {
                        "natural_language": state["natural_language"],
                        "metadata": state.get("metadata", {}),
                        "context": state.get("context", {}),
                    }

                    # mql_validation 需要 mql 参数
                    if skill_name == "mql_validation":
                        skill_inputs["mql"] = mql
                    # mql_generation 需要 natural_language
                    elif skill_name == "mql_generation":
                        skill_inputs["natural_language"] = state["natural_language"]
                    # mql_correction 需要 mql, errors, metadata
                    elif skill_name == "mql_correction":
                        skill_inputs["mql"] = mql
                        skill_inputs["errors"] = errors
                        skill_inputs["metadata"] = state.get("metadata", {})

                    skill_result = await skill.execute(skill_inputs)
                    
                    # 更新MQL
                    if "mql" in skill_result:
                        mql = skill_result["mql"]
                    
                    # 检查是否验证通过
                    if skill_name == "mql_validation":
                        is_valid = skill_result.get("is_valid", False)
                        validation_errors = skill_result.get("errors", [])
                        
                        if is_valid:
                            # 验证通过，传递 MQL 信息
                            self.add_step(
                                state,
                                f"MQL生成（第{attempt}次尝试）",
                                "验证通过",
                                "success",
                                extra={"mql": mql}
                            )
                            return {
                                "mql": mql,
                                "mql_attempts": attempt,
                                "mql_errors": []
                            }
                        else:
                            # 验证失败
                            errors = validation_errors
                            self.add_step(
                                state,
                                f"MQL验证（第{attempt}次尝试）",
                                f"验证失败: {', '.join(errors)}",
                                "warning"
                            )
                    
                    # 记录错误
                    if "errors" in skill_result and skill_name != "mql_validation":
                        errors = skill_result["errors"]
                
                except Exception as e:
                    print(f"⚠️  Skill '{skill_name}' 执行失败: {e}")
                    self.add_step(
                        state,
                        skill_name.replace("_", " ").title(),
                        f"执行失败: {str(e)}",
                        "error"
                    )
            
            # 如果路由决策表示完成，退出
            if routing_decision.get("is_complete", False):
                break
        
        # 重试失败
        self.add_step(
            state,
            f"MQL生成（第{attempt}次尝试）",
            f"失败，错误: {', '.join(errors) if errors else '未知错误'}",
            "error"
        )
        
        return {
            "mql": mql,
            "mql_attempts": attempt,
            "mql_errors": errors,
            "retry_count": attempt
        }
