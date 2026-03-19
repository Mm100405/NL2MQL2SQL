# backend/app/agents/skills/markdown_parser.py

import re
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class MarkdownSkill:
    """从Markdown文件定义的Skill
    
    Markdown Skill是一种声明式的Skill定义方式，通过Markdown文件描述Skill的功能、输入输出和Prompt模板。
    适合用于LLM驱动的任务，如文本生成、分析等。
    
    Attributes:
        name: Skill名称
        description: 功能描述
        inputs: 输入参数定义列表
        outputs: 输出字段定义列表
        prompt_template: Prompt模板字符串
        implementation: 实现配置（YAML格式）
        examples: 示例列表
        metadata_file: Markdown文件路径
    
    Example:
        >>> skill = MarkdownSkill.from_file("skills/result_interpretation.md")
        >>> print(skill.name)  # "结果解释"
        >>> print(skill.description)  # "使用自然语言解释查询结果..."
    """
    
    name: str
    description: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    prompt_template: str
    implementation: Dict[str, Any]
    examples: List[Dict[str, Any]]
    metadata_file: str
    
    @classmethod
    def from_file(cls, file_path: str) -> 'MarkdownSkill':
        """从Markdown文件加载Skill
        
        解析Markdown文件，提取Skill的各个部分定义。
        
        Args:
            file_path: Markdown文件路径
        
        Returns:
            MarkdownSkill实例
        
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        
        Example:
            >>> skill = MarkdownSkill.from_file("skills/my_skill.md")
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Skill文件不存在: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析各个部分
        name = cls._extract_name(content)
        description = cls._extract_description(content)
        inputs = cls._extract_inputs(content)
        outputs = cls._extract_outputs(content)
        prompt_template = cls._extract_prompt_template(content)
        implementation = cls._extract_implementation(content)
        examples = cls._extract_examples(content)
        
        return cls(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            prompt_template=prompt_template,
            implementation=implementation,
            examples=examples,
            metadata_file=file_path
        )
    
    @staticmethod
    def _extract_name(content: str) -> str:
        """提取Skill名称
        
        从Markdown的一级标题中提取：# Skill: 名称
        """
        match = re.search(r'^#\s+Skill:\s*(.+)$', content, re.MULTILINE)
        return match.group(1).strip() if match else "unknown"
    
    @staticmethod
    def _extract_description(content: str) -> str:
        """提取功能描述
        
        从"## 描述"部分提取描述文本。
        """
        match = re.search(r'##\s+描述\s*\n(.*?)(?=##|$)', content, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    @staticmethod
    def _extract_inputs(content: str) -> List[Dict[str, Any]]:
        """提取输入参数定义
        
        从"## 输入"部分提取参数列表，格式：
        - `param_name` (type): description
        """
        match = re.search(r'##\s+输入\s*\n(.*?)(?=##|$)', content, re.DOTALL)
        if match:
            lines = match.group(1).strip().split('\n')
            inputs = []
            for line in lines:
                if line.startswith('-'):
                    # 解析格式：- `name` (type): description
                    input_match = re.match(r'-\s*`(\w+)`\s*\((\w+)\)\s*:\s*(.*)', line)
                    if input_match:
                        inputs.append({
                            "name": input_match.group(1),
                            "type": input_match.group(2),
                            "description": input_match.group(3).strip(),
                            "optional": "可选" in input_match.group(3)
                        })
            return inputs
        return []
    
    @staticmethod
    def _extract_outputs(content: str) -> List[Dict[str, Any]]:
        """提取输出字段定义
        
        从"## 输出"部分提取字段列表，格式：
        - `field_name` (type): description
        """
        match = re.search(r'##\s+输出\s*\n(.*?)(?=##|$)', content, re.DOTALL)
        if match:
            lines = match.group(1).strip().split('\n')
            outputs = []
            for line in lines:
                if line.startswith('-'):
                    output_match = re.match(r'-\s*`(\w+)`\s*\((\w+)\)\s*:\s*(.*)', line)
                    if output_match:
                        outputs.append({
                            "name": output_match.group(1),
                            "type": output_match.group(2),
                            "description": output_match.group(3).strip()
                        })
            return outputs
        return []
    
    @staticmethod
    def _extract_prompt_template(content: str) -> str:
        """提取Prompt模板
        
        从"## Prompt 模板"部分的代码块中提取。
        """
        # 尝试匹配带代码块标记的Prompt
        match = re.search(r'##\s+Prompt\s+模板\s*\n```\s*\n(.*?)\n```', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 尝试匹配不带代码块标记的Prompt
        match = re.search(r'##\s+Prompt\s+模板\s*\n(.*?)(?=##|$)', content, re.DOTALL)
        return match.group(1).strip() if match else ""
    
    @staticmethod
    def _extract_implementation(content: str) -> Dict[str, Any]:
        """提取实现逻辑配置
        
        从"## 实现逻辑"部分的YAML代码块中提取。
        """
        match = re.search(r'##\s+实现逻辑\s*\n```yaml\s*\n(.*?)\n```', content, re.DOTALL)
        if match:
            try:
                return yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                return {}
        return {}
    
    @staticmethod
    def _extract_examples(content: str) -> List[Dict[str, Any]]:
        """提取示例
        
        从Markdown中的所有JSON代码块提取示例。
        """
        examples = []
        # 查找所有JSON代码块
        code_blocks = re.findall(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
        for block in code_blocks:
            try:
                examples.append(json.loads(block))
            except json.JSONDecodeError:
                pass
        return examples
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取Skill元数据"""
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "source": "markdown",
            "file": self.metadata_file
        }
    
    def __repr__(self) -> str:
        """返回Skill的字符串表示"""
        return f"<MarkdownSkill(name='{self.name}', file='{self.metadata_file}')>"
