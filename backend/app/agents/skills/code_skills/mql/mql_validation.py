# backend/app/agents/skills/code_skills/mql/mql_validation.py

from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.agents.skills.base_skill import BaseSkill


class MQLValidationSkill(BaseSkill):
    """MQL验证Skill

    验证MQL的合规性和正确性
    复用 app.utils.mql_validator.MQLValidator 服务
    """

    skill_name = "mql_validation"
    skill_type = "validation"
    description = "验证MQL的合规性和正确性"
    required_inputs = ["mql"]
    optional_inputs = []
    outputs = ["is_valid", "errors", "warnings"]

    def __init__(self, db: Session = None):
        super().__init__(db)

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行MQL验证 - 调用实际的MQLValidator服务"""
        mql = inputs.get("mql", {})

        if not mql:
            return {
                "is_valid": False,
                "errors": ["MQL为空"],
                "warnings": []
            }

        if not self.db:
            return {
                "is_valid": False,
                "errors": ["无数据库会话，无法验证"],
                "warnings": []
            }

        try:
            # 调用实际的MQL验证服务
            from app.utils.mql_validator import MQLValidator

            validator = MQLValidator(self.db)
            is_valid, error_msg = validator.validate_mql(mql)

            if is_valid:
                return {
                    "is_valid": True,
                    "errors": [],
                    "warnings": []
                }
            else:
                return {
                    "is_valid": False,
                    "errors": [error_msg],
                    "warnings": []
                }

        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"验证过程出错: {str(e)}"],
                "warnings": []
            }
