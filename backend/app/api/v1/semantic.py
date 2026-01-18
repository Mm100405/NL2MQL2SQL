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
    dataset_id: Optional[str] = None
    aggregation: Optional[str] = None
    measure_column: Optional[str] = None
    calculation_formula: Optional[str] = None
    filters: Optional[List[dict]] = None
    synonyms: Optional[List[str]] = None
    unit: Optional[str] = None
    description: Optional[str] = None


class DimensionCreate(BaseModel):
    dataset_id: str
    name: str
    display_name: Optional[str] = None
    physical_column: str
    data_type: str = "string"
    dimension_type: str = "normal"
    hierarchy: Optional[dict] = None
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
        elif source.type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(source.connection_config["database"])
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
                    SELECT column_name, data_type, is_nullable, 
                           col_description((table_schema||'.'||table_name)::regclass::oid, ordinal_position)
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = %s
                    ORDER BY ordinal_position
                """, (table_name, schema_name))
                columns = [
                    {
                        "name": col[0],
                        "type": col[1],
                        "nullable": col[2] == "YES",
                        "comment": col[3] or ""
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
            
        elif datasource.type == "sqlite":
            import sqlite3
            conn = sqlite3.connect(datasource.connection_config["database"])
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for (table_name,) in cursor.fetchall():
                cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns = [
                    {
                        "name": col[1],
                        "type": col[2],
                        "nullable": col[3] == 0,
                        "comment": ""
                    }
                    for col in cursor.fetchall()
                ]
                tables.append({"name": table_name, "schema": "main", "columns": columns})
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


@router.post("/metrics")
def create_metric(data: MetricCreate, db: Session = Depends(get_db)):
    metric = Metric(**data.model_dump())
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric.to_dict()


@router.put("/metrics/{id}")
def update_metric(id: str, data: dict, db: Session = Depends(get_db)):
    metric = db.query(Metric).filter(Metric.id == id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")
    
    for key, value in data.items():
        if hasattr(metric, key):
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
def get_dimensions(dataset_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Dimension)
    if dataset_id:
        query = query.filter(Dimension.dataset_id == dataset_id)
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
    dimension = Dimension(**data.model_dump())
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


@router.get("/lineage/graph")
def get_full_lineage_graph(db: Session = Depends(get_db)):
    nodes = []
    edges = []
    
    # Add all datasources as nodes
    datasources = db.query(DataSource).all()
    for ds in datasources:
        nodes.append({
            "id": ds.id,
            "name": ds.name,
            "type": "datasource",
            "category": 0
        })
    
    # Add all datasets as nodes and edges from datasources
    datasets = db.query(Dataset).all()
    for dataset in datasets:
        nodes.append({
            "id": dataset.id,
            "name": dataset.name,
            "type": "dataset",
            "category": 1
        })
        if dataset.datasource_id:
            edges.append({
                "source": dataset.datasource_id,
                "target": dataset.id,
                "type": "contains"
            })
    
    # Add dataset relations
    relations = db.query(DataRelation).all()
    for rel in relations:
        edges.append({
            "source": rel.left_dataset_id,
            "target": rel.right_dataset_id,
            "type": "join",
            "join_type": rel.join_type
        })
    
    # Add all metrics as nodes and edges from datasets
    metrics = db.query(Metric).all()
    for metric in metrics:
        nodes.append({
            "id": metric.id,
            "name": metric.name,
            "type": "metric",
            "metric_type": metric.metric_type,
            "category": 2
        })
        if metric.dataset_id:
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
    
    # Add all dimensions as nodes and edges from datasets
    dimensions = db.query(Dimension).all()
    for dim in dimensions:
        nodes.append({
            "id": dim.id,
            "name": dim.name,
            "type": "dimension",
            "dimension_type": dim.dimension_type,
            "category": 3
        })
        if dim.dataset_id:
            edges.append({
                "source": dim.dataset_id,
                "target": dim.id,
                "type": "defines"
            })
    
    return {"nodes": nodes, "edges": edges}
