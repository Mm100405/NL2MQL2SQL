from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.datasource import DataSource
from app.models.dataset import Dataset
from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.relation import DataRelation
from app.models.view import View

router = APIRouter()


# ============ Schemas ============
class DataSourceCreate(BaseModel):
    name: str
    type: str
    connection_config: dict


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    connection_config: Optional[dict] = None


class DatasetCreate(BaseModel):
    datasource_id: str
    name: str
    physical_name: str
    schema_name: Optional[str] = None
    columns: Optional[List[dict]] = None
    description: Optional[str] = None


class MetricCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    metric_type: str = "basic"
    source_type: Optional[str] = "physical"  # physical | view
    dataset_id: Optional[str] = None
    view_id: Optional[str] = None
    aggregation: Optional[str] = None
    calculation_method: Optional[str] = "field"
    measure_column: Optional[str] = None
    calculation_formula: Optional[str] = None
    is_semi_additive: Optional[dict] = None
    date_column_id: Optional[str] = None
    base_metric_id: Optional[str] = None
    derivation_type: Optional[str] = "none"
    time_constraint: Optional[str] = None
    analysis_dimensions: Optional[List[str]] = None
    filters: Optional[List[dict]] = None
    synonyms: Optional[List[str]] = None
    unit: Optional[str] = None
    description: Optional[str] = None


class DimensionCreate(BaseModel):
    source_type: Optional[str] = "physical"  # physical | view
    dataset_id: Optional[str] = None
    view_id: Optional[str] = None
    name: str
    display_name: Optional[str] = None
    physical_column: str
    data_type: str = "string"
    dimension_type: str = "normal"
    hierarchy: Optional[dict] = None
    format_config: Optional[dict] = None
    synonyms: Optional[List[str]] = None
    description: Optional[str] = None


class RelationCreate(BaseModel):
    left_dataset_id: str
    right_dataset_id: str
    join_type: str = "INNER"
    join_conditions: List[dict]
    relationship_type: Optional[str] = None
    description: Optional[str] = None


# ============ DataSource Routes ============
@router.get("/datasources")
def get_datasources(db: Session = Depends(get_db)):
    sources = db.query(DataSource).all()
    return [s.to_dict() for s in sources]


@router.get("/datasources/{id}")
def get_datasource(id: str, db: Session = Depends(get_db)):
    source = db.query(DataSource).filter(DataSource.id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    return source.to_dict()


@router.post("/datasources")
def create_datasource(data: DataSourceCreate, db: Session = Depends(get_db)):
    source = DataSource(
        name=data.name,
        type=data.type,
        connection_config=data.connection_config,
        status="inactive"
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source.to_dict()


@router.put("/datasources/{id}")
def update_datasource(id: str, data: DataSourceUpdate, db: Session = Depends(get_db)):
    source = db.query(DataSource).filter(DataSource.id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail="DataSource not found")

    update_data = data.model_dump(exclude_unset=True)

    # 特殊处理 connection_config：如果 password 为 "******" 或空，则保留原密码
    if "connection_config" in update_data:
        connection_config = update_data["connection_config"]
        if connection_config.get("password") in [None, "", "******"]:
            # 保留原密码
            connection_config["password"] = source.connection_config.get("password")

    for key, value in update_data.items():
        setattr(source, key, value)

    db.commit()
    db.refresh(source)
    return source.to_dict()


@router.delete("/datasources/{id}")
def delete_datasource(id: str, db: Session = Depends(get_db)):
    source = db.query(DataSource).filter(DataSource.id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail="DataSource not found")
    db.delete(source)
    db.commit()
    return {"message": "Deleted successfully"}


@router.post("/datasources/{id}/test")
async def test_datasource_connection(id: str, db: Session = Depends(get_db)):
    source = db.query(DataSource).filter(DataSource.id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail="DataSource not found")

    # Test connection based on database type
    try:
        if source.type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=source.connection_config.get("host", "localhost"),
                port=source.connection_config.get("port", 5432),
                database=source.connection_config["database"],
                user=source.connection_config.get("username", ""),
                password=source.connection_config.get("password", "")
            )
            conn.close()
        elif source.type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=source.connection_config.get("host", "localhost"),
                port=source.connection_config.get("port", 3306),
                database=source.connection_config["database"],
                user=source.connection_config.get("username", ""),
                password=source.connection_config.get("password", "")
            )
            conn.close()
        elif source.type == "clickhouse":
            import clickhouse_driver
            client = clickhouse_driver.Client(
                host=source.connection_config.get("host", "localhost"),
                port=source.connection_config.get("port", 9000),
                database=source.connection_config["database"],
                user=source.connection_config.get("username", "default"),
                password=source.connection_config.get("password", "")
            )
            client.disconnect()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {source.type}")

        source.status = "active"
        db.commit()
        return {"success": True, "message": "Connection successful"}
    except Exception as e:
        source.status = "error"
        db.commit()
        return {"success": False, "message": f"Connection failed: {str(e)}"}


class ConnectionConfigTest(BaseModel):
    type: str
    connection_config: dict


@router.post("/datasources/test")
async def test_connection_config(data: ConnectionConfigTest):
    """测试连接配置，不需要先创建数据源"""
    try:
        if data.type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=data.connection_config.get("host", "localhost"),
                port=data.connection_config.get("port", 5432),
                database=data.connection_config.get("database"),
                user=data.connection_config.get("username", ""),
                password=data.connection_config.get("password", "")
            )
            conn.close()
        elif data.type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=data.connection_config.get("host", "localhost"),
                port=data.connection_config.get("port", 3306),
                database=data.connection_config.get("database"),
                user=data.connection_config.get("username", ""),
                password=data.connection_config.get("password", "")
            )
            conn.close()
        elif data.type == "clickhouse":
            import clickhouse_driver
            client = clickhouse_driver.Client(
                host=data.connection_config.get("host", "localhost"),
                port=data.connection_config.get("port", 9000),
                database=data.connection_config.get("database"),
                user=data.connection_config.get("username", "default"),
                password=data.connection_config.get("password", "")
            )
            client.disconnect()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {data.type}")

        return {"success": True, "message": "Connection successful"}
    except Exception as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.post("/datasources/{datasource_id}/sync")
async def sync_physical_tables(datasource_id: str, db: Session = Depends(get_db)):
    """从数据源同步所有物理表到数据库"""
    # 获取数据源
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")

    tables = []
    try:
        # 连接数据库获取表列表
        if datasource.type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=datasource.connection_config.get("host", "localhost"),
                port=datasource.connection_config.get("port", 5432),
                database=datasource.connection_config["database"],
                user=datasource.connection_config.get("username", ""),
                password=datasource.connection_config.get("password", "")
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            """)
            for table_name, schema_name in cursor.fetchall():
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = %s
                    ORDER BY ordinal_position
                """, (table_name, schema_name))
                columns = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "comment": ""
                    }
                    for col in cursor.fetchall()
                ]
                tables.append({
                    "name": table_name,
                    "physical_name": table_name,
                    "schema_name": schema_name,
                    "columns": columns
                })
            conn.close()

        elif datasource.type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=datasource.connection_config.get("host", "localhost"),
                port=datasource.connection_config.get("port", 3306),
                database=datasource.connection_config["database"],
                user=datasource.connection_config.get("username", ""),
                password=datasource.connection_config.get("password", "")
            )
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            for (table_name,) in cursor.fetchall():
                cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
                columns = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[3] == "YES",
                        "comment": col[8] or ""
                    }
                    for col in cursor.fetchall()
                ]
                tables.append({
                    "name": table_name,
                    "physical_name": table_name,
                    "schema_name": datasource.connection_config["database"],
                    "columns": columns
                })
            conn.close()

        elif datasource.type == "clickhouse":
            import clickhouse_driver
            client = clickhouse_driver.Client(
                host=datasource.connection_config.get("host", "localhost"),
                port=datasource.connection_config.get("port", 9000),
                database=datasource.connection_config["database"],
                user=datasource.connection_config.get("username", "default"),
                password=datasource.connection_config.get("password", "")
            )
            result = client.execute("SHOW TABLES")
            for (table_name,) in result:
                desc = client.execute(f"DESCRIBE TABLE {table_name}")
                columns = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": "Nullable" in col[1],
                        "comment": col[4] if len(col) > 4 else ""
                    }
                    for col in desc
                ]
                tables.append({
                    "name": table_name,
                    "physical_name": table_name,
                    "schema_name": datasource.connection_config["database"],
                    "columns": columns
                })
            client.disconnect()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {datasource.type}")

        # 保存或更新表到数据库
        sync_count = 0
        for table_data in tables:
            # 检查是否已存在
            existing = db.query(Dataset).filter(
                Dataset.datasource_id == datasource_id,
                Dataset.physical_name == table_data["physical_name"]
            ).first()

            if existing:
                # 更新现有表
                existing.name = table_data["name"]
                existing.schema_name = table_data["schema_name"]
                existing.columns = table_data["columns"]
                sync_count += 1
            else:
                # 创建新表
                new_dataset = Dataset(
                    datasource_id=datasource_id,
                    name=table_data["name"],
                    physical_name=table_data["physical_name"],
                    schema_name=table_data["schema_name"],
                    columns=table_data["columns"],
                    description=""
                )
                db.add(new_dataset)
                sync_count += 1

        db.commit()
        return {"message": f"Successfully synced {sync_count} tables", "count": sync_count}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync tables: {str(e)}")




# ============ Dataset Routes ============
@router.get("/datasets")
def get_datasets(datasource_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Dataset)
    if datasource_id:
        query = query.filter(Dataset.datasource_id == datasource_id)
    datasets = query.all()
    return [d.to_dict() for d in datasets]


@router.get("/datasets/{id}")
def get_dataset(id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset.to_dict()


@router.post("/datasets")
def create_dataset(data: DatasetCreate, db: Session = Depends(get_db)):
    dataset = Dataset(**data.model_dump())
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset.to_dict()


@router.put("/datasets/{id}")
def update_dataset(id: str, data: dict, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    for key, value in data.items():
        if hasattr(dataset, key):
            setattr(dataset, key, value)
    
    db.commit()
    db.refresh(dataset)
    return dataset.to_dict()


@router.delete("/datasets/{id}")
def delete_dataset(id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    db.delete(dataset)
    db.commit()
    return {"message": "Deleted successfully"}


@router.post("/datasets/sync")
async def sync_datasets_from_source(request: dict, db: Session = Depends(get_db)):
    """从数据源同步数据集"""
    datasource_id = request.get("datasource_id")
    if not datasource_id:
        raise HTTPException(status_code=400, detail="datasource_id is required")
    
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    
    tables = []
    try:
        if datasource.type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=datasource.connection_config.get("host", "localhost"),
                port=datasource.connection_config.get("port", 5432),
                database=datasource.connection_config["database"],
                user=datasource.connection_config.get("username", ""),
                password=datasource.connection_config.get("password", "")
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name, table_schema 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            """)
            for table_name, schema_name in cursor.fetchall():
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = %s
                    ORDER BY ordinal_position
                """, (table_name, schema_name))
                columns = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "comment": ""
                    }
                    for col in cursor.fetchall()
                ]
                tables.append({"name": table_name, "schema": schema_name, "columns": columns})
            conn.close()
            
        elif datasource.type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=datasource.connection_config.get("host", "localhost"),
                port=datasource.connection_config.get("port", 3306),
                database=datasource.connection_config["database"],
                user=datasource.connection_config.get("username", ""),
                password=datasource.connection_config.get("password", "")
            )
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            for (table_name,) in cursor.fetchall():
                cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
                columns = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[3] == "YES",
                        "comment": col[8] or ""
                    }
                    for col in cursor.fetchall()
                ]
                tables.append({"name": table_name, "schema": datasource.connection_config["database"], "columns": columns})
            conn.close()
            
        elif datasource.type == "clickhouse":
            import clickhouse_driver
            client = clickhouse_driver.Client(
                host=datasource.connection_config.get("host", "localhost"),
                port=datasource.connection_config.get("port", 9000),
                database=datasource.connection_config["database"],
                user=datasource.connection_config.get("username", "default"),
                password=datasource.connection_config.get("password", "")
            )
            result = client.execute("SHOW TABLES")
            for (table_name,) in result:
                desc = client.execute(f"DESCRIBE TABLE {table_name}")
                columns = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": "Nullable" in col[1],
                        "comment": col[4] if len(col) > 4 else ""
                    }
                    for col in desc
                ]
                tables.append({"name": table_name, "schema": datasource.connection_config["database"], "columns": columns})
            client.disconnect()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {datasource.type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync tables: {str(e)}")
    
    return tables


# ============ Metric Routes ============
@router.get("/metrics")
def get_metrics(metric_type: Optional[str] = None, dataset_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Metric)
    if metric_type:
        query = query.filter(Metric.metric_type == metric_type)
    if dataset_id:
        query = query.filter(Metric.dataset_id == dataset_id)
    metrics = query.all()
    return [m.to_dict() for m in metrics]


@router.get("/metrics/{id}")
def get_metric(id: str, db: Session = Depends(get_db)):
    metric = db.query(Metric).filter(Metric.id == id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    return metric.to_dict()


def get_inherited_dimensions(metric_data: dict, db: Session) -> List[str]:
    """Get inherited dimensions from base metrics"""
    from app.utils.mql_validator import MQLValidator
    
    metric_type = metric_data.get("metric_type")
    base_dimensions = set()
    
    if metric_type == "derived":
        base_id = metric_data.get("base_metric_id")
        if base_id:
            base_metric = db.query(Metric).filter(Metric.id == base_id).first()
            if base_metric and base_metric.analysis_dimensions:
                base_dimensions.update(base_metric.analysis_dimensions)
                
    elif metric_type == "composite":
        formula = metric_data.get("calculation_formula")
        if formula:
            validator = MQLValidator(db)
            ref_names = validator.extract_referenced_metrics(formula)
            for name in ref_names:
                ref_metric = db.query(Metric).filter(Metric.name == name).first()
                if ref_metric and ref_metric.analysis_dimensions:
                    if not base_dimensions:
                        base_dimensions.update(ref_metric.analysis_dimensions)
                    else:
                        # For composite metrics, typically we take the intersection or union?
                        # User says "inherit all", implying union, but typically it should be intersection to be safe.
                        # However, "inherit all dimensions of its base metrics" usually means union in this context.
                        base_dimensions.update(ref_metric.analysis_dimensions)
    
    return list(base_dimensions)


@router.post("/metrics")
def create_metric(data: MetricCreate, db: Session = Depends(get_db)):
    metric_dict = data.model_dump()
    
    # 移除前端辅助字段
    metric_dict.pop("source_type", None)
    
    # 将空字符串转换为 None（外键字段）
    for key in ['view_id', 'dataset_id', 'base_metric_id', 'date_column_id']:
        if metric_dict.get(key) == '':
            metric_dict[key] = None
    
    # Handle dimension inheritance for derived/composite metrics
    if metric_dict["metric_type"] in ["derived", "composite"]:
        inherited = get_inherited_dimensions(metric_dict, db)
        
        requested = metric_dict.get("analysis_dimensions") or []
        if not requested:
            # Default to all inherited dimensions if none requested
            metric_dict["analysis_dimensions"] = inherited
        else:
            # Validate: no new dimensions allowed
            inherited_set = set(inherited)
            invalid = [d for d in requested if d not in inherited_set]
            if invalid:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot add dimensions not present in base metrics: {invalid}"
                )
    
    metric = Metric(**metric_dict)
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric.to_dict()


@router.put("/metrics/{id}")
def update_metric(id: str, data: dict, db: Session = Depends(get_db)):
    metric = db.query(Metric).filter(Metric.id == id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    # If updating metric_type or base_metric_id or formula, re-evaluate dimensions
    temp_data = metric.to_dict()
    temp_data.update(data)
    
    if temp_data["metric_type"] in ["derived", "composite"]:
        inherited = get_inherited_dimensions(temp_data, db)
        requested = data.get("analysis_dimensions")
        
        if requested is not None:
            inherited_set = set(inherited)
            invalid = [d for d in requested if d not in inherited_set]
            if invalid:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Cannot add dimensions not present in base metrics: {invalid}"
                )
    
    for key, value in data.items():
        if hasattr(metric, key):
            # 将空字符串转换为 None（外键字段）
            if key in ['view_id', 'dataset_id', 'base_metric_id', 'date_column_id'] and value == '':
                value = None
            setattr(metric, key, value)
    
    db.commit()
    db.refresh(metric)
    return metric.to_dict()


@router.delete("/metrics/{id}")
def delete_metric(id: str, db: Session = Depends(get_db)):
    metric = db.query(Metric).filter(Metric.id == id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    db.delete(metric)
    db.commit()
    return {"message": "Deleted successfully"}


@router.post("/metrics/validate")
def validate_metric_formula(formula: str, db: Session = Depends(get_db)):
    from app.utils.mql_validator import MQLValidator
    
    validator = MQLValidator(db)
    is_valid, message = validator.validate(formula)
    
    result = {"valid": is_valid, "message": message}
    
    if is_valid:
        referenced_metrics = validator.extract_referenced_metrics(formula)
        result["referenced_metrics"] = referenced_metrics
    
    return result


# ============ Dimension Routes ============
@router.get("/dimensions")
def get_dimensions(dataset_id: Optional[str] = None, view_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Dimension)
    if dataset_id:
        query = query.filter(Dimension.dataset_id == dataset_id)
    if view_id:
        query = query.filter(Dimension.view_id == view_id)
    dimensions = query.all()
    return [d.to_dict() for d in dimensions]


@router.get("/dimensions/{id}")
def get_dimension(id: str, db: Session = Depends(get_db)):
    dimension = db.query(Dimension).filter(Dimension.id == id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return dimension.to_dict()


@router.post("/dimensions")
def create_dimension(data: DimensionCreate, db: Session = Depends(get_db)):
    dimension_dict = data.model_dump()
    
    # 移除前端辅助字段
    dimension_dict.pop("source_type", None)
    
    # 将空字符串转换为 None（外键字段）
    for key in ['view_id', 'dataset_id']:
        if dimension_dict.get(key) == '':
            dimension_dict[key] = None
    
    dimension = Dimension(**dimension_dict)
    db.add(dimension)
    db.commit()
    db.refresh(dimension)
    return dimension.to_dict()


@router.put("/dimensions/{id}")
def update_dimension(id: str, data: dict, db: Session = Depends(get_db)):
    dimension = db.query(Dimension).filter(Dimension.id == id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    
    for key, value in data.items():
        if hasattr(dimension, key):
            # 将空字符串转换为 None（外键字段）
            if key in ['view_id', 'dataset_id'] and value == '':
                value = None
            setattr(dimension, key, value)
    
    db.commit()
    db.refresh(dimension)
    return dimension.to_dict()


@router.delete("/dimensions/{id}")
def delete_dimension(id: str, db: Session = Depends(get_db)):
    dimension = db.query(Dimension).filter(Dimension.id == id).first()
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    db.delete(dimension)
    db.commit()
    return {"message": "Deleted successfully"}


# ============ Relation Routes ============
@router.get("/relations")
def get_relations(db: Session = Depends(get_db)):
    relations = db.query(DataRelation).all()
    return [r.to_dict() for r in relations]


@router.post("/relations")
def create_relation(data: RelationCreate, db: Session = Depends(get_db)):
    relation = DataRelation(**data.model_dump())
    db.add(relation)
    db.commit()
    db.refresh(relation)
    return relation.to_dict()


@router.delete("/relations/{id}")
def delete_relation(id: str, db: Session = Depends(get_db)):
    relation = db.query(DataRelation).filter(DataRelation.id == id).first()
    if not relation:
        raise HTTPException(status_code=404, detail="Relation not found")
    db.delete(relation)
    db.commit()
    return {"message": "Deleted successfully"}


# ============ Lineage Routes ============
@router.get("/lineage/metric/{id}")
def get_metric_lineage(id: str, db: Session = Depends(get_db)):
    metric = db.query(Metric).filter(Metric.id == id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    upstream = []
    downstream = []
    
    # Build upstream lineage
    if metric.dataset_id:
        dataset = db.query(Dataset).filter(Dataset.id == metric.dataset_id).first()
        if dataset:
            upstream.append({
                "id": dataset.id,
                "name": dataset.name,
                "type": "dataset",
                "level": 1
            })
            
            if dataset.datasource_id:
                datasource = db.query(DataSource).filter(DataSource.id == dataset.datasource_id).first()
                if datasource:
                    upstream.append({
                        "id": datasource.id,
                        "name": datasource.name,
                        "type": "datasource",
                        "level": 2
                    })
    
    # For derived/composite metrics, find referenced metrics in formula
    if metric.calculation_formula:
        from app.utils.mql_validator import MQLValidator
        validator = MQLValidator(db)
        referenced_metric_names = validator.extract_referenced_metrics(metric.calculation_formula)
        
        for ref_name in referenced_metric_names:
            ref_metric = db.query(Metric).filter(Metric.name == ref_name).first()
            if ref_metric:
                upstream.append({
                    "id": ref_metric.id,
                    "name": ref_metric.name,
                    "type": "metric",
                    "metric_type": ref_metric.metric_type,
                    "level": 1
                })
    
    # Find metrics that reference this metric
    all_metrics = db.query(Metric).filter(Metric.calculation_formula.isnot(None)).all()
    for m in all_metrics:
        if m.calculation_formula and metric.name in m.calculation_formula:
            downstream.append({
                "id": m.id,
                "name": m.name,
                "type": "metric",
                "metric_type": m.metric_type,
                "level": -1
            })
    
    return {
        "metric": metric.to_dict(),
        "upstream": upstream,
        "downstream": downstream
    }


@router.get("/lineage/dataset/{id}")
def get_dataset_lineage(id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    upstream = []
    downstream = []
    
    # Build upstream: datasource
    if dataset.datasource_id:
        datasource = db.query(DataSource).filter(DataSource.id == dataset.datasource_id).first()
        if datasource:
            upstream.append({
                "id": datasource.id,
                "name": datasource.name,
                "type": "datasource",
                "level": 1
            })
    
    # Find related datasets through relations (as left or right dataset)
    left_relations = db.query(DataRelation).filter(DataRelation.left_dataset_id == id).all()
    right_relations = db.query(DataRelation).filter(DataRelation.right_dataset_id == id).all()
    
    for rel in left_relations:
        related = db.query(Dataset).filter(Dataset.id == rel.right_dataset_id).first()
        if related:
            upstream.append({
                "id": related.id,
                "name": related.name,
                "type": "dataset",
                "relation_type": rel.join_type,
                "level": 0
            })
    
    for rel in right_relations:
        related = db.query(Dataset).filter(Dataset.id == rel.left_dataset_id).first()
        if related:
            upstream.append({
                "id": related.id,
                "name": related.name,
                "type": "dataset",
                "relation_type": rel.join_type,
                "level": 0
            })
    
    # Build downstream: metrics and dimensions that use this dataset
    metrics = db.query(Metric).filter(Metric.dataset_id == id).all()
    for metric in metrics:
        downstream.append({
            "id": metric.id,
            "name": metric.name,
            "type": "metric",
            "metric_type": metric.metric_type,
            "level": -1
        })
    
    dimensions = db.query(Dimension).filter(Dimension.dataset_id == id).all()
    for dim in dimensions:
        downstream.append({
            "id": dim.id,
            "name": dim.name,
            "type": "dimension",
            "dimension_type": dim.dimension_type,
            "level": -1
        })
    
    return {
        "dataset": dataset.to_dict(),
        "upstream": upstream,
        "downstream": downstream
    }


@router.get("/metrics/{id}/allowed-dimensions")
def get_metric_allowed_dimensions(id: str, db: Session = Depends(get_db)):
    """获取指标允许的维度列表（基于analysis_dimensions约束）"""
    metric = db.query(Metric).filter(Metric.id == id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="指标不存在")
    
    # 获取指标配置的允许维度ID列表
    allowed_dim_ids = metric.analysis_dimensions or []
    
    # 查询这些维度的详细信息
    if allowed_dim_ids:
        dimensions = db.query(Dimension).filter(Dimension.id.in_(allowed_dim_ids)).all()
    else:
        # 如果未配置约束，返回所有维度
        dimensions = db.query(Dimension).all()
    
    return [
        {
            "id": dim.id,
            "name": dim.name,
            "display_name": dim.display_name,
            "physical_column": dim.physical_column,
            "dimension_type": dim.dimension_type,
            "data_type": dim.data_type,
            "format_config": dim.format_config
        }
        for dim in dimensions
    ]


@router.post("/metrics/allowed-dimensions")
def get_metrics_allowed_dimensions(metric_ids: List[str], db: Session = Depends(get_db)):
    """获取多个指标的交集维度（用于问数流程的维度约束）
    
    返回所有选中指标都允许的维度交集
    """
    if not metric_ids:
        return []
    
    # 查询所有相关指标
    metrics = db.query(Metric).filter(Metric.id.in_(metric_ids)).all()
    if not metrics:
        return []
    
    # 获取每个指标的允许维度集合
    metric_dim_sets = []
    for metric in metrics:
        allowed_ids = set(metric.analysis_dimensions or [])
        metric_dim_sets.append(allowed_ids)
    
    # 计算交集
    if len(metric_dim_sets) == 1:
        # 只有一个指标，返回其所有允许维度
        common_dim_ids = metric_dim_sets[0]
    else:
        # 多个指标，取交集
        common_dim_ids = set.intersection(*metric_dim_sets)
    
    # 查询交集维度的详细信息
    if common_dim_ids:
        dimensions = db.query(Dimension).filter(Dimension.id.in_(common_dim_ids)).all()
    else:
        # 无交集，返回空列表
        dimensions = []
    
    return [
        {
            "id": dim.id,
            "name": dim.name,
            "display_name": dim.display_name,
            "physical_column": dim.physical_column,
            "dimension_type": dim.dimension_type,
            "data_type": dim.data_type,
            "format_config": dim.format_config
        }
        for dim in dimensions
    ]


@router.get("/lineage/graph")
def get_full_lineage_graph(db: Session = Depends(get_db)):
    """获取完整的血缘关系图：数据源 → 物理表 → 视图 → 维度/指标"""
    nodes = []
    edges = []
    
    # Add all datasources as nodes (category 0)
    datasources = db.query(DataSource).all()
    for ds in datasources:
        nodes.append({
            "id": ds.id,
            "name": ds.name,
            "type": "datasource",
            "category": 0
        })
    
    # Add all datasets (physical tables) as nodes (category 1)
    datasets = db.query(Dataset).all()
    dataset_map = {d.id: d for d in datasets}
    for dataset in datasets:
        nodes.append({
            "id": dataset.id,
            "name": dataset.name,
            "type": "dataset",
            "category": 1,
            "physical_name": dataset.physical_name
        })
        if dataset.datasource_id:
            edges.append({
                "source": dataset.datasource_id,
                "target": dataset.id,
                "type": "contains"
            })
    
    # Add all views as nodes (category 2) and edges from datasets
    views = db.query(View).all()
    for view in views:
        nodes.append({
            "id": view.id,
            "name": view.name,
            "type": "view",
            "view_type": view.view_type,
            "category": 2
        })
        
        # Link view to its source tables
        if view.view_type == "single_table" and view.base_table_id:
            edges.append({
                "source": view.base_table_id,
                "target": view.id,
                "type": "source"
            })
        elif view.view_type == "joined" and view.join_config:
            # Add edges from all tables in join config
            tables = view.join_config.get("tables", [])
            for t in tables:
                if t.get("datasetId") in dataset_map:
                    edges.append({
                        "source": t["datasetId"],
                        "target": view.id,
                        "type": "source"
                    })
    
    # Add all metrics as nodes (category 3)
    metrics = db.query(Metric).all()
    for metric in metrics:
        nodes.append({
            "id": metric.id,
            "name": metric.name,
            "type": "metric",
            "metric_type": metric.metric_type,
            "category": 3
        })
        # Priority: view_id > dataset_id
        if metric.view_id:
            edges.append({
                "source": metric.view_id,
                "target": metric.id,
                "type": "derives"
            })
        elif metric.dataset_id:
            edges.append({
                "source": metric.dataset_id,
                "target": metric.id,
                "type": "derives"
            })
        
        # Add edges between metrics (derived/composite)
        if metric.calculation_formula:
            from app.utils.mql_validator import MQLValidator
            validator = MQLValidator(db)
            referenced_metrics = validator.extract_referenced_metrics(metric.calculation_formula)
            for ref_name in referenced_metrics:
                ref_metric = db.query(Metric).filter(Metric.name == ref_name).first()
                if ref_metric:
                    edges.append({
                        "source": ref_metric.id,
                        "target": metric.id,
                        "type": "uses"
                    })
    
    # Add all dimensions as nodes (category 4)
    dimensions = db.query(Dimension).all()
    for dim in dimensions:
        nodes.append({
            "id": dim.id,
            "name": dim.name,
            "type": "dimension",
            "dimension_type": dim.dimension_type,
            "category": 4
        })
        # Priority: view_id > dataset_id
        if dim.view_id:
            edges.append({
                "source": dim.view_id,
                "target": dim.id,
                "type": "defines"
            })
        elif dim.dataset_id:
            edges.append({
                "source": dim.dataset_id,
                "target": dim.id,
                "type": "defines"
            })
    
    return {"nodes": nodes, "edges": edges}
