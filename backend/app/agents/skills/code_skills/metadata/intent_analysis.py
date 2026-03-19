# backend/app/agents/skills/code_skills/metadata/intent_analysis.py

from typing import Dict, Any
import json
import re

from app.agents.skills.base_skill import BaseSkill


class IntentAnalysisSkill(BaseSkill):
    """意图分析Skill
    
    使用LLM分析用户查询的意图，包括：
    - 意图类型（trend、comparison、drilldown、attribution、aggregation）
    - 查询复杂度（low、medium、high）
    - 建议的指标和维度
    """
    
    skill_name = "intent_analysis"
    skill_type = "analysis"
    description = "分析用户查询意图和复杂度"
    required_inputs = ["natural_language", "metadata"]
    optional_inputs = ["context"]
    outputs = ["intent", "intent_type", "complexity"]
    
    def __init__(self, db=None):
        super().__init__(db)
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行意图分析"""
        natural_language = inputs.get("natural_language", "")
        metadata = inputs.get("metadata", {})
        context = inputs.get("context", {})
        
        # 构建Prompt
        prompt = self._build_prompt(natural_language, metadata)
        
        # 调用LLM
        model_config = self._get_model_config()
        
        try:
            from app.services.llm_client import call_llm
            
            response = await call_llm(
                prompt=prompt,
                provider=model_config["provider"],
                model_name=model_config["model_name"],
                api_key=model_config["api_key"],
                api_base=model_config["api_base"],
                config_params={"temperature": 0.2, "max_tokens": 512}
            )
            
            # 解析意图
            intent = self._parse_intent(response)
            
            return {
                "intent": intent,
                "intent_type": intent.get("intent_type"),
                "complexity": intent.get("complexity")
            }
        except Exception as e:
            print(f"⚠️  意图分析失败: {e}")
            return {
                "intent": {},
                "intent_type": "aggregation",
                "complexity": "low"
            }
    
    def _build_prompt(self, query: str, metadata: dict) -> str:
        """构建意图分析Prompt"""
        metrics = metadata.get("metrics", [])[:10]
        dimensions = metadata.get("dimensions", [])[:10]
        
        metrics_str = ", ".join([m.get("display_name", "") for m in metrics])
        dimensions_str = ", ".join([d.get("display_name", "") for d in dimensions])
        
        return f"""分析用户查询意图并返回JSON：

用户查询：{query}

可用指标：{metrics_str}
可用维度：{dimensions_str}

意图类型说明：
- trend: 趋势分析（如"销售额变化趋势"）
- comparison: 对比分析（如"本月vs上月"）
- drilldown: 下钻分析（如"查看某个省份的详细数据"）
- attribution: 归因分析（如"为什么销售额下降"）
- aggregation: 聚合统计（如"总销售额"）

复杂度说明：
- low: 单一指标、单一维度、简单过滤
- medium: 多指标或多维度、复杂过滤
- high: 多指标多维度、复杂逻辑、需要计算

返回格式：
{{
  "intent_type": "trend|comparison|drilldown|attribution|aggregation",
  "description": "意图描述",
  "suggested_metrics": ["指标1", "指标2"],
  "suggested_dimensions": ["维度1", "维度2"],
  "complexity": "low|medium|high"
}}

请返回JSON格式的意图分析结果："""
    
    def _parse_intent(self, response: str) -> dict:
        """解析LLM返回的意图"""
        try:
            # 提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"⚠️  解析意图失败: {e}")
        
        # 返回默认值
        return {
            "intent_type": "aggregation",
            "description": "聚合查询",
            "suggested_metrics": [],
            "suggested_dimensions": [],
            "complexity": "low"
        }
    
    def _get_model_config(self) -> dict:
        """获取模型配置"""
        if not self.db:
            return {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "api_key": None,
                "api_base": None
            }
        
        try:
            from app.models.model_config import ModelConfig
            from app.utils.encryption import decrypt_api_key
            
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
        
        return {
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "api_key": None,
            "api_base": None
        }
