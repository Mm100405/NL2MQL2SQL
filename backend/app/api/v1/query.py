from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import time
import uuid

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


class AnalysisStep(BaseModel):
    title: str
    content: str
    status: str = "success"


class NL2MQLResponse(BaseModel):
    mql: dict
    steps: List[AnalysisStep]
    confidence: float
    interpretation: str


class MQL2SQLRequest(BaseModel):
    mql: dict


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
    query_id: Optional[str] = None


class FullQueryResponse(BaseModel):
    natural_language: str
    mql: dict
    sql: str
    result: ExecuteResponse
    steps: List[AnalysisStep]
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
class IntentResponse(BaseModel):
    intent: str
    suggested_metrics: List[str]
    suggested_dimensions: List[str]
    steps: List[AnalysisStep]


@router.post("/analyze-intent", response_model=IntentResponse)
async def analyze_intent(request: QueryRequest, db: Session = Depends(get_db)):
    """分析查询意图和相关元数据"""
    from app.models.metric import Metric
    from app.models.dimension import Dimension
    
    # 简单的关键词匹配模拟检索 (实际应使用向量检索)
    q = request.natural_language.lower()
    all_metrics = db.query(Metric).all()
    all_dimensions = db.query(Dimension).all()
    
    suggested_metrics = [m for m in all_metrics if any(
        word in m.name.lower() or 
        word in (m.display_name or "").lower() or 
        word in (m.description or "").lower() 
        for word in q.split()
    )]
    if not suggested_metrics: suggested_metrics = all_metrics[:5]
    
    suggested_dims = [d for d in all_dimensions if any(
        word in d.name.lower() or 
        word in (d.display_name or "").lower() or 
        word in (d.description or "").lower() 
        for word in q.split()
    )]
    if not suggested_dims: suggested_dims = all_dimensions[:5]
    
    metrics_str = ", ".join([m.display_name or m.name for m in suggested_metrics[:10]])
    dims_str = ", ".join([d.display_name or d.name for d in suggested_dims[:10]])
    
    steps = [
        {
            "title": "意图识别",
            "content": f"正在分析您的查询：'{request.natural_language}'...",
            "status": "success"
        },
        {
            "title": "指标检索",
            "content": f"检索到相关指标：{metrics_str}\n相关维度：{dims_str}",
            "status": "success"
        }
    ]
    
    return IntentResponse(
        intent="具体指标和维度的精准查询",
        suggested_metrics=[m.display_name or m.name for m in suggested_metrics],
        suggested_dimensions=[d.display_name or d.name for d in suggested_dims],
        steps=steps
    )


@router.post("/generate-mql", response_model=NL2MQLResponse)
async def generate_mql(request: QueryRequest, db: Session = Depends(get_db)):
    """基于意图生成 MQL JSON"""
    model_config = db.query(ModelConfig).filter(
        ModelConfig.is_default == True,
        ModelConfig.is_active == True
    ).first()
    
    if not model_config:
        raise HTTPException(status_code=400, detail="No active model configured.")
    
    api_key = decrypt_api_key(model_config.api_key) if model_config.api_key else None
    
    result = await parse_natural_language(
        natural_language=request.natural_language,
        provider=model_config.provider,
        model_name=model_config.model_name,
        api_key=api_key,
        api_base=model_config.api_base,
        config_params=model_config.config_params,
        db=db,
        context=request.context
    )
    
    return NL2MQLResponse(**result)


@router.post("/mql2sql", response_model=MQL2SQLResponse)
async def mql_to_sql_endpoint(request: MQL2SQLRequest, db: Session = Depends(get_db)):
    """将MQL转换为SQL"""
    result = await mql_to_sql(request.mql, db)
    return MQL2SQLResponse(**result)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_sql(request: ExecuteRequest, db: Session = Depends(get_db)):
    """执行SQL查询（纯执行，不保存历史记录）"""
    start_time = time.time()
    
    try:
        result = await execute_query(
            sql=request.sql,
            datasource_id=request.datasource_id,
            limit=request.limit,
            db=db
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        result["execution_time"] = execution_time
        
        return ExecuteResponse(**result)
    except Exception as e:
        raise e


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
    steps = nl_result["steps"]
    
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
            "columns": ["日期", "销售额", "销售额年同比"],
            "data": [
                ["2025-04-01", 1000000, 0.12],
                ["2025-04-02", 1200000, 0.15],
                ["2025-04-03", 950000, -0.05],
                ["2025-04-04", 1100000, 0.08],
                ["2025-04-05", 1300000, 0.20]
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
        steps=steps,
        query_id=history.id
    )


@router.post("/drill-down")
async def drill_down(request: DrillDownRequest, db: Session = Depends(get_db)):
    """下钻分析"""
    from app.models.query_history import QueryHistory

    # 获取原查询历史
    original_query = db.query(QueryHistory).filter(QueryHistory.id == request.query_id).first()
    if not original_query:
        raise HTTPException(status_code=404, detail="Query history not found")

    # 解析原MQL
    original_mql = original_query.mql_query
    if not original_mql or not isinstance(original_mql, dict):
        raise HTTPException(status_code=400, detail="Invalid MQL format")

    # 添加下钻维度
    if "dimensions" not in original_mql:
        original_mql["dimensions"] = []
    
    # 检查是否已存在该维度
    if request.drill_dimension not in original_mql["dimensions"]:
        original_mql["dimensions"].insert(0, request.drill_dimension)  # 插入到最前面

    # 应用过滤条件（如果有）
    if request.filter:
        if "filters" not in original_mql:
            original_mql["filters"] = []
        original_mql["filters"].extend(request.filter.get("conditions", []))

    # 转换为SQL
    try:
        mql_result = await mql_to_sql(original_mql, db)
        sql = mql_result["sql"]
        datasource_id = mql_result["datasources"][0] if mql_result["datasources"] else None

        if not datasource_id:
            raise HTTPException(status_code=400, detail="No datasource found")

        # 执行查询
        result = execute_query(sql, datasource_id, db)

        return {
            "mql": original_mql,
            "sql": sql,
            "result": {
                "columns": result.columns,
                "data": result.data,
                "total_count": result.total_count,
                "execution_time": result.execution_time
            },
            "drill_dimension": request.drill_dimension,
            "message": f"已按 {request.drill_dimension} 维度下钻"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drill-down failed: {str(e)}")


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
    """获取查询历史（按对话ID分组，每个对话只显示一条最新记录）"""
    from sqlalchemy import func
    
    # 子查询：获取每个conversation_id的最新记录ID
    subquery = db.query(
        QueryHistory.conversation_id,
        func.max(QueryHistory.created_at).label('max_created_at')
    ).group_by(QueryHistory.conversation_id).subquery()
    
    # 主查询：关联获取完整记录
    query = db.query(QueryHistory).join(
        subquery,
        (QueryHistory.conversation_id == subquery.c.conversation_id) &
        (QueryHistory.created_at == subquery.c.max_created_at)
    ).order_by(QueryHistory.created_at.desc())
    
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    
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


@router.post("/conversation/start")
def start_conversation(db: Session = Depends(get_db)):
    """开始新的对话，返回对话ID"""
    conversation_id = str(uuid.uuid4())
    return {"conversation_id": conversation_id}


class SaveConversationRequest(BaseModel):
    messages: list


@router.post("/conversation/{conversation_id}/save")
def save_conversation_history(
    conversation_id: str,
    request: SaveConversationRequest,
    db: Session = Depends(get_db)
):
    """保存完整的对话历史记录"""
    messages = request.messages
    # 查找是否已存在该对话的历史记录
    existing_history = db.query(QueryHistory).filter(
        QueryHistory.conversation_id == conversation_id
    ).first()
    
    if existing_history:
        # 更新现有记录
        existing_history.messages = messages
        existing_history.natural_language = messages[0]["content"] if messages else "对话记录"
        db.commit()
        db.refresh(existing_history)
        return {"id": existing_history.id, "updated": True}
    else:
        # 创建新记录
        history = QueryHistory(
            conversation_id=conversation_id,
            natural_language=messages[0]["content"] if messages else "对话记录",
            messages=messages,
            status="success"
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        return {"id": history.id, "created": True}


@router.get("/conversation/{conversation_id}")
def get_conversation_history(conversation_id: str, db: Session = Depends(get_db)):
    """获取完整对话历史记录"""
    history = db.query(QueryHistory).filter(
        QueryHistory.conversation_id == conversation_id
    ).first()
    
    if not history:
        raise HTTPException(status_code=404, detail="Conversation history not found")
    
    return history.to_dict()
