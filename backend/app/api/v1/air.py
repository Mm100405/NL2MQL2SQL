from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.air import Workbook, IntegrationTask, ConsolidationRule, DataAcceleration

router = APIRouter()


# ============ Pydantic Models ============

class WorkbookCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "#165DFF"


class WorkbookResponse(BaseModel):
    id: int
    name: str
    description: str
    color: str
    status: str
    owner: str
    updated_at: str

    class Config:
        from_attributes = True


class IntegrationTaskCreate(BaseModel):
    name: str
    source_type: str
    target_type: str
    schedule_type: str = "manual"
    cron_expr: str = ""
    interval_minutes: int = 60
    description: str = ""


class IntegrationTaskResponse(BaseModel):
    id: int
    name: str
    source_type: str
    target_type: str
    status: str
    schedule: str
    last_run_time: str = "-"
    last_run_duration: str = "-"

    class Config:
        from_attributes = True


class ConsolidationRuleCreate(BaseModel):
    name: str
    type: str
    source_tables: List[str]
    target_table: str = ""
    strategy: str = "union"
    condition: str = ""
    description: str = ""


class ConsolidationRuleResponse(BaseModel):
    id: int
    name: str
    type: str
    description: str
    source_tables: List[str]
    target_table: str
    strategy: str
    enabled: bool
    exec_count: int

    class Config:
        from_attributes = True


class DataAccelerationCreate(BaseModel):
    name: str
    type: str
    source_table: str
    query: str
    refresh_policy: str = "schedule"
    schedule: str = "daily"
    description: str = ""


class DataAccelerationResponse(BaseModel):
    id: int
    name: str
    type: str
    description: str
    source_table: str
    query: str
    enabled: bool
    speedup: int
    original_latency: int
    accelerated_latency: int
    schedule: str
    next_run: str = "-"
    storage: str = "-"
    last_refresh: str = "-"
    cache_size: str = "-"

    class Config:
        from_attributes = True


# ============ Workbook APIs ============

@router.post("/air/workbooks", response_model=WorkbookResponse)
def create_workbook(workbook: WorkbookCreate, db: Session = Depends(get_db)):
    """创建工作簿"""
    db_workbook = Workbook(
        name=workbook.name,
        description=workbook.description,
        color=workbook.color,
        status="stopped",
        owner="admin"
    )
    db.add(db_workbook)
    db.commit()
    db.refresh(db_workbook)
    return WorkbookResponse(
        id=db_workbook.id,
        name=db_workbook.name,
        description=db_workbook.description or "",
        color=db_workbook.color or "#165DFF",
        status=db_workbook.status or "stopped",
        owner=db_workbook.owner or "admin",
        updated_at=db_workbook.updated_at.strftime("%Y-%m-%d %H:%M") if db_workbook.updated_at else ""
    )


@router.get("/air/workbooks", response_model=List[WorkbookResponse])
def list_workbooks(db: Session = Depends(get_db)):
    """获取工作簿列表"""
    workbooks = db.query(Workbook).all()
    return [
        WorkbookResponse(
            id=w.id,
            name=w.name,
            description=w.description or "",
            color=w.color or "#165DFF",
            status=w.status or "stopped",
            owner=w.owner or "admin",
            updated_at=w.updated_at.strftime("%Y-%m-%d %H:%M") if w.updated_at else ""
        )
        for w in workbooks
    ]


@router.delete("/air/workbooks/{workbook_id}")
def delete_workbook(workbook_id: int, db: Session = Depends(get_db)):
    """删除工作簿"""
    workbook = db.query(Workbook).filter(Workbook.id == workbook_id).first()
    if not workbook:
        raise HTTPException(status_code=404, detail="Workbook not found")
    db.delete(workbook)
    db.commit()
    return {"message": "Workbook deleted"}


# ============ Integration Task APIs ============

@router.post("/air/integration-tasks", response_model=IntegrationTaskResponse)
def create_integration_task(task: IntegrationTaskCreate, db: Session = Depends(get_db)):
    """创建集成任务"""
    schedule_text = "手动" if task.schedule_type == "manual" else task.cron_expr
    db_task = IntegrationTask(
        name=task.name,
        source_type=task.source_type,
        target_type=task.target_type,
        status="paused",
        schedule=schedule_text,
        schedule_type=task.schedule_type,
        cron_expr=task.cron_expr,
        interval_minutes=task.interval_minutes,
        description=task.description,
        last_run_time="-",
        last_run_duration="-"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return IntegrationTaskResponse(
        id=db_task.id,
        name=db_task.name,
        source_type=db_task.source_type,
        target_type=db_task.target_type,
        status=db_task.status or "paused",
        schedule=db_task.schedule or "手动",
        last_run_time=db_task.last_run_time or "-",
        last_run_duration=db_task.last_run_duration or "-"
    )


@router.get("/air/integration-tasks", response_model=List[IntegrationTaskResponse])
def list_integration_tasks(db: Session = Depends(get_db)):
    """获取集成任务列表"""
    tasks = db.query(IntegrationTask).all()
    return [
        IntegrationTaskResponse(
            id=t.id,
            name=t.name,
            source_type=t.source_type,
            target_type=t.target_type,
            status=t.status or "paused",
            schedule=t.schedule or "手动",
            last_run_time=t.last_run_time or "-",
            last_run_duration=t.last_run_duration or "-"
        )
        for t in tasks
    ]


@router.put("/air/integration-tasks/{task_id}/toggle")
def toggle_integration_task(task_id: int, db: Session = Depends(get_db)):
    """切换任务状态"""
    task = db.query(IntegrationTask).filter(IntegrationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = "paused" if task.status == "running" else "running"
    db.commit()
    return {"message": "Task status toggled", "status": task.status}


# ============ Consolidation Rule APIs ============

@router.post("/air/consolidation-rules", response_model=ConsolidationRuleResponse)
def create_consolidation_rule(rule: ConsolidationRuleCreate, db: Session = Depends(get_db)):
    """创建整合规则"""
    db_rule = ConsolidationRule(
        name=rule.name,
        type=rule.type,
        description=rule.description,
        source_tables=rule.source_tables,
        target_table=rule.target_table,
        strategy=rule.strategy.upper(),
        condition=rule.condition,
        enabled=False,
        exec_count=0
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return ConsolidationRuleResponse(
        id=db_rule.id,
        name=db_rule.name,
        type=db_rule.type,
        description=db_rule.description or "",
        source_tables=db_rule.source_tables or [],
        target_table=db_rule.target_table or "",
        strategy=db_rule.strategy or "UNION",
        enabled=db_rule.enabled or False,
        exec_count=db_rule.exec_count or 0
    )


@router.get("/air/consolidation-rules", response_model=List[ConsolidationRuleResponse])
def list_consolidation_rules(db: Session = Depends(get_db)):
    """获取整合规则列表"""
    rules = db.query(ConsolidationRule).all()
    return [
        ConsolidationRuleResponse(
            id=r.id,
            name=r.name,
            type=r.type,
            description=r.description or "",
            source_tables=r.source_tables or [],
            target_table=r.target_table or "",
            strategy=r.strategy or "UNION",
            enabled=r.enabled or False,
            exec_count=r.exec_count or 0
        )
        for r in rules
    ]


# ============ Data Acceleration APIs ============

@router.post("/air/accelerations", response_model=DataAccelerationResponse)
def create_acceleration(accel: DataAccelerationCreate, db: Session = Depends(get_db)):
    """创建数据加速配置"""
    type_map = {
        "materialized_view": "物化视图",
        "cube": "OLAP Cube",
        "cache": "查询缓存"
    }
    db_accel = DataAcceleration(
        name=accel.name,
        type=type_map.get(accel.type, "物化视图"),
        description=accel.description,
        source_table=accel.source_table,
        query=accel.query,
        refresh_policy=accel.refresh_policy,
        schedule=accel.schedule,
        enabled=False,
        speedup=0,
        original_latency=2000,
        accelerated_latency=0,
        next_run="-",
        storage="-",
        last_refresh="-",
        cache_size="-"
    )
    db.add(db_accel)
    db.commit()
    db.refresh(db_accel)
    return DataAccelerationResponse(
        id=db_accel.id,
        name=db_accel.name,
        type=db_accel.type,
        description=db_accel.description or "",
        source_table=db_accel.source_table or "",
        query=db_accel.query or "",
        enabled=db_accel.enabled or False,
        speedup=db_accel.speedup or 0,
        original_latency=db_accel.original_latency or 0,
        accelerated_latency=db_accel.accelerated_latency or 0,
        schedule=db_accel.schedule or "手动",
        next_run=db_accel.next_run or "-",
        storage=db_accel.storage or "-",
        last_refresh=db_accel.last_refresh or "-",
        cache_size=db_accel.cache_size or "-"
    )


@router.get("/air/accelerations", response_model=List[DataAccelerationResponse])
def list_accelerations(db: Session = Depends(get_db)):
    """获取数据加速配置列表"""
    accels = db.query(DataAcceleration).all()
    return [
        DataAccelerationResponse(
            id=a.id,
            name=a.name,
            type=a.type,
            description=a.description or "",
            source_table=a.source_table or "",
            query=a.query or "",
            enabled=a.enabled or False,
            speedup=a.speedup or 0,
            original_latency=a.original_latency or 0,
            accelerated_latency=a.accelerated_latency or 0,
            schedule=a.schedule or "手动",
            next_run=a.next_run or "-",
            storage=a.storage or "-",
            last_refresh=a.last_refresh or "-",
            cache_size=a.cache_size or "-"
        )
        for a in accels
    ]


@router.put("/air/accelerations/{accel_id}/toggle")
def toggle_acceleration(accel_id: int, db: Session = Depends(get_db)):
    """切换加速状态"""
    accel = db.query(DataAcceleration).filter(DataAcceleration.id == accel_id).first()
    if not accel:
        raise HTTPException(status_code=404, detail="Acceleration not found")
    accel.enabled = not accel.enabled
    db.commit()
    return {"message": "Acceleration status toggled", "enabled": accel.enabled}
