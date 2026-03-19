# backend/app/agents/skills/code_skills/mql/mql_correction.py

from typing import Dict, Any
import json
import re

from app.agents.skills.base_skill import BaseSkill


class MQLCorrectionSkill(BaseSkill):
    """MQL修正Skill
    
    根据验证错误信息智能修正MQL
    """
    
    skill_name = "mql_correction"
    skill_type = "validation"
    description = "根据验证错误智能修正MQL"
    required_inputs = ["mql", "errors", "metadata"]
    optional_inputs = ["natural_language"]
    outputs = ["mql", "corrections"]
    
    def __init__(self, db=None):
        super().__init__(db)
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行MQL修正"""
        mql = inputs.get("mql", {})
        errors = inputs.get("errors", [])
        metadata = inputs.get("metadata", {})
        natural_language = inputs.get("natural_language", "")
        
        # 如果没有错误，直接返回
        if not errors:
            return {
                "mql": mql,
                "corrections": []
            }
        
        # 构建修正Prompt
        prompt = self._build_correction_prompt(mql, errors, metadata, natural_language)
        
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
                config_params={"temperature": 0.2, "max_tokens": 2048}
            )
            
            # 解析修正后的MQL
            corrected_mql, corrections = self._parse_response(response)
            
            return {
                "mql": corrected_mql or mql,
                "corrections": corrections
            }
        except Exception as e:
            print(f"⚠️  MQL修正失败: {e}")
            # 失败时返回原始MQL
            return {
                "mql": mql,
                "corrections": [],
                "errors": [f"修正失败: {str(e)}"]
            }
    
    def _build_correction_prompt(self, mql: dict, errors: list, metadata: dict, query: str) -> str:
        """构建修正Prompt"""
        metrics = metadata.get("metrics", [])[:10]
        dimensions = metadata.get("dimensions", [])[:10]
        
        metrics_str = "\n".join([f"- {m['display_name']} | {m['name']}" for m in metrics])
        dimensions_str = "\n".join([f"- {d['display_name']} | {d['name']}" for d in dimensions])
        
        return f"""修正以下MQL错误。

## 原始查询
{query}

## 错误的MQL
```json
{json.dumps(mql, ensure_ascii=False, indent=2)}
```

## 错误信息
{chr(10).join([f"- {err}" for err in errors])}

## 可用指标
{metrics_str}

## 可用维度
{dimensions_str}

## 要求
1. 根据错误信息修正MQL
2. 只使用上面列出的可用指标和维度
3. 保持MQL的原始意图
4. 返回修正后的完整MQL

请返回JSON格式：
```json
{{
  "mql": {{ ... 修正后的MQL ... }},
  "corrections": ["修正说明1", "修正说明2"]
}}
```
"""
    
    def _parse_response(self, response: str) -> tuple:
        """解析LLM返回的修正结果"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("mql", {}), data.get("corrections", [])
        except Exception as e:
            print(f"⚠️  解析失败: {e}")
        
        return {}, []
    
    def _get_model_config(self) -> dict:
        """获取模型配置"""
        if not self.db:
            return {"provider": "openai", "model_name": "gpt-3.5-turbo", "api_key": None, "api_base": None}
        
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
        
        return {"provider": "openai", "model_name": "gpt-3.5-turbo", "api_key": None, "api_base": None}
