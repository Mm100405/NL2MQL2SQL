from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.big import LineageNode, LineageConnection, SQLAnalysis

router = APIRouter()


# ============ Pydantic Models ============

class LineageNodeCreate(BaseModel):
    node_id: str
    name: str
    node_type: str
    type: str = ""
    detail: str = ""
    fields: List[str] = []
    execution_time: str = ""
    row_count: str = ""
    upstream: List[str] = []
    downstream: List[str] = []


class LineageNodeResponse(BaseModel):
    id: int
    node_id: str
    name: str
    node_type: str
    type: str
    detail: str
    fields: List[str]
    execution_time: str
    row_count: str
    upstream: List[str]
    downstream: List[str]

    class Config:
        from_attributes = True


class LineageConnectionCreate(BaseModel):
    from_node: str
    to_node: str
    connection_type: str = ""
    color: str = "#165dff"


class LineageConnectionResponse(BaseModel):
    id: int
    from_node: str
    to_node: str
    connection_type: str
    color: str

    class Config:
        from_attributes = True


class SQLAnalysisRequest(BaseModel):
    sql: str
    depth: str = "operator"


class SQLAnalysisResponse(BaseModel):
    id: int
    sql: str
    depth: str
    result: dict

    class Config:
        from_attributes = True


# ============ Lineage Node APIs ============

@router.post("/big/lineage-nodes", response_model=LineageNodeResponse)
def create_lineage_node(node: LineageNodeCreate, db: Session = Depends(get_db)):
    """创建血缘节点"""
    db_node = LineageNode(
        node_id=node.node_id,
        name=node.name,
        node_type=node.node_type,
        type=node.type,
        detail=node.detail,
        fields=node.fields,
        execution_time=node.execution_time,
        row_count=node.row_count,
        upstream=node.upstream,
        downstream=node.downstream
    )
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return LineageNodeResponse(
        id=db_node.id,
        node_id=db_node.node_id,
        name=db_node.name,
        node_type=db_node.node_type,
        type=db_node.type or "",
        detail=db_node.detail or "",
        fields=db_node.fields or [],
        execution_time=db_node.execution_time or "",
        row_count=db_node.row_count or "",
        upstream=db_node.upstream or [],
        downstream=db_node.downstream or []
    )


@router.get("/big/lineage-nodes", response_model=List[LineageNodeResponse])
def list_lineage_nodes(db: Session = Depends(get_db)):
    """获取血缘节点列表"""
    nodes = db.query(LineageNode).all()
    return [
        LineageNodeResponse(
            id=n.id,
            node_id=n.node_id,
            name=n.name,
            node_type=n.node_type,
            type=n.type or "",
            detail=n.detail or "",
            fields=n.fields or [],
            execution_time=n.execution_time or "",
            row_count=n.row_count or "",
            upstream=n.upstream or [],
            downstream=n.downstream or []
        )
        for n in nodes
    ]


@router.get("/big/lineage-nodes/{node_id}", response_model=LineageNodeResponse)
def get_lineage_node(node_id: str, db: Session = Depends(get_db)):
    """获取血缘节点详情"""
    node = db.query(LineageNode).filter(LineageNode.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return LineageNodeResponse(
        id=node.id,
        node_id=node.node_id,
        name=node.name,
        node_type=node.node_type,
        type=node.type or "",
        detail=node.detail or "",
        fields=node.fields or [],
        execution_time=node.execution_time or "",
        row_count=node.row_count or "",
        upstream=node.upstream or [],
        downstream=node.downstream or []
    )


# ============ Lineage Connection APIs ============

@router.post("/big/lineage-connections", response_model=LineageConnectionResponse)
def create_lineage_connection(conn: LineageConnectionCreate, db: Session = Depends(get_db)):
    """创建血缘连接"""
    db_conn = LineageConnection(
        from_node=conn.from_node,
        to_node=conn.to_node,
        connection_type=conn.connection_type,
        color=conn.color
    )
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)
    return LineageConnectionResponse(
        id=db_conn.id,
        from_node=db_conn.from_node,
        to_node=db_conn.to_node,
        connection_type=db_conn.connection_type or "",
        color=db_conn.color or "#165dff"
    )


@router.get("/big/lineage-connections", response_model=List[LineageConnectionResponse])
def list_lineage_connections(db: Session = Depends(get_db)):
    """获取血缘连接列表"""
    connections = db.query(LineageConnection).all()
    return [
        LineageConnectionResponse(
            id=c.id,
            from_node=c.from_node,
            to_node=c.to_node,
            connection_type=c.connection_type or "",
            color=c.color or "#165dff"
        )
        for c in connections
    ]


# ============ SQL Analysis APIs ============

@router.post("/big/sql-analysis", response_model=SQLAnalysisResponse)
def analyze_sql(request: SQLAnalysisRequest, db: Session = Depends(get_db)):
    """分析SQL血缘"""
    # 简化实现：返回模拟结果
    result = {
        "source_tables": ["ods_orders", "ods_order_items"],
        "target_tables": ["dwd_order_wide"],
        "operators": [
            {"type": "JOIN", "detail": "ods_orders.order_id = ods_order_items.order_id"},
            {"type": "FILTER", "detail": "status = 'completed'"},
            {"type": "GROUP BY", "detail": "user_id, DATE(create_time)"},
            {"type": "AGGREGATE", "detail": "SUM(amount), COUNT(*)"}
        ],
        "fields": {
            "ods_orders": ["order_id", "user_id", "amount", "status", "create_time"],
            "ods_order_items": ["order_id", "product_id", "quantity"],
            "dwd_order_wide": ["user_id", "order_date", "total_amount", "order_count"]
        }
    }
    
    db_analysis = SQLAnalysis(
        sql=request.sql,
        depth=request.depth,
        result=result
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    
    return SQLAnalysisResponse(
        id=db_analysis.id,
        sql=db_analysis.sql,
        depth=db_analysis.depth or "operator",
        result=db_analysis.result or {}
    )


@router.get("/big/sql-analysis", response_model=List[SQLAnalysisResponse])
def list_sql_analyses(db: Session = Depends(get_db)):
    """获取SQL分析历史"""
    analyses = db.query(SQLAnalysis).order_by(SQLAnalysis.id.desc()).limit(50).all()
    return [
        SQLAnalysisResponse(
            id=a.id,
            sql=a.sql,
            depth=a.depth or "operator",
            result=a.result or {}
        )
        for a in analyses
    ]


# ============ Lineage Graph APIs ============

@router.get("/big/lineage-graph/{target}")
def get_lineage_graph(target: str, direction: str = "both", db: Session = Depends(get_db)):
    """获取血缘图谱"""
    # 返回完整的血缘图数据结构
    nodes = db.query(LineageNode).all()
    connections = db.query(LineageConnection).all()
    
    return {
        "target": target,
        "direction": direction,
        "nodes": [
            {
                "id": n.node_id,
                "name": n.name,
                "nodeType": n.node_type,
                "type": n.type or "",
                "detail": n.detail or "",
                "fields": n.fields or [],
                "executionTime": n.execution_time or "",
                "rowCount": n.row_count or "",
                "upstream": n.upstream or [],
                "downstream": n.downstream or []
            }
            for n in nodes
        ],
        "connections": [
            {
                "id": c.id,
                "from": c.from_node,
                "to": c.to_node,
                "type": c.connection_type or "",
                "color": c.color or "#165dff"
            }
            for c in connections
        ]
    }
