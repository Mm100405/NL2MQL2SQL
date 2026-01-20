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
    __tablename__ = "dimensions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    physical_column = Column(String(255), nullable=False)
    data_type = Column(String(20), nullable=False, default="string")  # string, number, date, datetime
    dimension_type = Column(String(20), nullable=False, default=DimensionType.normal.value)
    hierarchy = Column(JSON, nullable=True)  # {levels: ["year", "month", "day"]}
    format_config = Column(JSON, nullable=True) # {default_format: "YYYY-MM", options: ["YYYY-MM-DD", "YYYY-MM"]}
    synonyms = Column(JSON, nullable=True)  # Alternative names
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "name": self.name,
            "display_name": self.display_name,
            "physical_column": self.physical_column,
            "data_type": self.data_type,
            "dimension_type": self.dimension_type,
            "hierarchy": self.hierarchy,
            "format_config": self.format_config,
            "synonyms": self.synonyms or [],
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
