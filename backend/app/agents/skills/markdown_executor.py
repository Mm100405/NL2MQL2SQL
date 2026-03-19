# backend/app/agents/skills/markdown_executor.py

import json
import re
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.agents.skills.markdown_parser import MarkdownSkill
from app.services.llm_client import call_llm


class MarkdownSkillExecutor:
    """Markdown Skill执行器
    
    负责执行Markdown定义的Skill。主要流程：
    1. 验证输入参数
    2. 渲染Prompt模板（替换变量）
    3. 调用LLM
    4. 解析输出结果
    
    Attributes:
        skill: MarkdownSkill实例
        db: 数据库会话（可选）
    
    Example:
        >>> from app.agents.skills.markdown_parser import MarkdownSkill
        >>> from app.agents.skills.markdown_executor import MarkdownSkillExecutor
        >>> 
        >>> skill = MarkdownSkill.from_file("skills/result_interpretation.md")
        >>> executor = MarkdownSkillExecutor(skill, db)
        >>> result = await executor.execute({
        ...     "query_result": {...},
        ...     "natural_language": "查询销售额"
        ... })
    """
    
    def __init__(self, skill: MarkdownSkill, db: Session = None):
        """初始化Markdown Skill执行器
        
        Args:
            skill: MarkdownSkill实例
            db: 数据库会话（可选）
        """
        self.skill = skill
        self.db = db
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行Markdown Skill
        
        执行流程：
        1. 验证输入参数
        2. 渲染Prompt模板
        3. 获取模型配置
        4. 调用LLM
        5. 解析输出
        
        Args:
            inputs: 输入参数字典
        
        Returns:
            执行结果字典
        
        Raises:
            ValueError: 输入参数验证失败
            Exception: LLM调用失败
        """
        # 1. 验证输入
        self._validate_inputs(inputs)
        
        # 2. 渲染Prompt模板
        prompt = self._render_prompt(inputs)
        
        # 3. 获取实现配置
        implementation = self.skill.implementation
        model_config_dict = implementation.get("model", {})
        
        # 4. 获取模型配置
        model_config = self._get_model_config()
        
        # 5. 调用LLM
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params=model_config_dict
        )
        
        # 6. 解析输出
        output = self._parse_output(response)
        
        return output
    
    def _validate_inputs(self, inputs: Dict[str, Any]):
        """验证输入参数
        
        检查所有必需的输入参数是否存在。
        
        Args:
            inputs: 输入参数字典
        
        Raises:
            ValueError: 缺少必需参数
        """
        for input_def in self.skill.inputs:
            name = input_def["name"]
            is_optional = input_def.get("optional", False)
            
            if not is_optional and name not in inputs:
                raise ValueError(f"缺少必需参数: {name}")
    
    def _render_prompt(self, inputs: Dict[str, Any]) -> str:
        """渲染Prompt模板
        
        将输入参数替换到Prompt模板中的占位符。
        支持简单的字符串替换，格式为 {variable_name}。
        
        Args:
            inputs: 输入参数字典
        
        Returns:
            渲染后的Prompt字符串
        
        Example:
            >>> template = "用户查询：{natural_language}\\n结果：{query_result}"
            >>> inputs = {"natural_language": "销售额", "query_result": {...}}
            >>> prompt = self._render_prompt(inputs)
            >>> # prompt = "用户查询：销售额\\n结果：{...}"
        """
        template = self.skill.prompt_template
        
        # 简单的字符串替换
        for key, value in inputs.items():
            placeholder = f"{{{key}}}"
            
            # 如果值是字典或列表，转换为JSON字符串
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, ensure_ascii=False, indent=2)
            else:
                value_str = str(value)
            
            template = template.replace(placeholder, value_str)
        
        return template
    
    def _get_model_config(self) -> Dict[str, Any]:
        """获取模型配置
        
        从数据库查询默认的模型配置。
        
        Returns:
            模型配置字典，包含provider、model_name、api_key、api_base等字段
        
        Note:
            如果数据库中没有配置，返回空配置（可能导致调用失败）
        """
        if not self.db:
            return {
                "provider": "openai",
                "model_name": "gpt-3.5-turbo",
                "api_key": None,
                "api_base": None
            }
        
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
        
        return {
            "provider": "openai",
            "model_name": "gpt-3.5-turbo",
            "api_key": None,
            "api_base": None
        }
    
    def _parse_output(self, response: str) -> Dict[str, Any]:
        """解析LLM输出
        
        尝试从响应中提取JSON格式的输出。
        支持以下格式：
        1. 直接的JSON字符串
        2. 包含在```json```代码块中的JSON
        
        Args:
            response: LLM的原始响应字符串
        
        Returns:
            解析后的结果字典，如果解析失败则返回原始响应
        
        Example:
            >>> response = '```json\\n{"summary": "测试"}\\n```'
            >>> output = self._parse_output(response)
            >>> # output = {"summary": "测试"}
        """
        try:
            # 尝试提取JSON代码块
            json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # 尝试提取任何JSON对象
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # 如果都不是，返回原始响应
            return {"result": response}
        except json.JSONDecodeError as e:
            # JSON解析失败，返回原始响应
            print(f"⚠️  JSON解析失败: {e}")
            return {"result": response}
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取Skill元数据"""
        return self.skill.get_metadata()
    
    def __repr__(self) -> str:
        """返回执行器的字符串表示"""
        return f"<MarkdownSkillExecutor(skill='{self.skill.name}')>"
