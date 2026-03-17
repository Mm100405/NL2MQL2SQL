"""DataFormatConfig Model - 数据格式配置模型"""
from sqlalchemy import Column, String, Text, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class DataFormatConfig(Base):
    """数据格式配置模型 - 用于存储用户配置的输出格式和转换规则"""
    __tablename__ = "data_format_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 用户ID
    user_id = Column(String(36), nullable=True)

    # 配置名称
    name = Column(String(255), nullable=False)

    # 自然语言查询
    natural_language = Column(Text, nullable=True)

    # 目标格式JSON示例
    target_format_example = Column(JSON, nullable=True)

    # API所需参数列表（用"、"分隔的字符串，存储到后端后转为JSON数组）
    api_parameters_str = Column(Text, nullable=True)

    # 生成的API信息
    generated_api = Column(JSON, nullable=True)

    # 转换脚本
    transform_script = Column(Text, nullable=True)

    # 参数映射配置
    parameter_mappings = Column(JSON, nullable=True)

    # MQL模板
    mql_template = Column(JSON, nullable=True)

    # 配置状态: draft | validated | deployed | failed
    status = Column(String(20), nullable=False, default="draft")

    # 错误信息
    error_message = Column(Text, nullable=True)

    # 关联的视图ID（在参数筛选时确定）
    view_id = Column(String(36), ForeignKey("views.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "natural_language": self.natural_language,
            "target_format_example": self.target_format_example,
            "api_parameters": self._parse_api_parameters(),
            "generated_api": self.generated_api,
            "transform_script": self.transform_script,
            "parameter_mappings": self.parameter_mappings,
            "mql_template": self.mql_template,
            "status": self.status,
            "error_message": self.error_message,
            "view_id": self.view_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def _parse_api_parameters(self):
        """解析API参数字符串为列表"""
        if not self.api_parameters_str:
            return []
        return [p.strip() for p in self.api_parameters_str.split("、") if p.strip()]
