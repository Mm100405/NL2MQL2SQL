from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Dataset(Base):
    """
    物理表模型 - 代表数据源中的实际表
    """
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    datasource_id = Column(String(36), ForeignKey("datasources.id"), nullable=False)
    name = Column(String(255), nullable=False)
    physical_name = Column(String(255), nullable=False)  # Actual table/view name
    schema_name = Column(String(255), nullable=True)
    columns = Column(JSON, nullable=True)  # [{name, type, nullable, comment}]
    
    # 字段元数据配置
    # 格式: {
    #   "column_name": {
    #     "value_range": {"min": 0, "max": 100},  # 数值范围
    #     "dict_id": "dictionary_uuid",           # 关联的字典ID
    #     "enum_values": ["A", "B", "C"],         # 枚举值列表
    #     "auto_enum": true                        # 是否自动生成枚举值
    #   }
    # }
    column_metadata = Column(JSON, nullable=True)
    
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "datasource_id": self.datasource_id,
            "name": self.name,
            "physical_name": self.physical_name,
            "schema_name": self.schema_name,
            "columns": self.columns or [],
            "column_metadata": self.column_metadata or {},
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_column_metadata(self, column_name: str) -> dict:
        """获取指定字段的元数据配置"""
        if not self.column_metadata:
            return {}
        return self.column_metadata.get(column_name, {})
