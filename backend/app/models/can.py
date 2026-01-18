from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class MetricCatalog(Base):
    """指标目录模型"""
    __tablename__ = "metric_catalogs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="指标名称")
    code = Column(String(100), nullable=False, unique=True, comment="指标编码")
    type = Column(String(20), nullable=False, comment="指标类型: basic/derived/composite")
    status = Column(String(20), default="draft", comment="状态: published/draft/deprecated")
    category = Column(String(200), comment="所属分类")
    description = Column(Text, comment="描述")
    formula = Column(Text, comment="计算逻辑")
    owner = Column(String(100), default="admin", comment="负责人")
    tags = Column(JSON, comment="标签")
    dimensions = Column(JSON, comment="关联维度")
    query_count = Column(Integer, default=0, comment="查询次数")
    application_count = Column(Integer, default=0, comment="应用数量")
    dependency_count = Column(Integer, default=0, comment="依赖指标数")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MetricApplication(Base):
    """指标应用模型"""
    __tablename__ = "metric_applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="应用名称")
    type = Column(String(20), nullable=False, comment="应用类型: dashboard/report/api")
    description = Column(Text, comment="描述")
    metrics = Column(JSON, comment="包含的指标列表")
    owner = Column(String(100), default="admin", comment="负责人")
    view_count = Column(Integer, default=0, comment="查看次数")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MetricAcceleration(Base):
    """指标加速配置模型"""
    __tablename__ = "metric_accelerations"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(200), nullable=False, comment="指标名称")
    metric_code = Column(String(100), nullable=False, comment="指标编码")
    dimensions = Column(JSON, comment="预聚合维度")
    granularity = Column(String(20), comment="时间粒度")
    refresh_policy = Column(String(50), comment="刷新策略")
    enabled = Column(Boolean, default=False, comment="是否启用")
    hit_rate = Column(Integer, default=0, comment="命中率(%)")
    original_latency = Column(Integer, default=0, comment="原始延迟(ms)")
    accelerated_latency = Column(Integer, default=0, comment="加速后延迟(ms)")
    last_refresh = Column(String(50), comment="上次刷新")
    cache_size = Column(String(50), comment="缓存大小")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SystemRole(Base):
    """系统角色模型"""
    __tablename__ = "system_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, comment="角色名称")
    description = Column(Text, comment="角色描述")
    permissions = Column(JSON, comment="权限列表")
    is_system = Column(Boolean, default=False, comment="是否系统角色")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(String(50), comment="操作时间")
    user = Column(String(100), comment="操作用户")
    action = Column(String(50), comment="操作类型")
    target = Column(String(200), comment="操作对象")
    details = Column(Text, comment="操作详情")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
