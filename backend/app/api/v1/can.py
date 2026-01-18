from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.can import MetricCatalog, MetricApplication, MetricAcceleration, SystemRole, AuditLog

router = APIRouter()


# ============ Pydantic Models ============

class MetricCatalogCreate(BaseModel):
    name: str
    code: str
    type: str
    category: str
    formula: str
    description: str = ""
    tags: List[str] = []


class MetricCatalogResponse(BaseModel):
    id: int
    name: str
    code: str
    type: str
    status: str
    category: str
    description: str
    formula: str
    owner: str
    tags: List[str]
    dimensions: List[str]
    query_count: int
    application_count: int
    dependency_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MetricApplicationCreate(BaseModel):
    name: str
    type: str
    metrics: List[str]
    description: str = ""


class MetricApplicationResponse(BaseModel):
    id: int
    name: str
    type: str
    description: str
    metrics: List[str]
    owner: str
    view_count: int
    updated_at: str

    class Config:
        from_attributes = True


class MetricAccelerationCreate(BaseModel):
    metric_code: str
    dimensions: List[str]
    granularity: str
    refresh_policy: str = "interval"
    refresh_interval: int = 60


class MetricAccelerationResponse(BaseModel):
    id: int
    metric_name: str
    metric_code: str
    dimensions: List[str]
    granularity: str
    refresh_policy: str
    enabled: bool
    hit_rate: int
    original_latency: int
    accelerated_latency: int
    last_refresh: str
    cache_size: str

    class Config:
        from_attributes = True


class SystemRoleCreate(BaseModel):
    name: str
    description: str = ""
    permissions: List[str] = []


class SystemRoleResponse(BaseModel):
    id: int
    name: str
    description: str
    permissions: List[str]
    is_system: bool

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    time: str
    user: str
    action: str
    target: str
    details: str

    class Config:
        from_attributes = True


# ============ Metric Catalog APIs ============

@router.post("/can/catalogs", response_model=MetricCatalogResponse)
def create_metric_catalog(metric: MetricCatalogCreate, db: Session = Depends(get_db)):
    """创建指标"""
    db_metric = MetricCatalog(
        name=metric.name,
        code=metric.code,
        type=metric.type,
        status="draft",
        category=metric.category,
        description=metric.description,
        formula=metric.formula,
        owner="admin",
        tags=metric.tags,
        dimensions=[],
        query_count=0,
        application_count=0,
        dependency_count=0
    )
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return MetricCatalogResponse(
        id=db_metric.id,
        name=db_metric.name,
        code=db_metric.code,
        type=db_metric.type,
        status=db_metric.status,
        category=db_metric.category or "",
        description=db_metric.description or "",
        formula=db_metric.formula or "",
        owner=db_metric.owner or "admin",
        tags=db_metric.tags or [],
        dimensions=db_metric.dimensions or [],
        query_count=db_metric.query_count or 0,
        application_count=db_metric.application_count or 0,
        dependency_count=db_metric.dependency_count or 0,
        created_at=db_metric.created_at.strftime("%Y-%m-%d %H:%M") if db_metric.created_at else "",
        updated_at=db_metric.updated_at.strftime("%Y-%m-%d %H:%M") if db_metric.updated_at else ""
    )


@router.get("/can/catalogs", response_model=List[MetricCatalogResponse])
def list_metric_catalogs(db: Session = Depends(get_db)):
    """获取指标列表"""
    metrics = db.query(MetricCatalog).all()
    return [
        MetricCatalogResponse(
            id=m.id,
            name=m.name,
            code=m.code,
            type=m.type,
            status=m.status,
            category=m.category or "",
            description=m.description or "",
            formula=m.formula or "",
            owner=m.owner or "admin",
            tags=m.tags or [],
            dimensions=m.dimensions or [],
            query_count=m.query_count or 0,
            application_count=m.application_count or 0,
            dependency_count=m.dependency_count or 0,
            created_at=m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
            updated_at=m.updated_at.strftime("%Y-%m-%d %H:%M") if m.updated_at else ""
        )
        for m in metrics
    ]


@router.put("/can/catalogs/{metric_id}/publish")
def publish_metric(metric_id: int, db: Session = Depends(get_db)):
    """发布指标"""
    metric = db.query(MetricCatalog).filter(MetricCatalog.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    metric.status = "published"
    db.commit()
    return {"message": "Metric published"}


@router.put("/can/catalogs/{metric_id}/deprecate")
def deprecate_metric(metric_id: int, db: Session = Depends(get_db)):
    """废弃指标"""
    metric = db.query(MetricCatalog).filter(MetricCatalog.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    metric.status = "deprecated"
    db.commit()
    return {"message": "Metric deprecated"}


# ============ Metric Application APIs ============

@router.post("/can/applications", response_model=MetricApplicationResponse)
def create_metric_application(app: MetricApplicationCreate, db: Session = Depends(get_db)):
    """创建指标应用"""
    db_app = MetricApplication(
        name=app.name,
        type=app.type,
        description=app.description,
        metrics=app.metrics,
        owner="admin",
        view_count=0
    )
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return MetricApplicationResponse(
        id=db_app.id,
        name=db_app.name,
        type=db_app.type,
        description=db_app.description or "",
        metrics=db_app.metrics or [],
        owner=db_app.owner or "admin",
        view_count=db_app.view_count or 0,
        updated_at=db_app.updated_at.strftime("%Y-%m-%d") if db_app.updated_at else ""
    )


@router.get("/can/applications", response_model=List[MetricApplicationResponse])
def list_metric_applications(db: Session = Depends(get_db)):
    """获取指标应用列表"""
    apps = db.query(MetricApplication).all()
    return [
        MetricApplicationResponse(
            id=a.id,
            name=a.name,
            type=a.type,
            description=a.description or "",
            metrics=a.metrics or [],
            owner=a.owner or "admin",
            view_count=a.view_count or 0,
            updated_at=a.updated_at.strftime("%Y-%m-%d") if a.updated_at else ""
        )
        for a in apps
    ]


# ============ Metric Acceleration APIs ============

@router.post("/can/accelerations", response_model=MetricAccelerationResponse)
def create_metric_acceleration(accel: MetricAccelerationCreate, db: Session = Depends(get_db)):
    """创建指标加速配置"""
    metric_names = {
        "gmv": "销售额",
        "order_count": "订单量",
        "avg_order_value": "客单价",
        "new_users": "新增用户数"
    }
    refresh_text = "实时" if accel.refresh_policy == "realtime" else f"每{accel.refresh_interval}分钟"
    
    db_accel = MetricAcceleration(
        metric_name=metric_names.get(accel.metric_code, accel.metric_code),
        metric_code=accel.metric_code,
        dimensions=accel.dimensions,
        granularity=accel.granularity,
        refresh_policy=refresh_text,
        enabled=False,
        hit_rate=0,
        original_latency=2000,
        accelerated_latency=0,
        last_refresh="-",
        cache_size="-"
    )
    db.add(db_accel)
    db.commit()
    db.refresh(db_accel)
    return MetricAccelerationResponse(
        id=db_accel.id,
        metric_name=db_accel.metric_name,
        metric_code=db_accel.metric_code,
        dimensions=db_accel.dimensions or [],
        granularity=db_accel.granularity or "天",
        refresh_policy=db_accel.refresh_policy or "手动",
        enabled=db_accel.enabled or False,
        hit_rate=db_accel.hit_rate or 0,
        original_latency=db_accel.original_latency or 0,
        accelerated_latency=db_accel.accelerated_latency or 0,
        last_refresh=db_accel.last_refresh or "-",
        cache_size=db_accel.cache_size or "-"
    )


@router.get("/can/accelerations", response_model=List[MetricAccelerationResponse])
def list_metric_accelerations(db: Session = Depends(get_db)):
    """获取指标加速配置列表"""
    accels = db.query(MetricAcceleration).all()
    return [
        MetricAccelerationResponse(
            id=a.id,
            metric_name=a.metric_name,
            metric_code=a.metric_code,
            dimensions=a.dimensions or [],
            granularity=a.granularity or "天",
            refresh_policy=a.refresh_policy or "手动",
            enabled=a.enabled or False,
            hit_rate=a.hit_rate or 0,
            original_latency=a.original_latency or 0,
            accelerated_latency=a.accelerated_latency or 0,
            last_refresh=a.last_refresh or "-",
            cache_size=a.cache_size or "-"
        )
        for a in accels
    ]


@router.put("/can/accelerations/{accel_id}/toggle")
def toggle_metric_acceleration(accel_id: int, db: Session = Depends(get_db)):
    """切换指标加速状态"""
    accel = db.query(MetricAcceleration).filter(MetricAcceleration.id == accel_id).first()
    if not accel:
        raise HTTPException(status_code=404, detail="Acceleration not found")
    accel.enabled = not accel.enabled
    db.commit()
    return {"message": "Acceleration status toggled", "enabled": accel.enabled}


# ============ System Role APIs ============

@router.post("/can/roles", response_model=SystemRoleResponse)
def create_system_role(role: SystemRoleCreate, db: Session = Depends(get_db)):
    """创建角色"""
    db_role = SystemRole(
        name=role.name,
        description=role.description,
        permissions=role.permissions,
        is_system=False
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return SystemRoleResponse(
        id=db_role.id,
        name=db_role.name,
        description=db_role.description or "",
        permissions=db_role.permissions or [],
        is_system=db_role.is_system or False
    )


@router.get("/can/roles", response_model=List[SystemRoleResponse])
def list_system_roles(db: Session = Depends(get_db)):
    """获取角色列表"""
    roles = db.query(SystemRole).all()
    return [
        SystemRoleResponse(
            id=r.id,
            name=r.name,
            description=r.description or "",
            permissions=r.permissions or [],
            is_system=r.is_system or False
        )
        for r in roles
    ]


# ============ Audit Log APIs ============

@router.get("/can/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(db: Session = Depends(get_db)):
    """获取审计日志列表"""
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
    return [
        AuditLogResponse(
            id=log.id,
            time=log.time or "",
            user=log.user or "",
            action=log.action or "",
            target=log.target or "",
            details=log.details or ""
        )
        for log in logs
    ]


@router.post("/can/audit-logs")
def create_audit_log(
    user: str,
    action: str,
    target: str,
    details: str,
    db: Session = Depends(get_db)
):
    """创建审计日志"""
    log = AuditLog(
        time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user=user,
        action=action,
        target=target,
        details=details
    )
    db.add(log)
    db.commit()
    return {"message": "Audit log created"}
