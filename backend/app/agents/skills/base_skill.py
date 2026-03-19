# backend/app/agents/skills/base_skill.py

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sqlalchemy.orm import Session
import logging


class BaseSkill(ABC):
    """Skill基类
    
    所有Skill（代码Skill和Markdown Skill）都需要继承此基类。
    Skill是可复用的业务逻辑单元，负责具体的执行任务。
    
    Attributes:
        skill_name: Skill的唯一标识名称
        skill_type: Skill类型（retrieval, generation, validation, execution, analysis）
        description: Skill的功能描述
        required_inputs: 必需的输入参数列表
        optional_inputs: 可选的输入参数列表
        outputs: 输出字段列表
    """
    
    skill_name: str
    skill_type: str
    description: str
    required_inputs: List[str]
    optional_inputs: List[str]
    outputs: List[str]
    
    def __init__(self, db: Session = None):
        """初始化Skill
        
        Args:
            db: 数据库会话（可选）
        """
        self.db = db
        # 设置日志记录器
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行Skill的核心逻辑
        
        这是Skill的主要入口点，子类必须实现此方法。
        
        Args:
            inputs: 输入参数字典，包含执行所需的所有参数
        
        Returns:
            执行结果字典，包含Skill的输出
        
        Example:
            >>> skill = MySkill(db)
            >>> result = await skill.execute({"query": "销售额", "context": {}})
            >>> print(result["mql"])
        """
        pass
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> tuple[bool, str]:
        """验证输入参数
        
        检查必需的输入参数是否都存在。
        
        Args:
            inputs: 输入参数字典
        
        Returns:
            (是否验证通过, 错误信息)
        
        Example:
            >>> is_valid, error_msg = skill.validate_inputs({"query": "test"})
            >>> if not is_valid:
            >>>     print(f"验证失败: {error_msg}")
        """
        for required_input in self.required_inputs:
            if required_input not in inputs:
                return False, f"缺少必需参数: {required_input}"
        return True, ""
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取Skill的元数据
        
        返回Skill的描述信息，用于LLM路由决策。
        
        Returns:
            包含Skill元数据的字典
        
        Example:
            >>> metadata = skill.get_metadata()
            >>> print(metadata["name"])  # "mql_generation"
            >>> print(metadata["description"])  # "根据自然语言生成MQL"
        """
        return {
            "name": self.skill_name,
            "type": self.skill_type,
            "description": self.description,
            "required_inputs": self.required_inputs,
            "optional_inputs": self.optional_inputs,
            "outputs": self.outputs
        }
    
    def __repr__(self) -> str:
        """返回Skill的字符串表示"""
        return f"<{self.__class__.__name__}(name='{self.skill_name}', type='{self.skill_type}')>"
