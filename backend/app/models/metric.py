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


class CalculationMethod(str, enum.Enum):
    field = "field"
    expression = "expression"


class DerivationType(str, enum.Enum):
    none = "none"
    yoy = "yoy"
    mom = "mom"
    yoy_growth = "yoy_growth"
    mom_growth = "mom_growth"


class Metric(Base):
    """
    指标模型 - 支持基础指标、派生指标、复合指标
    可关联到视图(View)或数据集(Dataset)
    """
    __tablename__ = "metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=True)
    metric_type = Column(String(20), nullable=False, default=MetricType.basic.value)
    
    # 关联视图（新增，优先使用）
    view_id = Column(String(36), ForeignKey("views.id"), nullable=True)
    # 关联数据集（保留兼容）
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)
    aggregation = Column(String(20), nullable=True)  # SUM, COUNT, AVG, etc.
    calculation_method = Column(String(20), nullable=True, default=CalculationMethod.field.value)
    measure_column = Column(String(255), nullable=True)  # Physical column for basic metrics
    calculation_formula = Column(Text, nullable=True)  # MQL formula for derived/composite
    is_semi_additive = Column(JSON, nullable=True) # JSON to store semi-additive settings
    date_column_id = Column(String(36), nullable=True) # ⚠️ DEPRECATED: 使用 View.default_date_column_id 代替
    base_metric_id = Column(String(36), ForeignKey("metrics.id"), nullable=True)
    derivation_type = Column(String(20), nullable=True, default=DerivationType.none.value)
    time_constraint = Column(Text, nullable=True)  # ⚠️ DEPRECATED: 使用 filters 代替
    analysis_dimensions = Column(JSON, nullable=True)  # List of dimension IDs
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
            "view_id": self.view_id,
            "dataset_id": self.dataset_id,
            "aggregation": self.aggregation,
            "calculation_method": self.calculation_method,
            "measure_column": self.measure_column,
            "calculation_formula": self.calculation_formula,
            "is_semi_additive": self.is_semi_additive,
            "date_column_id": self.date_column_id,
            "base_metric_id": self.base_metric_id,
            "derivation_type": self.derivation_type,
            "time_constraint": self.time_constraint,
            "analysis_dimensions": self.analysis_dimensions or [],
            "filters": self.filters or [],
            "synonyms": self.synonyms or [],
            "unit": self.unit,
            "format": self.format,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
