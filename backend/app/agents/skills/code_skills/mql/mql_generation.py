"""
MQL生成Skill - 根据查询意图和元数据生成MQL查询
复用 app.services.nl_parser.parse_natural_language 服务
"""

from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.agents.skills.base_skill import BaseSkill


class MQLGenerationSkill(BaseSkill):
    """MQL生成Skill - 根据查询意图和元数据生成MQL查询"""

    skill_name: str = "mql_generation"
    skill_type: str = "generation"
    description: str = "根据查询意图和元数据生成MQL查询"
    required_inputs: List[str] = ["natural_language"]
    optional_inputs: List[str] = ["context", "intent", "metadata"]
    outputs: List[str] = ["mql", "steps", "confidence", "interpretation"]

    def __init__(self, db: Session = None):
        super().__init__(db)

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行MQL生成 - 调用实际的parse_natural_language服务"""
        natural_language = inputs.get("natural_language", "")
        context = inputs.get("context", {})

        if not natural_language:
            return {
                "success": False,
                "mql": None,
                "message": "查询内容为空"
            }

        # 获取模型配置
        model_config = self._get_model_config()
        if not model_config["api_key"]:
            return {
                "success": False,
                "mql": None,
                "message": "未配置模型API Key"
            }

        try:
            # 调用实际的MQL生成服务
            from app.services.nl_parser import parse_natural_language

            result = await parse_natural_language(
                natural_language=natural_language,
                provider=model_config["provider"],
                model_name=model_config["model_name"],
                api_key=model_config["api_key"],
                api_base=model_config["api_base"],
                config_params=model_config.get("config_params"),
                db=self.db,
                context=context
            )

            return {
                "success": True,
                "mql": result.get("mql"),
                "steps": result.get("steps", []),
                "confidence": result.get("confidence", 0.0),
                "interpretation": result.get("interpretation", ""),
                "message": "MQL生成成功"
            }

        except Exception as e:
            print(f"MQL生成失败: {e}")
            return {
                "success": False,
                "mql": None,
                "message": f"MQL生成失败: {str(e)}"
            }

    def _get_model_config(self) -> dict:
        """获取模型配置"""
        if not self.db:
            return {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "api_key": None,
                "api_base": None,
                "config_params": None
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
                    "api_base": model_config.api_base,
                    "config_params": model_config.config_params
                }
        except Exception as e:
            print(f"获取模型配置失败: {e}")

        return {
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "api_key": None,
            "api_base": None,
            "config_params": None
        }
