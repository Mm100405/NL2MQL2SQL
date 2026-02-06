"""View Management API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.view import View, ViewType
from app.models.dataset import Dataset
from app.models.datasource import DataSource
from app.services.query_executor import execute_query

router = APIRouter()


# ============ Schemas ============
class JoinCondition(BaseModel):
    left_column: str
    right_column: str
    operator: str = "="


class JoinConfig(BaseModel):
    left_table: str
    right_table: str
    join_type: str = "INNER"
    conditions: List[JoinCondition]


class TableConfig(BaseModel):
    id: str
    alias: str
    position: Optional[dict] = None


class ViewJoinConfig(BaseModel):
    tables: List[TableConfig]
    joins: List[JoinConfig]


class ViewColumn(BaseModel):
    name: str
    source_table: Optional[str] = None
    source_column: Optional[str] = None
    alias: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None


class ViewCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    datasource_id: str
    view_type: str = ViewType.SINGLE_TABLE
    base_table_id: Optional[str] = None
    join_config: Optional[dict] = None
    custom_sql: Optional[str] = None
    columns: Optional[List[dict]] = None
    canvas_config: Optional[dict] = None
    description: Optional[str] = None


class ViewUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    view_type: Optional[str] = None
    base_table_id: Optional[str] = None
    join_config: Optional[dict] = None
    custom_sql: Optional[str] = None
    columns: Optional[List[dict]] = None
    canvas_config: Optional[dict] = None
    description: Optional[str] = None


class PreviewRequest(BaseModel):
    limit: int = 100


# ============ Routes ============
@router.get("")
def get_views(datasource_id: Optional[str] = None, db: Session = Depends(get_db)):
    """获取视图列表"""
    query = db.query(View)
    if datasource_id:
        query = query.filter(View.datasource_id == datasource_id)
    views = query.order_by(View.created_at.desc()).all()
    return [v.to_dict() for v in views]


@router.get("/{id}")
def get_view(id: str, db: Session = Depends(get_db)):
    """获取单个视图详情"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    return view.to_dict()


@router.post("")
def create_view(data: ViewCreate, db: Session = Depends(get_db)):
    """创建视图"""
    # 检查名称是否重复
    existing = db.query(View).filter(View.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"View name '{data.name}' already exists")
    
    # 验证数据源存在
    datasource = db.query(DataSource).filter(DataSource.id == data.datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    # 验证视图类型和必要字段
    if data.view_type == ViewType.SINGLE_TABLE:
        if not data.base_table_id:
            raise HTTPException(status_code=400, detail="base_table_id is required for single_table view")
        dataset = db.query(Dataset).filter(Dataset.id == data.base_table_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Base table not found")
    elif data.view_type == ViewType.JOINED:
        if not data.join_config:
            raise HTTPException(status_code=400, detail="join_config is required for joined view")
    elif data.view_type == ViewType.SQL:
        if not data.custom_sql:
            raise HTTPException(status_code=400, detail="custom_sql is required for sql view")
    
    view = View(
        name=data.name,
        display_name=data.display_name,
        datasource_id=data.datasource_id,
        view_type=data.view_type,
        base_table_id=data.base_table_id,
        join_config=data.join_config,
        custom_sql=data.custom_sql,
        columns=data.columns,
        canvas_config=data.canvas_config,
        description=data.description
    )
    db.add(view)
    db.commit()
    db.refresh(view)
    return view.to_dict()


@router.put("/{id}")
def update_view(id: str, data: ViewUpdate, db: Session = Depends(get_db)):
    """更新视图"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # 检查名称是否重复
    if data.name and data.name != view.name:
        existing = db.query(View).filter(View.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"View name '{data.name}' already exists")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(view, key, value)
    
    db.commit()
    db.refresh(view)
    return view.to_dict()


@router.delete("/{id}")
def delete_view(id: str, db: Session = Depends(get_db)):
    """删除视图"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # 检查是否有指标或维度引用此视图
    from app.models.metric import Metric
    from app.models.dimension import Dimension
    
    metrics_count = db.query(Metric).filter(Metric.view_id == id).count()
    dimensions_count = db.query(Dimension).filter(Dimension.view_id == id).count()
    
    if metrics_count > 0 or dimensions_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete view: {metrics_count} metrics and {dimensions_count} dimensions are using this view"
        )
    
    db.delete(view)
    db.commit()
    return {"message": "Deleted successfully"}


@router.post("/{id}/preview")
async def preview_view(id: str, request: PreviewRequest, db: Session = Depends(get_db)):
    """预览视图数据"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # 获取所有数据集
    datasets = {d.id: d for d in db.query(Dataset).all()}
    
    # 生成FROM子句
    from_clause = view.generate_from_clause(datasets)
    
    # 构建SELECT子句
    if view.columns:
        select_columns = []
        for col in view.columns:
            source_table = col.get("source_table", "")
            source_column = col.get("source_column", col.get("name"))
            alias = col.get("alias", col.get("name"))
            if source_table:
                select_columns.append(f"{source_table}.{source_column} AS {alias}")
            else:
                select_columns.append(f"{source_column} AS {alias}")
        select_clause = ", ".join(select_columns)
    else:
        select_clause = "*"
    
    sql = f"SELECT {select_clause} FROM {from_clause} LIMIT {request.limit}"
    
    try:
        result = await execute_query(
            sql=sql,
            datasource_id=view.datasource_id,
            limit=request.limit,
            db=db
        )
        return {
            "sql": sql,
            "columns": result.get("columns", []),
            "data": result.get("data", []),
            "total_count": result.get("total_count", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.get("/{id}/columns")
def get_view_columns(id: str, db: Session = Depends(get_db)):
    """获取视图可用字段列表"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    columns = []
    
    if view.view_type == ViewType.SINGLE_TABLE:
        # 单表模式：返回基础表的所有字段
        if view.base_table_id:
            dataset = db.query(Dataset).filter(Dataset.id == view.base_table_id).first()
            if dataset and dataset.columns:
                for col in dataset.columns:
                    columns.append({
                        "name": col.get("name"),
                        "type": col.get("type"),
                        "source_table": dataset.name,
                        "source_column": col.get("name"),
                        "nullable": col.get("nullable", True),
                        "comment": col.get("comment", "")
                    })
    
    elif view.view_type == ViewType.JOINED:
        # 多表模式：返回所有表的字段，带表别名前缀
        if view.join_config:
            tables = view.join_config.get("tables", [])
            for t in tables:
                dataset_id = t.get("id")
                alias = t.get("alias", "")
                dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
                if dataset and dataset.columns:
                    for col in dataset.columns:
                        columns.append({
                            "name": f"{alias}.{col.get('name')}",
                            "type": col.get("type"),
                            "source_table": alias,
                            "source_column": col.get("name"),
                            "nullable": col.get("nullable", True),
                            "comment": col.get("comment", "")
                        })
    
    elif view.view_type == ViewType.SQL:
        # 自定义SQL模式：返回已配置的字段列表
        if view.columns:
            columns = view.columns
    
    return columns


@router.post("/{id}/generate-sql")
def generate_view_sql(id: str, db: Session = Depends(get_db)):
    """根据视图配置生成SQL"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    datasets = {d.id: d for d in db.query(Dataset).all()}
    
    # 获取数据源类型
    datasource = db.query(DataSource).filter(DataSource.id == view.datasource_id).first()
    dialect = datasource.type if datasource else "mysql"
    
    from_clause = view.generate_from_clause(datasets, dialect)
    
    # 构建完整SQL
    if view.columns:
        select_columns = []
        for col in view.columns:
            source_table = col.get("source_table", "")
            source_column = col.get("source_column", col.get("name"))
            alias = col.get("alias", col.get("name"))
            if source_table:
                select_columns.append(f"{source_table}.{source_column} AS {alias}")
            else:
                select_columns.append(f"{source_column} AS {alias}")
        select_clause = ", ".join(select_columns)
    else:
        select_clause = "*"
    
    sql = f"SELECT {select_clause} FROM {from_clause}"
    
    return {
        "sql": sql,
        "view_type": view.view_type,
        "from_clause": from_clause
    }


@router.get("/{id}/tables")
def get_view_tables(id: str, db: Session = Depends(get_db)):
    """获取视图中引用的表列表"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    tables = []
    
    if view.view_type == ViewType.SINGLE_TABLE:
        if view.base_table_id:
            dataset = db.query(Dataset).filter(Dataset.id == view.base_table_id).first()
            if dataset:
                tables.append(dataset.to_dict())
    
    elif view.view_type == ViewType.JOINED:
        if view.join_config:
            table_ids = [t.get("id") for t in view.join_config.get("tables", [])]
            for tid in table_ids:
                dataset = db.query(Dataset).filter(Dataset.id == tid).first()
                if dataset:
                    tables.append(dataset.to_dict())
    
    return tables
