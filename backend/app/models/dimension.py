from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from datetime import datetime
import uuid
import enum

from app.database import Base


class DimensionType(str, enum.Enum):
    normal = "normal"      # 普通维度
    time = "time"          # 时间维度
    geo = "geo"            # 地理维度
    categorical = "categorical" # 分类维度
    numerical = "numerical"     # 数值维度
    user_defined = "user_defined" # 用户自定义维度


class Dimension(Base):
    """
    维度模型 - 可关联到视图(View)或数据集(Dataset)
    """
    __tablename__ = "dimensions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 关联视图（新增，优先使用）
    view_id = Column(String(36), ForeignKey("views.id"), nullable=True)
    # 关联数据集（保留兼容）
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    physical_column = Column(String(255), nullable=False)
    data_type = Column(String(20), nullable=False, default="string")  # string, number, date, datetime
    dimension_type = Column(String(20), nullable=False, default=DimensionType.normal.value)
    hierarchy = Column(JSON, nullable=True)  # {levels: ["year", "month", "day"]}
    format_config = Column(JSON, nullable=True) # {default_format: "YYYY-MM", options: ["YYYY-MM-DD", "YYYY-MM"]}
    
    # 字段值配置（新增）
    # 格式: {
    #   "range": {"min": 0, "max": 100},  # 数值范围
    #   "dict_id": "dictionary_uuid",     # 关联的字典ID
    #   "auto_enum": true                  # 是否自动生成枚举值
    # }
    value_config = Column(JSON, nullable=True)
    
    synonyms = Column(JSON, nullable=True)  # Alternative names
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "view_id": self.view_id,
            "dataset_id": self.dataset_id,
            "name": self.name,
            "display_name": self.display_name,
            "physical_column": self.physical_column,
            "data_type": self.data_type,
            "dimension_type": self.dimension_type,
            "hierarchy": self.hierarchy,
            "format_config": self.format_config,
            "value_config": self.value_config,
            "synonyms": self.synonyms or [],
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
