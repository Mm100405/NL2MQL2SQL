"""Field Dictionary Model - For field value mapping and enumeration"""
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from datetime import datetime
import uuid

from app.database import Base


class DictSourceType:
    MANUAL = "manual"      # 手动配置
    VIEW_REF = "view_ref"  # 引用视图
    AUTO = "auto"          # 自动生成


class FieldDictionary(Base):
    """
    字段字典模型 - 用于存储字段值映射关系
    支持三种来源类型：
    1. manual: 手动配置的静态映射
    2. view_ref: 引用其他视图的字段值
    3. auto: 从表字段自动生成的去重值列表
    """
    __tablename__ = "field_dictionaries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=True)
    
    # 字典来源类型
    source_type = Column(String(20), nullable=False, default=DictSourceType.MANUAL)
    
    # 手动配置的映射列表
    # 格式: [{
    #   "value": "A",           # 实际值
    #   "label": "选项A",       # 显示标签
    #   "synonyms": ["甲", "选项甲"]  # 同义词列表，用于自然语言匹配
    # }]
    mappings = Column(JSON, nullable=True)
    
    # 引用视图配置（source_type = view_ref 时使用）
    ref_view_id = Column(String(36), ForeignKey("views.id"), nullable=True)
    ref_value_column = Column(String(255), nullable=True)  # 值字段
    ref_label_column = Column(String(255), nullable=True)  # 标签字段
    
    # 自动生成配置（source_type = auto 时使用）
    auto_source_dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)
    auto_source_column = Column(String(255), nullable=True)
    auto_filters = Column(JSON, nullable=True)  # 自动生成时的过滤条件
    auto_last_sync = Column(DateTime, nullable=True)  # 上次同步时间
    
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "source_type": self.source_type,
            "mappings": self.mappings or [],
            "ref_view_id": self.ref_view_id,
            "ref_value_column": self.ref_value_column,
            "ref_label_column": self.ref_label_column,
            "auto_source_dataset_id": self.auto_source_dataset_id,
            "auto_source_column": self.auto_source_column,
            "auto_filters": self.auto_filters or [],
            "auto_last_sync": self.auto_last_sync.isoformat() if self.auto_last_sync else None,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def get_value_from_label(self, label: str) -> str:
        """
        根据标签或同义词获取实际值
        用于自然语言解析时的值匹配
        """
        if not self.mappings:
            return label
            
        label_lower = label.lower()
        for mapping in self.mappings:
            # 匹配标签
            if mapping.get("label", "").lower() == label_lower:
                return mapping.get("value", label)
            # 匹配同义词
            synonyms = mapping.get("synonyms", [])
            for syn in synonyms:
                if syn.lower() == label_lower:
                    return mapping.get("value", label)
        
        return label

    def get_label_from_value(self, value: str) -> str:
        """
        根据实际值获取显示标签
        """
        if not self.mappings:
            return value
            
        for mapping in self.mappings:
            if mapping.get("value") == value:
                return mapping.get("label", value)
        
        return value
