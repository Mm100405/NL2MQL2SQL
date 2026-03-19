# backend/app/agents/skills/skill_loader.py

from pathlib import Path
from typing import Dict, Optional, Union, List
from sqlalchemy.orm import Session
import importlib
import inspect

from app.agents.skills.base_skill import BaseSkill
from app.agents.skills.markdown_parser import MarkdownSkill
from app.agents.skills.markdown_executor import MarkdownSkillExecutor


class SkillLoader:
    """混合Skill加载器
    
    负责加载和管理两类Skill：
    1. 代码Skill（Python类，继承自BaseSkill）
    2. Markdown Skill（.md文件定义的Skill）
    
    加载位置：
    - 代码Skill：agents/skills/code_skills/ 目录
    - Markdown Skill（系统）：agents/skills/markdown_skills/ 目录
    - Markdown Skill（用户）：.codebuddy/skills/ 目录
    
    Attributes:
        db: 数据库会话
        _code_skills: 代码Skill缓存
        _markdown_skills: Markdown Skill缓存
    """
    
    def __init__(self, db: Session = None):
        """初始化Skill加载器"""
        self.db = db
        self._code_skills: Dict[str, BaseSkill] = {}
        self._markdown_skills: Dict[str, MarkdownSkill] = {}
        
        # 加载所有Skill
        self._load_code_skills()
        self._load_markdown_skills()
    
    def _load_code_skills(self):
        """加载代码Skill"""
        code_skills_dir = Path(__file__).parent / "code_skills"
        
        if not code_skills_dir.exists():
            return
        
        for skill_file in code_skills_dir.rglob("*.py"):
            if skill_file.name.startswith("_"):
                continue
            
            try:
                relative_path = skill_file.relative_to(code_skills_dir.parent)
                module_path = str(relative_path).replace("/", ".").replace("\\", ".").replace(".py", "")
                module_name = f"app.agents.skills.{module_path}"
                
                module = importlib.import_module(module_name)
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        inspect.isclass(attr) and
                        issubclass(attr, BaseSkill) and
                        attr != BaseSkill and
                        hasattr(attr, 'skill_name')
                    ):
                        skill_instance = attr(db=self.db)
                        self._code_skills[skill_instance.skill_name] = skill_instance
                        print(f"[OK] 已加载代码Skill: {skill_instance.skill_name}")
            except Exception as e:
                print(f"[WARN] 加载代码Skill失败 {skill_file}: {e}")
    
    def _load_markdown_skills(self):
        """加载Markdown Skill"""
        system_md_dir = Path(__file__).parent / "markdown_skills"
        user_md_dir = Path.cwd() / ".codebuddy" / "skills"
        
        for source, md_dir in [("系统", system_md_dir), ("用户", user_md_dir)]:
            if not md_dir.exists():
                continue
            
            for md_file in md_dir.glob("**/*.md"):
                if md_file.name.startswith("_"):
                    continue
                
                try:
                    skill = MarkdownSkill.from_file(str(md_file))
                    self._markdown_skills[skill.name] = skill
                    print(f"[OK] 已加载Markdown Skill ({source}): {skill.name}")
                except Exception as e:
                    print(f"[WARN] 加载Markdown Skill失败 {md_file}: {e}")
    
    def get_skill(self, skill_name: str) -> Optional[Union[BaseSkill, MarkdownSkillExecutor]]:
        """获取Skill实例"""
        if skill_name in self._code_skills:
            return self._code_skills[skill_name]
        
        if skill_name in self._markdown_skills:
            skill = self._markdown_skills[skill_name]
            return MarkdownSkillExecutor(skill, self.db)
        
        return None
    
    def list_skills(self) -> Dict[str, Dict]:
        """列出所有Skill"""
        skills = {}
        
        for name, skill in self._code_skills.items():
            skills[name] = {
                "name": skill.skill_name,
                "type": skill.skill_type,
                "description": skill.description,
                "source": "code"
            }
        
        for name, skill in self._markdown_skills.items():
            skills[name] = {
                "name": skill.name,
                "description": skill.description,
                "source": "markdown"
            }
        
        return skills
    
    def load_code_skills(self) -> Dict[str, BaseSkill]:
        """获取已加载的代码Skills"""
        return self._code_skills
    
    def load_markdown_skills(self) -> Dict[str, MarkdownSkill]:
        """获取已加载的Markdown Skills"""
        return self._markdown_skills
    
    def get_skills_by_type(self, skill_type: str) -> List[str]:
        """根据类型获取Skill名称"""
        return [
            name for name, skill in self._code_skills.items()
            if skill.skill_type == skill_type
        ]
    
    def reload_markdown_skills(self):
        """重新加载Markdown Skill（热更新）"""
        self._markdown_skills.clear()
        self._load_markdown_skills()
    
    def reload_all(self):
        """重新加载所有Skill"""
        self._code_skills.clear()
        self._markdown_skills.clear()
        self._load_code_skills()
        self._load_markdown_skills()
