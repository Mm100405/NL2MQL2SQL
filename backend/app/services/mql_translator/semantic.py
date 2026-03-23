"""
semantic.py - 语义上下文层

从数据库加载元数据（Metric, Dimension, View, Dataset, DataSource），
提供统一的字段查找接口，供 expression_parser 和 ast_builder 使用。
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.dataset import Dataset
from app.models.view import View
from app.models.datasource import DataSource


@dataclass
class FieldRef:
    """字段引用"""
    physical_column: str          # 物理列名
    display_name: str             # 展示名称
    name: str                     # 逻辑名称
    data_type: str                # 数据类型: string/number/date/datetime
    dimension_type: str           # 维度类型: normal/time/geo/categorical/numerical
    source_view_id: Optional[str] = None  # 所属视图ID
    format_config: Optional[Dict] = None  # 格式配置


@dataclass
class MetricRef:
    """指标引用"""
    name: str                     # 逻辑名称
    display_name: str              # 展示名称
    metric_type: str               # basic/derived/composite
    aggregation: Optional[str]    # SUM/COUNT/AVG/MAX/MIN/COUNT_DISTINCT
    calculation_method: str        # field/expression
    measure_column: Optional[str]  # 物理列名（basic类型）
    calculation_formula: Optional[str]  # 公式（derived/composite类型）
    derivation_type: str           # none/yoy/mom/yoy_growth/mom_growth
    base_metric_id: Optional[str] = None  # 基础指标ID（派生类型）
    source_view_id: Optional[str] = None   # 所属视图ID
    filters: Optional[List[Dict]] = None   # 默认过滤条件


@dataclass
class ViewRef:
    """视图引用"""
    id: str
    name: str
    display_name: str
    view_type: str                 # single_table/joined/sql
    datasource_id: str
    base_table_id: Optional[str] = None
    join_config: Optional[Dict] = None
    custom_sql: Optional[str] = None
    columns: List[Dict] = field(default_factory=list)  # [{name, source_table, source_column, alias, type}]


@dataclass
class DatasetRef:
    """数据集引用"""
    id: str
    name: str
    physical_name: str
    schema_name: Optional[str] = None
    datasource_id: Optional[str] = None
    columns: List[Dict] = field(default_factory=list)


@dataclass
class TimeFormatConfig:
    """时间格式配置"""
    suffix_to_format: Dict[str, str] = field(default_factory=dict)   # day -> YYYY-MM-DD
    label_to_format: Dict[str, str] = field(default_factory=dict)    # 按月 -> YYYY-MM
    default_formats: Dict[str, str] = field(default_factory=lambda: {
        "day": "YYYY-MM-DD",
        "month": "YYYY-MM",
        "year": "YYYY",
        "week": "YYYY-WW",
    })
    default_labels: Dict[str, str] = field(default_factory=lambda: {
        "按日": "YYYY-MM-DD",
        "按月": "YYYY-MM",
        "按年": "YYYY",
        "按周": "YYYY-WW",
    })


class SemanticContext:
    """
    语义上下文 - 加载和缓存所有元数据，提供统一查询接口

    使用方法：
        context = SemanticContext(db)
        context.load()
        field = context.resolve_field("日期__按月")
        metric = context.resolve_metric("销售额")
    """

    def __init__(self, db: Session):
        self.db = db

        # 元数据缓存
        self._metrics: Dict[str, MetricRef] = {}
        self._dimensions: Dict[str, FieldRef] = {}
        self._views: Dict[str, ViewRef] = {}
        self._datasets: Dict[str, DatasetRef] = {}
        self._datasources: Dict[str, DataSource] = {}
        self._time_formats: TimeFormatConfig = TimeFormatConfig()

        # 反向索引（用于 display_name -> name 查找）
        self._display_name_to_metric: Dict[str, str] = {}
        self._display_name_to_dimension: Dict[str, str] = {}

        self._loaded = False

    def load(self) -> "SemanticContext":
        """从数据库加载所有元数据"""
        if self._loaded:
            return self

        # 加载指标
        for m in self.db.query(Metric).all():
            ref = MetricRef(
                name=m.name,
                display_name=m.display_name or m.name,
                metric_type=m.metric_type,
                aggregation=m.aggregation,
                calculation_method=m.calculation_method or "field",
                measure_column=m.measure_column,
                calculation_formula=m.calculation_formula,
                derivation_type=m.derivation_type or "none",
                base_metric_id=m.base_metric_id,
                source_view_id=m.view_id,
                filters=m.filters,
            )
            self._metrics[m.name] = ref
            self._display_name_to_metric[ref.display_name] = m.name

        # 加载维度
        for d in self.db.query(Dimension).all():
            ref = FieldRef(
                physical_column=d.physical_column,
                display_name=d.display_name or d.name,
                name=d.name,
                data_type=d.data_type or "string",
                dimension_type=d.dimension_type or "normal",
                source_view_id=d.view_id,
                format_config=d.format_config,
            )
            self._dimensions[d.name] = ref
            self._display_name_to_dimension[ref.display_name] = d.name

        # 加载视图
        for v in self.db.query(View).all():
            ref = ViewRef(
                id=v.id,
                name=v.name,
                display_name=v.display_name or v.name,
                view_type=v.view_type,
                datasource_id=v.datasource_id,
                base_table_id=v.base_table_id,
                join_config=v.join_config,
                custom_sql=v.custom_sql,
                columns=v.columns or [],
            )
            self._views[v.id] = ref

        # 加载数据集
        for d in self.db.query(Dataset).all():
            ref = DatasetRef(
                id=d.id,
                name=d.name,
                physical_name=d.physical_name,
                schema_name=d.schema_name,
                datasource_id=d.datasource_id,
                columns=d.columns or [],
            )
            self._datasets[d.id] = ref

        # 加载数据源
        for ds in self.db.query(DataSource).all():
            self._datasources[ds.id] = ds

        # 加载时间格式配置
        from app.models.settings import SystemSetting
        tf_setting = self.db.query(SystemSetting).filter(SystemSetting.key == "time_formats").first()
        if tf_setting and tf_setting.value:
            for f in tf_setting.value:
                suffix = f.get("suffix")
                name = f.get("name")
                label = f.get("label")
                if suffix and name:
                    self._time_formats.suffix_to_format[suffix] = name
                if label and name:
                    self._time_formats.label_to_format[label] = name
        else:
            # 使用默认配置
            self._time_formats.suffix_to_format = self._time_formats.default_formats.copy()
            self._time_formats.label_to_format = self._time_formats.default_labels.copy()

        self._loaded = True
        return self

    def resolve_field(self, field_name: str) -> Optional[FieldRef]:
        """
        解析字段引用 - 三级查找：display_name -> name -> physical_column

        Args:
            field_name: 字段名，可能带后缀（如 "日期__按月"）

        Returns:
            FieldRef 或 None
        """
        # 解析后缀（如 date__year -> date, year）
        actual_name = field_name
        suffix = None
        if "__" in field_name:
            actual_name, suffix = field_name.split("__", 1)

        # 1. 优先按 display_name 查找
        lookup_name = self._display_name_to_dimension.get(actual_name)
        if lookup_name:
            ref = self._dimensions.get(lookup_name)
        else:
            # 2. 按 name 查找
            ref = self._dimensions.get(actual_name)

        # 3. 按 physical_column 查找
        if not ref:
            for dim in self._dimensions.values():
                if dim.physical_column == actual_name:
                    ref = dim
                    break

        # 如果找到且有后缀，需要更新 ref 的 format_config
        if ref and suffix:
            # 优先从 label_to_format 匹配（针对 "按月" 等）
            if suffix in self._time_formats.label_to_format:
                fmt = self._time_formats.label_to_format[suffix]
                ref.format_config = {"default_format": fmt, "source": "label"}
            # 次选从 suffix_to_format 匹配（针对 "year" 等）
            elif suffix in self._time_formats.suffix_to_format:
                fmt = self._time_formats.suffix_to_format[suffix]
                ref.format_config = {"default_format": fmt, "source": "suffix"}

        return ref

    def resolve_metric(self, metric_name: str) -> Optional[MetricRef]:
        """
        解析指标引用 - 三级查找：display_name -> name -> measure_column

        Args:
            metric_name: 指标名

        Returns:
            MetricRef 或 None
        """
        # 1. 按 display_name 查找
        lookup_name = self._display_name_to_metric.get(metric_name)
        if lookup_name:
            return self._metrics.get(lookup_name)

        # 2. 按 name 查找
        ref = self._metrics.get(metric_name)
        if ref:
            return ref

        # 3. 按 measure_column 查找
        for m in self._metrics.values():
            if m.measure_column == metric_name:
                return m

        return None

    def resolve_view(self, view_id: str) -> Optional[ViewRef]:
        """根据视图ID获取视图引用"""
        return self._views.get(view_id)

    def resolve_dataset(self, dataset_id: str) -> Optional[DatasetRef]:
        """根据数据集ID获取数据集引用"""
        return self._datasets.get(dataset_id)

    def get_view_column_expression(self, view_id: str, column_name: str) -> str:
        """
        获取视图列的 SQL 表达式（处理 JOIN 视图的表别名前缀）

        对于不同视图类型：
        - single_table: 直接返回列名
        - joined: 返回 table_alias.column_name 格式
        - sql: 直接返回列名
        """
        view = self._views.get(view_id)
        if not view:
            return column_name

        if view.view_type == "single_table":
            return column_name

        if view.view_type == "joined":
            if view.columns:
                for col in view.columns:
                    if col.get("name") == column_name or col.get("alias") == column_name:
                        source_table = col.get("source_table")
                        source_column = col.get("source_column", column_name)
                        if source_table:
                            return f"{source_table}.{source_column}"
            return column_name

        if view.view_type == "sql":
            return column_name

        return column_name

    def get_used_view(self, mql: Dict[str, Any]) -> Tuple[Optional[ViewRef], Optional[str]]:
        """
        确定 MQL 使用的视图和数据源

        Returns:
            (view_ref, datasource_id) 或 (None, None)
        """
        metric_defs = mql.get("metricDefinitions", {})

        # 从指标定义中查找视图
        for alias, defn in metric_defs.items():
            ref_metric_name = defn.get("refMetric")
            if not ref_metric_name:
                continue

            metric_ref = self.resolve_metric(ref_metric_name)
            if not metric_ref:
                continue

            # 优先从 view_id 查找
            if metric_ref.source_view_id:
                view = self.resolve_view(metric_ref.source_view_id)
                if view:
                    return view, view.datasource_id

            # 从 dataset_id 查找
            # 需要遍历 datasets 找到关联的
            for ds in self._datasets.values():
                if ds.datasource_id:
                    # 通过指标反查 dataset
                    for m in self._metrics.values():
                        if m.source_view_id is None and hasattr(m, 'dataset_id'):
                            # 需要从 DB 对象获取 dataset_id
                            pass

        # 如果没找到，尝试从维度找
        for dim_name in mql.get("dimensions", []):
            actual_name = dim_name.split("__")[0] if "__" in dim_name else dim_name
            dim_ref = self.resolve_field(actual_name)
            if dim_ref and dim_ref.source_view_id:
                view = self.resolve_view(dim_ref.source_view_id)
                if view:
                    return view, view.datasource_id

        # 默认返回第一个视图
        if self._views:
            first_view = list(self._views.values())[0]
            return first_view, first_view.datasource_id

        return None, None

    def get_dialect(self, datasource_id: Optional[str]) -> str:
        """获取 SQL 方言"""
        if datasource_id and datasource_id in self._datasources:
            ds = self._datasources[datasource_id]
            return ds.type or "mysql"
        return "mysql"

    def get_datasource(self, datasource_id: str) -> Optional[DataSource]:
        """获取数据源对象"""
        return self._datasources.get(datasource_id)

    def get_time_format_for_field(self, field_name: str) -> Optional[str]:
        """
        获取字段对应的时间格式（如果有后缀的话）

        例如：
            "日期__按月" -> "YYYY-MM"
            "date__month" -> "YYYY-MM"
        """
        if "__" not in field_name:
            return None

        _, suffix = field_name.split("__", 1)

        # 先从 label_to_format 匹配
        if suffix in self._time_formats.label_to_format:
            return self._time_formats.label_to_format[suffix]

        # 再从 suffix_to_format 匹配
        if suffix in self._time_formats.suffix_to_format:
            return self._time_formats.suffix_to_format[suffix]

        return None

    @property
    def metrics(self) -> Dict[str, MetricRef]:
        return self._metrics

    @property
    def dimensions(self) -> Dict[str, FieldRef]:
        return self._dimensions

    @property
    def views(self) -> Dict[str, ViewRef]:
        return self._views

    @property
    def datasets(self) -> Dict[str, DatasetRef]:
        return self._datasets

    @property
    def datasources(self) -> Dict[str, DataSource]:
        return self._datasources
