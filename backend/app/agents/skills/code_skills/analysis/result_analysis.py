# backend/app/agents/skills/code_skills/analysis/result_analysis.py

from typing import Dict, Any
import json
import re

from app.agents.skills.base_skill import BaseSkill


class ResultAnalysisSkill(BaseSkill):
    """结果分析Skill
    
    分析查询结果并生成洞察
    使用LLM进行智能分析
    """
    
    skill_name = "result_analysis"
    skill_type = "analysis"
    description = "分析查询结果并生成洞察"
    required_inputs = ["query_result", "natural_language"]
    optional_inputs = ["intent_type"]
    outputs = ["summary", "insights", "visualization"]
    
    def __init__(self, db=None):
        super().__init__(db)
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行结果分析"""
        query_result = inputs.get("query_result", {})
        natural_language = inputs.get("natural_language", "")
        intent_type = inputs.get("intent_type", "aggregation")
        
        if not query_result or query_result.get("error"):
            return {
                "summary": "无有效查询结果",
                "insights": [],
                "visualization": {"type": "table"}
            }
        
        # 构建分析Prompt
        prompt = self._build_analysis_prompt(query_result, natural_language, intent_type)
        
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
                config_params={"temperature": 0.3, "max_tokens": 1024}
            )
            
            # 解析结果
            summary, insights, visualization = self._parse_response(response)
            
            return {
                "summary": summary,
                "insights": insights,
                "visualization": visualization
            }
        except Exception as e:
            print(f"⚠️  结果分析失败: {e}")
            # 失败时返回简单总结
            return {
                "summary": f"查询返回 {query_result.get('total_count', 0)} 条结果",
                "insights": [f"共{query_result.get('total_count', 0)}条数据"],
                "visualization": {"type": "table"}
            }
    
    def _build_analysis_prompt(self, query_result: dict, query: str, intent_type: str) -> str:
        """构建分析Prompt"""
        columns = query_result.get("columns", [])
        data = query_result.get("data", [])[:5]  # 只取前5行
        total_count = query_result.get("total_count", 0)
        
        return f"""分析查询结果并生成洞察。

## 用户查询
{query}

## 查询意图
{intent_type}

## 查询结果

### 数据列
{', '.join(columns)}

### 数据样本（前5行）
{json.dumps(data, ensure_ascii=False, indent=2)}

### 总记录数
{total_count}

## 要求
1. 用1-2句话概括查询结果
2. 从数据中发现3-5个有价值的洞察
3. 推荐最适合的可视化类型

## 可视化类型说明
- line: 折线图，适合趋势分析
- bar: 柱状图，适合对比分析
- pie: 饼图，适合占比分析
- table: 表格，适合详细数据展示

## 输出格式

请返回JSON格式：
```json
{{
  "summary": "结果总结",
  "insights": ["洞察1", "洞察2", "洞察3"],
  "visualization": {{
    "type": "line",
    "description": "为什么选择这个可视化类型"
  }}
}}
```

请分析并返回："""
    
    def _parse_response(self, response: str) -> tuple:
        """解析LLM返回的分析结果"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                return (
                    data.get("summary", ""),
                    data.get("insights", []),
                    data.get("visualization", {"type": "table"})
                )
        except Exception as e:
            print(f"⚠️  解析失败: {e}")
        
        # 解析失败，返回默认值
        return "", [], {"type": "table"}
    
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
