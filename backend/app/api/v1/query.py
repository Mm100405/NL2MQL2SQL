from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import time

from app.database import get_db
from app.models.query_history import QueryHistory
from app.models.model_config import ModelConfig
from app.services.nl_parser import parse_natural_language
from app.services.mql_engine import mql_to_sql
from app.services.query_executor import execute_query
from app.utils.encryption import decrypt_api_key

router = APIRouter()


# ============ Schemas ============
class QueryRequest(BaseModel):
    natural_language: str
    context: Optional[dict] = None


class NL2MQLResponse(BaseModel):
    mql: str
    confidence: float
    interpretation: str


class MQL2SQLRequest(BaseModel):
    mql: str


class MQL2SQLResponse(BaseModel):
    sql: str
    datasources: List[str]
    lineage: Optional[dict] = None


class ExecuteRequest(BaseModel):
    sql: str
    datasource_id: str
    limit: int = 1000


class ExecuteResponse(BaseModel):
    columns: List[str]
    data: List[List]
    total_count: int
    execution_time: int
    chart_recommendation: Optional[str] = None


class FullQueryResponse(BaseModel):
    natural_language: str
    mql: str
    sql: str
    result: ExecuteResponse
    query_id: str


class DrillDownRequest(BaseModel):
    query_id: str
    drill_dimension: str
    filter: Optional[dict] = None


class AttributionRequest(BaseModel):
    metric: str
    dimensions: List[str]
    date_range: Optional[dict] = None


# ============ Routes ============
@router.post("/nl2mql", response_model=NL2MQLResponse)
async def nl_to_mql(request: QueryRequest, db: Session = Depends(get_db)):
    """将自然语言转换为MQL"""
    # Get default model config
    model_config = db.query(ModelConfig).filter(
        ModelConfig.is_default == True,
        ModelConfig.is_active == True
    ).first()
    
    if not model_config:
        raise HTTPException(status_code=400, detail="No active model configured. Please configure an AI model first.")
    
    api_key = decrypt_api_key(model_config.api_key) if model_config.api_key else None
    
    result = await parse_natural_language(
        natural_language=request.natural_language,
        provider=model_config.provider,
        model_name=model_config.model_name,
        api_key=api_key,
        api_base=model_config.api_base,
        config_params=model_config.config_params,
        db=db
    )
    
    return NL2MQLResponse(**result)


@router.post("/mql2sql", response_model=MQL2SQLResponse)
async def mql_to_sql_endpoint(request: MQL2SQLRequest, db: Session = Depends(get_db)):
    """将MQL转换为SQL"""
    result = await mql_to_sql(request.mql, db)
    return MQL2SQLResponse(**result)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_sql(request: ExecuteRequest, db: Session = Depends(get_db)):
    """执行SQL查询"""
    start_time = time.time()
    
    result = await execute_query(
        sql=request.sql,
        datasource_id=request.datasource_id,
        limit=request.limit,
        db=db
    )
    
    execution_time = int((time.time() - start_time) * 1000)
    result["execution_time"] = execution_time
    
    return ExecuteResponse(**result)


@router.post("/nl2result", response_model=FullQueryResponse)
async def nl_to_result(request: QueryRequest, db: Session = Depends(get_db)):
    """端到端查询：自然语言直接到结果"""
    start_time = time.time()
    
    # Get default model config
    model_config = db.query(ModelConfig).filter(
        ModelConfig.is_default == True,
        ModelConfig.is_active == True
    ).first()
    
    if not model_config:
        raise HTTPException(status_code=400, detail="No active model configured. Please configure an AI model first.")
    
    api_key = decrypt_api_key(model_config.api_key) if model_config.api_key else None
    
    # Step 1: NL to MQL
    nl_result = await parse_natural_language(
        natural_language=request.natural_language,
        provider=model_config.provider,
        model_name=model_config.model_name,
        api_key=api_key,
        api_base=model_config.api_base,
        config_params=model_config.config_params,
        db=db
    )
    mql = nl_result["mql"]
    
    # Step 2: MQL to SQL
    sql_result = await mql_to_sql(mql, db)
    sql = sql_result["sql"]
    datasource_id = sql_result["datasources"][0] if sql_result["datasources"] else None
    
    # Step 3: Execute SQL
    if datasource_id:
        query_result = await execute_query(sql, datasource_id, limit=1000, db=db)
    else:
        # Use demo data if no datasource
        query_result = {
            "columns": ["日期", "销售额"],
            "data": [
                ["2024-01-01", 10000],
                ["2024-01-02", 12000],
                ["2024-01-03", 9500],
                ["2024-01-04", 11000],
                ["2024-01-05", 13000]
            ],
            "total_count": 5,
            "chart_recommendation": "line"
        }
    
    execution_time = int((time.time() - start_time) * 1000)
    query_result["execution_time"] = execution_time
    
    # Save to history
    history = QueryHistory(
        natural_language=request.natural_language,
        mql_query=mql,
        sql_query=sql,
        execution_time=execution_time,
        result_count=query_result["total_count"],
        status="success"
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    
    return FullQueryResponse(
        natural_language=request.natural_language,
        mql=mql,
        sql=sql,
        result=ExecuteResponse(**query_result),
        query_id=history.id
    )


@router.post("/drill-down")
async def drill_down(request: DrillDownRequest, db: Session = Depends(get_db)):
    """下钻分析"""
    # TODO: Implement drill-down logic
    return {"message": "Drill-down feature coming soon"}


@router.post("/attribution")
async def attribution_analysis(request: AttributionRequest, db: Session = Depends(get_db)):
    """归因分析"""
    # TODO: Implement attribution analysis
    return {"message": "Attribution analysis feature coming soon"}


@router.get("/history")
def get_query_history(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """获取查询历史"""
    offset = (page - 1) * page_size
    
    total = db.query(QueryHistory).count()
    items = db.query(QueryHistory)\
        .order_by(QueryHistory.created_at.desc())\
        .offset(offset)\
        .limit(page_size)\
        .all()
    
    return {
        "items": [h.to_dict() for h in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/history/{id}")
def get_query_history_detail(id: str, db: Session = Depends(get_db)):
    """获取查询历史详情"""
    history = db.query(QueryHistory).filter(QueryHistory.id == id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Query history not found")
    return history.to_dict()


@router.delete("/history/{id}")
def delete_query_history(id: str, db: Session = Depends(get_db)):
    """删除查询历史"""
    history = db.query(QueryHistory).filter(QueryHistory.id == id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Query history not found")
    db.delete(history)
    db.commit()
    return {"message": "Deleted successfully"}
