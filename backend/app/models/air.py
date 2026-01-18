from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class Workbook(Base):
    """工作簿模型"""
    __tablename__ = "workbooks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="工作簿名称")
    description = Column(Text, comment="描述")
    color = Column(String(20), default="#165DFF", comment="颜色标识")
    status = Column(String(20), default="stopped", comment="状态: active/stopped")
    owner = Column(String(100), default="admin", comment="负责人")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IntegrationTask(Base):
    """数据集成任务模型"""
    __tablename__ = "integration_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="任务名称")
    source_type = Column(String(50), nullable=False, comment="源数据类型")
    target_type = Column(String(50), nullable=False, comment="目标数据类型")
    status = Column(String(20), default="paused", comment="状态: running/paused/failed/success")
    schedule = Column(String(100), comment="调度策略")
    schedule_type = Column(String(20), comment="调度类型: cron/interval/manual")
    cron_expr = Column(String(100), comment="Cron表达式")
    interval_minutes = Column(Integer, comment="执行间隔(分钟)")
    description = Column(Text, comment="描述")
    last_run_time = Column(String(50), comment="上次执行时间")
    last_run_duration = Column(String(50), comment="执行耗时")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConsolidationRule(Base):
    """数据整合规则模型"""
    __tablename__ = "consolidation_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="规则名称")
    type = Column(String(20), nullable=False, comment="规则类型: merge/clean/transform")
    description = Column(Text, comment="描述")
    source_tables = Column(JSON, comment="源表列表")
    target_table = Column(String(200), comment="目标表")
    strategy = Column(String(50), comment="合并策略")
    condition = Column(Text, comment="条件/逻辑")
    enabled = Column(Boolean, default=True, comment="是否启用")
    exec_count = Column(Integer, default=0, comment="执行次数")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DataAcceleration(Base):
    """数据加速配置模型"""
    __tablename__ = "data_accelerations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="任务名称")
    type = Column(String(50), nullable=False, comment="加速类型: materialized_view/cube/cache")
    description = Column(Text, comment="描述")
    source_table = Column(String(200), comment="源表")
    query = Column(Text, comment="加速SQL")
    refresh_policy = Column(String(50), comment="刷新策略")
    schedule = Column(String(100), comment="刷新周期")
    enabled = Column(Boolean, default=False, comment="是否启用")
    speedup = Column(Integer, default=0, comment="加速比")
    original_latency = Column(Integer, default=0, comment="原始延迟(ms)")
    accelerated_latency = Column(Integer, default=0, comment="加速后延迟(ms)")
    next_run = Column(String(50), comment="下次执行")
    storage = Column(String(50), comment="存储占用")
    last_refresh = Column(String(50), comment="上次刷新")
    cache_size = Column(String(50), comment="缓存大小")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
