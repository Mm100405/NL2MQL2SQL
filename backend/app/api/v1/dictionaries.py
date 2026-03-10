"""Field Dictionary Management API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.field_dict import FieldDictionary, DictSourceType
from app.models.view import View
from app.models.dataset import Dataset
from app.models.datasource import DataSource
from app.services.query_executor import execute_query

router = APIRouter()


# ============ Schemas ============
class DictMapping(BaseModel):
    value: str
    label: str
    synonyms: Optional[List[str]] = None


class DictionaryCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    source_type: str = DictSourceType.MANUAL
    mappings: Optional[List[dict]] = None
    ref_view_id: Optional[str] = None
    ref_value_column: Optional[str] = None
    ref_label_column: Optional[str] = None
    auto_source_dataset_id: Optional[str] = None
    auto_source_column: Optional[str] = None
    auto_filters: Optional[List[dict]] = None
    description: Optional[str] = None


class DictionaryUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    source_type: Optional[str] = None
    mappings: Optional[List[dict]] = None
    ref_view_id: Optional[str] = None
    ref_value_column: Optional[str] = None
    ref_label_column: Optional[str] = None
    auto_source_dataset_id: Optional[str] = None
    auto_source_column: Optional[str] = None
    auto_filters: Optional[List[dict]] = None
    description: Optional[str] = None


class AutoGenerateRequest(BaseModel):
    datasource_id: str
    dataset_id: str
    column_name: str
    dictionary_name: str
    filters: Optional[List[dict]] = None
    limit: int = 1000


# ============ Routes ============
@router.get("")
def get_dictionaries(source_type: Optional[str] = None, db: Session = Depends(get_db)):
    """获取字典列表"""
    query = db.query(FieldDictionary)
    if source_type:
        query = query.filter(FieldDictionary.source_type == source_type)
    dictionaries = query.order_by(FieldDictionary.created_at.desc()).all()
    return [d.to_dict() for d in dictionaries]


@router.get("/{id}")
def get_dictionary(id: str, db: Session = Depends(get_db)):
    """获取单个字典详情"""
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    return dictionary.to_dict()


@router.post("")
def create_dictionary(data: DictionaryCreate, db: Session = Depends(get_db)):
    """创建字典"""
    # 检查名称是否重复
    existing = db.query(FieldDictionary).filter(FieldDictionary.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Dictionary name '{data.name}' already exists")
    
    # 验证引用配置
    if data.source_type == DictSourceType.VIEW_REF:
        if not data.ref_view_id:
            raise HTTPException(status_code=400, detail="ref_view_id is required for view_ref dictionary")
        view = db.query(View).filter(View.id == data.ref_view_id).first()
        if not view:
            raise HTTPException(status_code=404, detail="Referenced view not found")
    
    if data.source_type == DictSourceType.AUTO:
        if not data.auto_source_dataset_id or not data.auto_source_column:
            raise HTTPException(status_code=400, detail="auto_source_dataset_id and auto_source_column are required for auto dictionary")
    
    # 将空字符串转换为 None，避免外键约束问题
    def _empty_to_none(val):
        return val if val else None

    dictionary = FieldDictionary(
        name=data.name,
        display_name=data.display_name,
        source_type=data.source_type,
        mappings=data.mappings,
        ref_view_id=_empty_to_none(data.ref_view_id),
        ref_value_column=_empty_to_none(data.ref_value_column),
        ref_label_column=_empty_to_none(data.ref_label_column),
        auto_source_dataset_id=_empty_to_none(data.auto_source_dataset_id),
        auto_source_column=_empty_to_none(data.auto_source_column),
        auto_filters=data.auto_filters if data.auto_filters else None,
        description=data.description
    )
    db.add(dictionary)
    db.commit()
    db.refresh(dictionary)
    return dictionary.to_dict()


@router.put("/{id}")
def update_dictionary(id: str, data: DictionaryUpdate, db: Session = Depends(get_db)):
    """更新字典"""
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    # 检查名称是否重复
    if data.name and data.name != dictionary.name:
        existing = db.query(FieldDictionary).filter(FieldDictionary.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Dictionary name '{data.name}' already exists")
    
    update_data = data.model_dump(exclude_unset=True)
    # 将空字符串转换为 None，避免外键约束问题
    for key, value in update_data.items():
        if value == '':
            value = None
        # 处理空数组转为 None（auto_filters）
        if key == 'auto_filters' and (value == [] or value == None):
            value = None
        setattr(dictionary, key, value)
    
    db.commit()
    db.refresh(dictionary)
    return dictionary.to_dict()


@router.delete("/{id}")
def delete_dictionary(id: str, db: Session = Depends(get_db)):
    """删除字典"""
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    db.delete(dictionary)
    db.commit()
    return {"message": "Deleted successfully"}


@router.get("/{id}/values")
async def get_dictionary_values(id: str, db: Session = Depends(get_db)):
    """
    获取字典值列表
    - 对于手动配置的字典，直接返回mappings
    - 对于引用视图的字典，动态查询视图数据
    - 对于自动生成的字典，返回缓存的mappings
    """
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    if dictionary.source_type == DictSourceType.MANUAL:
        return {
            "source_type": dictionary.source_type,
            "values": dictionary.mappings or []
        }
    
    elif dictionary.source_type == DictSourceType.VIEW_REF:
        # 动态查询引用视图
        if not dictionary.ref_view_id:
            return {"source_type": dictionary.source_type, "values": []}
        
        view = db.query(View).filter(View.id == dictionary.ref_view_id).first()
        if not view:
            return {"source_type": dictionary.source_type, "values": []}
        
        value_col = dictionary.ref_value_column or "value"
        label_col = dictionary.ref_label_column or value_col
        
        datasets = {d.id: d for d in db.query(Dataset).all()}
        from_clause = view.generate_from_clause(datasets)
        
        sql = f"SELECT DISTINCT {value_col} AS value, {label_col} AS label FROM {from_clause} WHERE {value_col} IS NOT NULL LIMIT 1000"
        
        try:
            result = await execute_query(
                sql=sql,
                datasource_id=view.datasource_id,
                limit=1000,
                db=db
            )
            values = []
            for row in result.get("data", []):
                values.append({
                    "value": str(row[0]) if row[0] is not None else "",
                    "label": str(row[1]) if len(row) > 1 and row[1] is not None else str(row[0]) if row[0] is not None else ""
                })
            return {"source_type": dictionary.source_type, "values": values}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to query view: {str(e)}")
    
    elif dictionary.source_type == DictSourceType.AUTO:
        return {
            "source_type": dictionary.source_type,
            "values": dictionary.mappings or [],
            "last_sync": dictionary.auto_last_sync.isoformat() if dictionary.auto_last_sync else None
        }
    
    return {"source_type": dictionary.source_type, "values": []}


@router.post("/auto-generate")
async def auto_generate_dictionary(request: AutoGenerateRequest, db: Session = Depends(get_db)):
    """
    从表字段自动生成去重值列表
    """
    # 验证数据集
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # 验证字段存在
    column_exists = False
    if dataset.columns:
        for col in dataset.columns:
            if col.get("name") == request.column_name:
                column_exists = True
                break
    if not column_exists:
        raise HTTPException(status_code=400, detail=f"Column '{request.column_name}' not found in dataset")
    
    # 构建过滤条件
    where_conditions = [f"`{request.column_name}` IS NOT NULL"]
    
    # 添加用户配置的过滤条件
    filters = request.filters or []
    for filter_item in filters:
        column = filter_item.get("column", "")
        operator = filter_item.get("operator", "=")
        value = filter_item.get("value", "")
        
        if column and operator and value:
            if operator == "IN":
                values = [f"'{v.strip()}'" for v in value.split(",") if v.strip()]
                if values:
                    where_conditions.append(f"`{column}` IN ({', '.join(values)})")
            elif operator == "LIKE":
                where_conditions.append(f"`{column}` LIKE '%{value}%'")
            elif operator in ["IS NULL", "IS NOT NULL"]:
                where_conditions.append(f"`{column}` {operator}")
            else:
                where_conditions.append(f"`{column}` {operator} '{value}'")
    
    where_clause = " AND ".join(where_conditions)
    
    # 查询去重值
    sql = f"SELECT DISTINCT `{request.column_name}` AS value FROM {dataset.physical_name} WHERE {where_clause} LIMIT {request.limit}"
    
    try:
        result = await execute_query(
            sql=sql,
            datasource_id=request.datasource_id,
            limit=request.limit,
            db=db
        )
        
        # 生成mappings
        mappings = []
        for row in result.get("data", []):
            value = str(row[0]) if row[0] is not None else ""
            if value:
                mappings.append({
                    "value": value,
                    "label": value,
                    "synonyms": []
                })
        
        # 检查是否已有同名字典
        existing = db.query(FieldDictionary).filter(FieldDictionary.name == request.dictionary_name).first()
        
        if existing:
            # 更新现有字典
            existing.mappings = mappings
            existing.auto_last_sync = datetime.utcnow()
            if request.filters:
                existing.auto_filters = request.filters
            db.commit()
            db.refresh(existing)
            return existing.to_dict()
        else:
            # 创建新字典
            dictionary = FieldDictionary(
                name=request.dictionary_name,
                display_name=request.dictionary_name,
                source_type=DictSourceType.AUTO,
                mappings=mappings,
                auto_source_dataset_id=request.dataset_id,
                auto_source_column=request.column_name,
                auto_filters=request.filters or [],
                auto_last_sync=datetime.utcnow()
            )
            db.add(dictionary)
            db.commit()
            db.refresh(dictionary)
            return dictionary.to_dict()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dictionary: {str(e)}")


@router.post("/{id}/sync")
async def sync_dictionary(id: str, db: Session = Depends(get_db)):
    """
    同步自动生成类型的字典
    """
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    if dictionary.source_type != DictSourceType.AUTO:
        raise HTTPException(status_code=400, detail="Only auto-generated dictionaries can be synced")
    
    if not dictionary.auto_source_dataset_id or not dictionary.auto_source_column:
        raise HTTPException(status_code=400, detail="Dictionary missing auto-generate configuration")
    
    dataset = db.query(Dataset).filter(Dataset.id == dictionary.auto_source_dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Source dataset not found")
    
    # 构建过滤条件
    where_conditions = [f"`{dictionary.auto_source_column}` IS NOT NULL"]
    
    # 添加用户配置的过滤条件
    auto_filters = dictionary.auto_filters or []
    for filter_item in auto_filters:
        column = filter_item.get("column", "")
        operator = filter_item.get("operator", "=")
        value = filter_item.get("value", "")
        
        if column and operator and value:
            # 处理特殊操作符
            if operator == "IN":
                values = [f"'{v.strip()}'" for v in value.split(",") if v.strip()]
                if values:
                    where_conditions.append(f"`{column}` IN ({', '.join(values)})")
            elif operator == "LIKE":
                where_conditions.append(f"`{column}` LIKE '%{value}%'")
            elif operator in ["IS NULL", "IS NOT NULL"]:
                where_conditions.append(f"`{column}` {operator}")
            else:
                where_conditions.append(f"`{column}` {operator} '{value}'")
    
    where_clause = " AND ".join(where_conditions)
    
    # 查询去重值
    sql = f"SELECT DISTINCT `{dictionary.auto_source_column}` AS value FROM {dataset.physical_name} WHERE {where_clause} LIMIT 1000"
    
    try:
        result = await execute_query(
            sql=sql,
            datasource_id=dataset.datasource_id,
            limit=1000,
            db=db
        )
        
        # 更新mappings
        mappings = []
        for row in result.get("data", []):
            value = str(row[0]) if row[0] is not None else ""
            if value:
                # 保留原有的synonyms
                old_mapping = next((m for m in (dictionary.mappings or []) if m.get("value") == value), None)
                synonyms = old_mapping.get("synonyms", []) if old_mapping else []
                label = old_mapping.get("label", value) if old_mapping else value
                mappings.append({
                    "value": value,
                    "label": label,
                    "synonyms": synonyms
                })
        
        dictionary.mappings = mappings
        dictionary.auto_last_sync = datetime.utcnow()
        db.commit()
        db.refresh(dictionary)
        
        return dictionary.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync dictionary: {str(e)}")


@router.post("/{id}/mappings")
def add_mapping(id: str, mapping: DictMapping, db: Session = Depends(get_db)):
    """添加字典映射项"""
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    if not dictionary.mappings:
        dictionary.mappings = []
    
    # 检查是否已存在
    for m in dictionary.mappings:
        if m.get("value") == mapping.value:
            raise HTTPException(status_code=400, detail=f"Value '{mapping.value}' already exists")
    
    dictionary.mappings.append({
        "value": mapping.value,
        "label": mapping.label,
        "synonyms": mapping.synonyms or []
    })
    
    db.commit()
    db.refresh(dictionary)
    return dictionary.to_dict()


@router.delete("/{id}/mappings/{value}")
def delete_mapping(id: str, value: str, db: Session = Depends(get_db)):
    """删除字典映射项"""
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    if not dictionary.mappings:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    original_len = len(dictionary.mappings)
    dictionary.mappings = [m for m in dictionary.mappings if m.get("value") != value]
    
    if len(dictionary.mappings) == original_len:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    db.commit()
    db.refresh(dictionary)
    return dictionary.to_dict()


# ============ NL 解析支持接口 ============
class ResolveValueRequest(BaseModel):
    """值解析请求"""
    label: str


class BatchResolveRequest(BaseModel):
    """批量值解析请求"""
    labels: List[str]


@router.post("/{id}/resolve-value")
def resolve_value(id: str, request: ResolveValueRequest, db: Session = Depends(get_db)):
    """
    根据标签或同义词解析实际值
    
    用于自然语言解析时，将用户输入的标签词转换为实际值
    例如：用户说"线上"，解析为 "ONLINE"
    """
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")
    
    actual_value = dictionary.get_value_from_label(request.label)
    
    return {
        "dict_id": id,
        "input": request.label,
        "resolved_value": actual_value,
        "found": actual_value != request.label
    }


@router.post("/{id}/batch-resolve")
def batch_resolve_values(id: str, request: BatchResolveRequest, db: Session = Depends(get_db)):
    """
    批量解析值
    
    用于自然语言解析时，批量将用户输入的标签词转换为实际值
    """
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")
    
    results = []
    for label in request.labels:
        actual_value = dictionary.get_value_from_label(label)
        results.append({
            "input": label,
            "resolved_value": actual_value,
            "found": actual_value != label
        })
    
    return {
        "dict_id": id,
        "results": results
    }


@router.get("/{id}/labels")
def get_dictionary_labels(id: str, db: Session = Depends(get_db)):
    """
    获取字典的所有标签（用于 NL 提示）
    
    返回所有 label 和 synonyms，供 LLM 作为可选值提示
    """
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == id).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail="字典不存在")
    
    labels = set()
    if dictionary.mappings:
        for m in dictionary.mappings:
            if m.get("label"):
                labels.add(m.get("label"))
            # 添加同义词
            for syn in (m.get("synonyms") or []):
                labels.add(syn)
    
    return {
        "dict_id": id,
        "dict_name": dictionary.name,
        "labels": sorted(list(labels))
    }


@router.get("/by-name/{name}")
def get_dictionary_by_name(name: str, db: Session = Depends(get_db)):
    """根据字典名称获取字典（用于内部调用）"""
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.name == name).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail=f"字典 '{name}' 不存在")
    return dictionary.to_dict()


@router.post("/by-name/{name}/resolve")
def resolve_by_dict_name(name: str, request: ResolveValueRequest, db: Session = Depends(get_db)):
    """根据字典名称解析值（用于内部调用）"""
    dictionary = db.query(FieldDictionary).filter(FieldDictionary.name == name).first()
    if not dictionary:
        raise HTTPException(status_code=404, detail=f"字典 '{name}' 不存在")
    
    actual_value = dictionary.get_value_from_label(request.label)
    
    return {
        "dict_name": name,
        "input": request.label,
        "resolved_value": actual_value,
        "found": actual_value != request.label
    }
