# backend/app/agents/skills/code_skills/sql/sql_translation.py

from typing import Dict, Any
from sqlalchemy.orm import Session

from app.agents.skills.base_skill import BaseSkill


class SQLTranslationSkill(BaseSkill):
    """SQL转换Skill
    
    将MQL转换为可执行的SQL语句
    复用现有的mql_engine服务
    """
    
    skill_name = "sql_translation"
    skill_type = "execution"
    description = "将MQL转换为可执行的SQL"
    required_inputs = ["mql"]
    optional_inputs = []
    outputs = ["sql", "datasources", "lineage"]
    
    def __init__(self, db: Session = None):
        super().__init__(db)
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL转换"""
        mql = inputs.get("mql", {})
        
        if not mql:
            return {
                "sql": "",
                "datasources": [],
                "lineage": {},
                "errors": ["MQL为空"]
            }
        
        try:
            # 复用现有的mql_to_sql服务
            from app.services.mql_engine import mql_to_sql
            
            result = await mql_to_sql(mql, self.db)
            
            return {
                "sql": result.get("sql", ""),
                "datasources": result.get("datasources", []),
                "lineage": result.get("lineage", {})
            }
        except Exception as e:
            print(f"⚠️  SQL转换失败: {e}")
            return {
                "sql": "",
                "datasources": [],
                "lineage": {},
                "errors": [f"转换失败: {str(e)}"]
            }
