from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class LineageNode(Base):
    """血缘节点模型"""
    __tablename__ = "lineage_nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String(100), nullable=False, unique=True, comment="节点ID")
    name = Column(String(200), nullable=False, comment="节点名称")
    node_type = Column(String(20), nullable=False, comment="节点类型: source/operator/target")
    type = Column(String(50), comment="算子类型")
    detail = Column(Text, comment="详情")
    fields = Column(JSON, comment="字段列表")
    execution_time = Column(String(50), comment="执行时间")
    row_count = Column(String(50), comment="行数")
    upstream = Column(JSON, comment="上游节点")
    downstream = Column(JSON, comment="下游节点")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LineageConnection(Base):
    """血缘连接模型"""
    __tablename__ = "lineage_connections"

    id = Column(Integer, primary_key=True, index=True)
    from_node = Column(String(100), nullable=False, comment="源节点ID")
    to_node = Column(String(100), nullable=False, comment="目标节点ID")
    connection_type = Column(String(50), comment="连接类型")
    color = Column(String(20), comment="连接线颜色")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SQLAnalysis(Base):
    """SQL分析记录模型"""
    __tablename__ = "sql_analyses"

    id = Column(Integer, primary_key=True, index=True)
    sql = Column(Text, nullable=False, comment="SQL语句")
    depth = Column(String(20), comment="分析深度: table/column/operator")
    result = Column(JSON, comment="分析结果")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
