"""
base.py - MQL 校验器基类和公共接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session


class Severity(str, Enum):
    """校验错误级别"""
    ERROR = "ERROR"      # 必须修正
    WARNING = "WARNING"  # 容忍，可选修正


@dataclass
class ValidationError:
    """校验错误"""
    code: str            # 错误码，如 "FILTER_METRIC_IN_WHERE"
    message: str         # 错误消息
    severity: Severity    # 错误级别
    field: str           # 出错字段
    value: Any = None    # 错误值
    suggestion: str = ""  # 修正建议

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "field": self.field,
            "value": self.value,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def add_error(self, error: ValidationError):
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: ValidationError):
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult"):
        """合并另一个校验结果"""
        for error in other.errors:
            self.add_error(error)
        for warning in other.warnings:
            self.add_warning(warning)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
        }

    @property
    def all_errors(self) -> List[ValidationError]:
        """所有错误（包括 WARNING 视为 ERROR）"""
        return self.errors + [w for w in self.warnings if w.severity == Severity.ERROR]


class ValidationContext:
    """
    校验上下文 - 包含校验所需的元数据

    在 Node 1 (Preparation) 阶段构建，传递给各校验器使用
    """

    def __init__(self, db: Session):
        self.db = db
        # 指标集合
        self.metric_names: Set[str] = set()
        self.metric_display_names: Set[str] = set()
        # 指标定义映射
        self.metric_definitions: Dict[str, Dict[str, Any]] = {}
        # 维度集合
        self.dimension_names: Set[str] = set()
        self.dimension_display_names: Set[str] = set()
        # 维度定义映射
        self.dimension_definitions: Dict[str, Dict[str, Any]] = {}
        # 时间维度
        self.time_dimensions: Set[str] = set()
        # 所有可用字段名（指标 + 维度 + 可过滤字段）
        self.all_field_names: Set[str] = set()
        # 可过滤字段集合（从 View 中加载，用于 filters 校验）
        self.filterable_fields: Set[str] = set()
        # 指标字段（只能在 having，不能在 filters）
        self.metric_fields: Set[str] = set()
        # 维度字段（只能在 filters）
        self.dimension_fields: Set[str] = set()
        # 时间格式映射
        self.time_formats: Dict[str, str] = {}
        # 加载元数据
        self._load_metadata()

    def _load_metadata(self):
        """从数据库加载元数据"""
        from app.models.metric import Metric
        from app.models.dimension import Dimension
        from app.models.view import View

        # 加载指标
        for m in self.db.query(Metric).all():
            self.metric_names.add(m.name)
            if m.display_name:
                self.metric_display_names.add(m.display_name)
                self.all_field_names.add(m.display_name)
            self.all_field_names.add(m.name)
            self.metric_fields.add(m.name)
            self.metric_definitions[m.name] = {
                "name": m.name,
                "display_name": m.display_name,
                "metric_type": m.metric_type,
                "aggregation": m.aggregation,
                "measure_column": m.measure_column,
                "view_id": m.view_id,
            }

        # 加载维度
        for d in self.db.query(Dimension).all():
            self.dimension_names.add(d.name)
            if d.display_name:
                self.dimension_display_names.add(d.display_name)
                self.all_field_names.add(d.display_name)
            self.all_field_names.add(d.name)
            self.dimension_fields.add(d.name)
            self.dimension_definitions[d.name] = {
                "name": d.name,
                "display_name": d.display_name,
                "physical_column": d.physical_column,
                "dimension_type": d.dimension_type,
                "data_type": d.data_type,
                "format_config": d.format_config,
            }
            if d.dimension_type == "time":
                self.time_dimensions.add(d.name)

        # 加载可过滤字段（从 View 中）
        for view in self.db.query(View).all():
            columns = view.columns or []
            for col in columns:
                # 检查字段是否可过滤
                if col.get("filterable", True):
                    display_name = col.get("display_name") or col.get("name")
                    field_name = col.get("name")
                    if display_name:
                        self.filterable_fields.add(display_name)
                        self.all_field_names.add(display_name)
                    if field_name:
                        self.filterable_fields.add(field_name)
                        self.all_field_names.add(field_name)

        # 合并指标和维度到 all_field_names
        self.all_field_names = self.metric_names | self.metric_display_names | self.dimension_names | self.dimension_display_names | self.filterable_fields

    def is_metric(self, field_name: str) -> bool:
        """判断字段是否为指标"""
        return field_name in self.metric_names or field_name in self.metric_display_names

    def is_dimension(self, field_name: str) -> bool:
        """判断字段是否为维度"""
        return field_name in self.dimension_names or field_name in self.dimension_display_names

    def get_metric_name(self, field_name: str) -> Optional[str]:
        """获取指标的逻辑名称"""
        if field_name in self.metric_definitions:
            return field_name
        for name, defn in self.metric_definitions.items():
            if defn.get("display_name") == field_name:
                return name
        return None


class BaseMQLValidator(ABC):
    """
    MQL 校验器基类

    每个校验器负责验证 MQL 的一个字段。
    """

    # 校验的字段名
    field_name: str = ""

    # 错误码前缀
    error_code_prefix: str = ""

    def __init__(self, db: Session):
        self.db = db
        self.context: Optional[ValidationContext] = None

    def set_context(self, context: ValidationContext):
        """设置校验上下文"""
        self.context = context
        return self

    @abstractmethod
    def validate(self, value: Any, mql: Dict[str, Any]) -> ValidationResult:
        """
        校验逻辑

        Args:
            value: 字段值
            mql: 完整 MQL（用于交叉校验）

        Returns:
            ValidationResult
        """
        pass

    def error(
        self,
        code: str,
        message: str,
        field: str,
        value: Any = None,
        suggestion: str = "",
    ) -> ValidationError:
        """创建 ERROR 级别错误"""
        return ValidationError(
            code=f"{self.error_code_prefix}{code}",
            message=message,
            severity=Severity.ERROR,
            field=field,
            value=value,
            suggestion=suggestion,
        )

    def warning(
        self,
        code: str,
        message: str,
        field: str,
        value: Any = None,
        suggestion: str = "",
    ) -> ValidationError:
        """创建 WARNING 级别错误"""
        return ValidationError(
            code=f"{self.error_code_prefix}{code}",
            message=message,
            severity=Severity.WARNING,
            field=field,
            value=value,
            suggestion=suggestion,
        )

    def extract_field_refs(self, expr: str) -> List[str]:
        """
        从表达式中提取字段引用

        匹配 [字段名] 格式
        """
        import re
        refs = re.findall(r"\[([^\]]+)\]", expr)
        return refs

    def extract_field_refs_from_structured(self, condition: Any) -> List[str]:
        """从结构化 filter 条件中提取所有字段名

        Args:
            condition: 结构化条件节点（叶子条件或分组条件）

        Returns:
            所有叶子条件中的 field 名称列表
        """
        if not isinstance(condition, dict):
            return []
        if "field" in condition:
            return [condition["field"]]
        fields = []
        for sub in condition.get("conditions", []):
            fields.extend(self.extract_field_refs_from_structured(sub))
        return fields
