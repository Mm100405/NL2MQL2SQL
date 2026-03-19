# backend/app/agents/routers/llm_router.py

from typing import Dict, Any, List, Optional
import json
import re
from sqlalchemy.orm import Session

from app.services.llm_client import call_llm
from app.agents.skills.skill_loader import SkillLoader


class LLMRouter:
    """LLM智能路由器
    
    使用LLM根据当前状态和路由规则动态决策下一步执行哪些Skills。
    """
    
    def __init__(self, skill_loader: SkillLoader, db: Session = None):
        """初始化LLM路由器"""
        self.skill_loader = skill_loader
        self.db = db
    
    async def decide_next_skills(
        self,
        current_state: Dict[str, Any],
        available_skills: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """决定下一步执行哪些Skill
        
        Args:
            current_state: 当前状态字典
            available_skills: 可用的Skill名称列表
            context: 上下文信息（如当前阶段、意图类型等）
        
        Returns:
            决策结果字典，包含skills、reasoning、is_complete字段
        """
        # 1. 获取所有Skill的描述
        skill_descriptions = self._get_skill_descriptions(available_skills)
        
        # 2. 构建路由Prompt
        prompt = self._build_routing_prompt(current_state, skill_descriptions, context)
        
        # 3. 调用LLM
        model_config = self._get_model_config()
        
        try:
            response = await call_llm(
                prompt=prompt,
                provider=model_config["provider"],
                model_name=model_config["model_name"],
                api_key=model_config["api_key"],
                api_base=model_config["api_base"],
                config_params={"temperature": 0.1, "max_tokens": 1024}
            )
        except Exception as e:
            print(f"⚠️  LLM调用失败: {e}")
            return {
                "skills": available_skills[:1],
                "reasoning": f"LLM调用失败，使用默认决策: {str(e)}",
                "is_complete": False
            }
        
        # 4. 解析路由决策
        decision = self._parse_routing_decision(response, available_skills)
        
        return decision
    
    def _get_skill_descriptions(self, skill_names: List[str]) -> Dict[str, str]:
        """获取Skill描述"""
        descriptions = {}
        for name in skill_names:
            skill = self.skill_loader.get_skill(name)
            if skill:
                if hasattr(skill, 'description'):
                    descriptions[name] = skill.description
                elif hasattr(skill, 'skill'):
                    descriptions[name] = skill.skill.description
                else:
                    descriptions[name] = "无描述"
            else:
                descriptions[name] = "未找到"
        return descriptions
    
    def _build_routing_prompt(
        self,
        state: Dict[str, Any],
        skill_descriptions: Dict[str, str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建路由Prompt"""
        steps = state.get("steps", [])
        last_steps = steps[-3:] if steps else []
        phase = context.get("phase", "unknown") if context else "unknown"
        intent_type = context.get("intent_type") if context else None
        
        prompt = f"""你是一个智能路由助手，负责决定下一步执行哪些Skill。

## 当前状态

### 用户查询
{state.get('natural_language', '未知')}

### 当前阶段
{phase}

### 已执行的步骤
{self._format_steps(last_steps)}

### 当前MQL
{self._format_mql(state.get('mql'))}

### 错误信息
{state.get('mql_errors', '无') if state.get('mql_errors') else '无'}

### 重试次数
{state.get('retry_count', 0)}/{state.get('max_retries', 3)}
"""
        
        if intent_type:
            prompt += f"\n### 意图类型\n{intent_type}\n"
        
        prompt += f"""
## 可用的Skill
{self._format_skills(skill_descriptions)}

## 路由规则

根据当前阶段和状态，按照以下规则决策：

1. **准备阶段**（phase=preparation）：
   - 必须执行：metadata_retrieval
   - 可选执行：intent_analysis

2. **生成阶段**（phase=generation）：
   - 必须执行：mql_generation, mql_validation
   - 如果MQL验证失败，执行：mql_correction
   - 如果已达到最大重试次数，标记is_complete=true

3. **执行阶段**（phase=execution）：
   - 必须执行：sql_translation, query_execution

4. **解释阶段**（phase=interpretation）：
   - 根据意图类型选择相应的分析Skill

## 决策输出

请返回JSON格式的决策：

```json
{{
  "skills": ["skill1", "skill2"],
  "reasoning": "决策原因",
  "is_complete": false
}}
```

现在请做出决策："""

        return prompt
    
    def _format_steps(self, steps: List[Dict]) -> str:
        """格式化步骤列表"""
        if not steps:
            return "（无）"
        return "\n".join([f"- {s.get('title', '未知')}: {s.get('content', '')} ({s.get('status', 'unknown')})" for s in steps])
    
    def _format_skills(self, skill_descriptions: Dict[str, str]) -> str:
        """格式化Skill列表"""
        return "\n".join([f"- **{name}**: {desc}" for name, desc in skill_descriptions.items()])
    
    def _format_mql(self, mql: Optional[Dict[str, Any]]) -> str:
        """格式化MQL对象"""
        if not mql:
            return "未生成"
        try:
            return json.dumps(mql, ensure_ascii=False, indent=2)
        except:
            return str(mql)
    
    def _parse_routing_decision(
        self,
        response: str,
        available_skills: List[str]
    ) -> Dict[str, Any]:
        """解析LLM返回的路由决策"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                
                skills = decision.get("skills", [])
                if not isinstance(skills, list):
                    skills = [skills] if skills else []
                
                valid_skills = [s for s in skills if s in available_skills]
                
                if len(valid_skills) != len(skills):
                    print(f"⚠️  过滤不可用的Skill: {set(skills) - set(valid_skills)}")
                
                return {
                    "skills": valid_skills if valid_skills else available_skills[:1],
                    "reasoning": decision.get("reasoning", "无"),
                    "is_complete": decision.get("is_complete", False)
                }
        except Exception as e:
            print(f"⚠️  解析路由决策失败: {e}")
        
        return {
            "skills": available_skills[:1],
            "reasoning": "解析失败，使用默认决策",
            "is_complete": False
        }
    
    def _get_model_config(self) -> Dict[str, Any]:
        """获取模型配置"""
        if not self.db:
            return {"provider": "openai", "model_name": "gpt-3.5-turbo", "api_key": None, "api_base": None}
        
        from app.models.model_config import ModelConfig
        from app.utils.encryption import decrypt_api_key
        
        try:
            model_config = self.db.query(ModelConfig).filter(
                ModelConfig.is_default == True,
                ModelConfig.is_active == True
            ).first()
            
            if model_config:
                return {
                    "provider": model_config.provider,
                    "model_name": model_config.model_name,
                    "api_key": decrypt_api_key(model_config.api_key) if model_config.api_key else None,
                    "api_base": model_config.api_base
                }
        except Exception as e:
            print(f"⚠️  获取模型配置失败: {e}")
        
        return {"provider": "openai", "model_name": "gpt-3.5-turbo", "api_key": None, "api_base": None}
