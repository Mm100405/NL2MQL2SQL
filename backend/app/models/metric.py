from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, Enum
from datetime import datetime
import uuid
import enum

from app.database import Base


class MetricType(str, enum.Enum):
    basic = "basic"        # 基础指标（原子指标）
    derived = "derived"    # 派生指标
    composite = "composite"  # 复合指标


class AggregationType(str, enum.Enum):
    SUM = "SUM"
    COUNT = "COUNT"
    AVG = "AVG"
    MAX = "MAX"
    MIN = "MIN"
    COUNT_DISTINCT = "COUNT_DISTINCT"


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=True)
    metric_type = Column(String(20), nullable=False, default=MetricType.basic.value)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)
    aggregation = Column(String(20), nullable=True)  # SUM, COUNT, AVG, etc.
    measure_column = Column(String(255), nullable=True)  # Physical column for basic metrics
    calculation_formula = Column(Text, nullable=True)  # MQL formula for derived/composite
    filters = Column(JSON, nullable=True)  # Default filters [{field, operator, value}]
    synonyms = Column(JSON, nullable=True)  # Alternative names for NL recognition
    unit = Column(String(50), nullable=True)  # e.g., "元", "个", "%"
    format = Column(String(50), nullable=True)  # Display format
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "metric_type": self.metric_type,
            "dataset_id": self.dataset_id,
            "aggregation": self.aggregation,
            "measure_column": self.measure_column,
            "calculation_formula": self.calculation_formula,
            "filters": self.filters or [],
            "synonyms": self.synonyms or [],
            "unit": self.unit,
            "format": self.format,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
