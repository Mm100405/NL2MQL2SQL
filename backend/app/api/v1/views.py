"""View Management API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.view import View, ViewType
from app.models.view_category import ViewCategory
from app.models.dataset import Dataset
from app.models.datasource import DataSource
from app.services.query_executor import execute_query

router = APIRouter()


# ============ 分类 Schemas ============
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None


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
    category_id: Optional[str] = None
    category_name: Optional[str] = None
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
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    view_type: Optional[str] = None
    base_table_id: Optional[str] = None
    join_config: Optional[dict] = None
    custom_sql: Optional[str] = None
    columns: Optional[List[dict]] = None
    canvas_config: Optional[dict] = None
    description: Optional[str] = None


class PreviewRequest(BaseModel):
    limit: int = 100
    page: int = 1
    page_size: int = 10


# ============ Routes ============
# ============ 分类路由（必须在视图路由之前）============

@router.get("/categories/stats")
def get_category_stats(datasource_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    获取视图分类统计

    返回格式：
    {
        "categories": [
            {"category_id": "xxx", "category_name": "xxx", "view_count": 10},
            {"category_id": None, "category_name": "未分类", "view_count": 5}
        ]
    }
    """
    query = db.query(View)
    if datasource_id:
        query = query.filter(View.datasource_id == datasource_id)

    # 按分类分组统计
    from sqlalchemy import func
    category_stats = db.query(
        View.category_id,
        View.category_name,
        func.count(View.id).label("count")
    ).filter(
        View.datasource_id == datasource_id if datasource_id else True
    ).group_by(View.category_id, View.category_name).all()

    # 转换为响应格式
    categories = []
    for category_id, category_name, count in category_stats:
        cat_name = category_name or "未分类"
        categories.append({
            "category_id": category_id,
            "category_name": cat_name,
            "view_count": count
        })

    # 按视图数量降序排序
    categories.sort(key=lambda x: x["view_count"], reverse=True)

    return {"categories": categories}


# ============ 分类管理接口 ============
@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取所有分类"""
    categories = db.query(ViewCategory).order_by(ViewCategory.name).all()
    return [cat.to_dict() for cat in categories]


@router.get("/categories/tree")
def get_category_tree(db: Session = Depends(get_db)):
    """获取分类树结构"""
    categories = db.query(ViewCategory).all()

    # 构建分类映射，转换为前端 a-tree 组件需要的格式
    cat_map = {cat.id: {
        "key": cat.id,
        "title": cat.name,
        "description": cat.description,
        "parent_id": cat.parent_id,
        "created_at": cat.created_at.isoformat() if cat.created_at else None,
        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
        "children": []
    } for cat in categories}

    # 构建树结构
    tree = []
    for cat_id, cat_data in cat_map.items():
        parent_id = cat_data["parent_id"]
        if parent_id and parent_id in cat_map:
            cat_map[parent_id]["children"].append(cat_data)
        else:
            tree.append(cat_data)

    return tree


@router.get("/categories/{id}")
def get_category(id: str, db: Session = Depends(get_db)):
    """获取单个分类详情"""
    category = db.query(ViewCategory).filter(ViewCategory.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category.to_dict()


@router.post("/categories")
def create_category(data: CategoryCreate, db: Session = Depends(get_db)):
    """创建新分类"""
    # 检查名称是否重复
    existing = db.query(ViewCategory).filter(ViewCategory.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Category name '{data.name}' already exists")
    
    # 如果有父分类，验证父分类存在
    if data.parent_id:
        parent = db.query(ViewCategory).filter(ViewCategory.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
    
    category = ViewCategory(
        name=data.name,
        description=data.description,
        parent_id=data.parent_id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category.to_dict()


@router.put("/categories/{id}")
def update_category(id: str, data: CategoryUpdate, db: Session = Depends(get_db)):
    """更新分类"""
    category = db.query(ViewCategory).filter(ViewCategory.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 检查名称是否重复
    if data.name and data.name != category.name:
        existing = db.query(ViewCategory).filter(ViewCategory.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Category name '{data.name}' already exists")
    
    # 验证父分类存在且不是自己
    if data.parent_id is not None:
        if data.parent_id == id:
            raise HTTPException(status_code=400, detail="Cannot set category as its own parent")
        parent = db.query(ViewCategory).filter(ViewCategory.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    
    db.commit()
    db.refresh(category)
    return category.to_dict()


@router.delete("/categories/{id}")
def delete_category(id: str, db: Session = Depends(get_db)):
    """删除分类"""
    category = db.query(ViewCategory).filter(ViewCategory.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # 检查是否有视图使用此分类
    view_count = db.query(View).filter(View.category_id == id).count()
    if view_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category: {view_count} views are using this category"
        )
    
    # 检查是否有子分类
    child_count = db.query(ViewCategory).filter(ViewCategory.parent_id == id).count()
    if child_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete category: {child_count} child categories exist"
        )
    
    db.delete(category)
    db.commit()
    return {"message": "Deleted successfully"}


# ============ 视图路由 ============
@router.get("")
def get_views(
    datasource_id: Optional[str] = None,
    category_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取视图列表（支持按数据源和分类筛选）"""
    query = db.query(View)
    if datasource_id:
        query = query.filter(View.datasource_id == datasource_id)
    if category_id:
        query = query.filter(View.category_id == category_id)
    views = query.order_by(View.created_at.desc()).all()
    return [v.to_dict() for v in views]


@router.get("/default")
def get_default_view(db: Session = Depends(get_db)):
    """获取默认视图"""
    view = db.query(View).filter(View.is_default == True).first()
    if not view:
        # 如果没有默认视图，返回第一个视图
        view = db.query(View).first()
    if not view:
        return None
    return view.to_dict()


@router.put("/{id}/default")
def set_default_view(id: str, db: Session = Depends(get_db)):
    """设置默认视图"""
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # 清除其他视图的默认标记
    db.query(View).filter(View.is_default == True).update({"is_default": False})
    
    # 设置当前视图为默认
    view.is_default = True
    db.commit()
    db.refresh(view)
    return view.to_dict()


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
        category_id=data.category_id,
        category_name=data.category_name,
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
    """预览视图数据（支持分页）"""
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
            # SQL视图类型：FROM子句是子查询，不能使用内层表别名
            if view.view_type == ViewType.SQL or not source_table:
                select_columns.append(f"{source_column} AS {alias}")
            else:
                select_columns.append(f"{source_table}.{source_column} AS {alias}")
        select_clause = ", ".join(select_columns)
    else:
        select_clause = "*"
    
    # 计算分页偏移量
    page = request.page if request.page > 0 else 1
    page_size = request.page_size if request.page_size > 0 else 10
    offset = (page - 1) * page_size
    
    # 构建分页SQL
    sql = f"SELECT {select_clause} FROM {from_clause} LIMIT {page_size} OFFSET {offset}"
    
    try:
        # 执行分页查询
        result = await execute_query(
            sql=sql,
            datasource_id=view.datasource_id,
            limit=page_size,
            db=db
        )
        
        # 获取总数 - 构建COUNT查询
        count_sql = f"SELECT COUNT(*) as total FROM {from_clause}"
        count_result = await execute_query(
            sql=count_sql,
            datasource_id=view.datasource_id,
            limit=1,
            db=db
        )
        
        # 提取总数
        total_count = 0
        if count_result.get("data") and len(count_result["data"]) > 0:
            total_count = count_result["data"][0][0]
        
        return {
            "sql": sql,
            "columns": result.get("columns", []),
            "data": result.get("data", []),
            "total": total_count,
            "page": page,
            "page_size": page_size
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
            # SQL视图类型：FROM子句是子查询，不能使用内层表别名
            if view.view_type == ViewType.SQL or not source_table:
                select_columns.append(f"{source_column} AS {alias}")
            else:
                select_columns.append(f"{source_table}.{source_column} AS {alias}")
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


# ============ 字段管理接口（用于 filters 增强） ============
class ViewColumnUpdate(BaseModel):
    """视图字段更新"""
    columns: List[dict]


class ColumnValueConfig(BaseModel):
    """字段值域配置"""
    type: str = "none"  # none | enum | range | dict | sql
    enum_values: Optional[List[str]] = None
    range: Optional[dict] = None
    dict_id: Optional[str] = None
    sql_expression: Optional[str] = None
    value_column: Optional[str] = None
    label_column: Optional[str] = None


class ColumnConfig(BaseModel):
    """单个字段配置"""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    value_config: Optional[ColumnValueConfig] = None
    filterable: Optional[bool] = True
    filter_operators: Optional[List[str]] = None
    synonyms: Optional[List[str]] = None


@router.get("/{id}/filterable-fields")
def get_filterable_fields(id: str, db: Session = Depends(get_db)):
    """
    获取视图可过滤字段列表
    
    用于 NL 解析和前端过滤器配置，返回所有可过滤字段及其值域配置
    """
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    from app.models.field_dict import FieldDictionary
    
    filterable_fields = []
    time_type_keywords = ["date", "time", "datetime", "timestamp"]
    
    # 获取视图的列配置
    if view.columns:
        for col in view.columns:
            if col.get("filterable", True):  # 默认可过滤
                field_type = col.get("type", "").lower()
                # 判断是否为时间字段
                is_time_field = any(keyword in field_type for keyword in time_type_keywords)
                
                field_info = {
                    "name": col.get("name"),
                    "display_name": col.get("display_name") or col.get("name"),
                    "description": col.get("description") or col.get("default_comment", ""),
                    "type": col.get("type"),
                    "value_config": col.get("value_config", {"type": "none"}),
                    "filter_operators": col.get("filter_operators", ["=", "!=", "IN", "NOT IN"]),
                    "synonyms": col.get("synonyms", []),
                    "is_time_field": is_time_field  # 标记是否为时间字段
                }
                
                # 如果有字典，获取字典信息
                dict_id = col.get("value_config", {}).get("dict_id") if col.get("value_config") else None
                if dict_id:
                    dictionary = db.query(FieldDictionary).filter(
                        FieldDictionary.id == dict_id
                    ).first()
                    if dictionary:
                        field_info["dict_info"] = {
                            "id": dictionary.id,
                            "name": dictionary.name,
                            "display_name": dictionary.display_name,
                            "source_type": dictionary.source_type
                        }
                
                filterable_fields.append(field_info)
    
    return {
        "view_id": id,
        "view_name": view.name,
        "view_display_name": view.display_name,
        "fields": filterable_fields
    }


@router.put("/{id}/columns")
def update_view_columns(id: str, data: ViewColumnUpdate, db: Session = Depends(get_db)):
    """
    更新视图字段配置
    
    包括展示名、说明、值域配置、过滤开关等
    """
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # 验证字段配置
    for col in data.columns:
        name = col.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="字段名不能为空")
        
        # 验证字典引用
        value_config = col.get("value_config", {})
        if value_config.get("type") == "dict":
            dict_id = value_config.get("dict_id")
            if dict_id:
                from app.models.field_dict import FieldDictionary
                dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == dict_id).first()
                if not dictionary:
                    raise HTTPException(status_code=400, detail=f"字典 '{dict_id}' 不存在")
    
    # 更新字段配置
    view.columns = data.columns
    db.commit()
    db.refresh(view)
    
    return view.to_dict()


@router.patch("/{id}/columns/{column_name}")
def update_single_column(
    id: str, 
    column_name: str, 
    data: ColumnConfig, 
    db: Session = Depends(get_db)
):
    """
    更新单个字段配置
    """
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    if not view.columns:
        raise HTTPException(status_code=400, detail="视图尚未配置字段列表")
    
    # 查找并更新字段
    found = False
    for i, col in enumerate(view.columns):
        if col.get("name") == column_name:
            found = True
            # 合并更新
            if data.display_name is not None:
                col["display_name"] = data.display_name
            if data.description is not None:
                col["description"] = data.description
            if data.value_config is not None:
                col["value_config"] = data.value_config.model_dump()
            if data.filterable is not None:
                col["filterable"] = data.filterable
            if data.filter_operators is not None:
                col["filter_operators"] = data.filter_operators
            if data.synonyms is not None:
                col["synonyms"] = data.synonyms
            view.columns[i] = col
            break
    
    if not found:
        raise HTTPException(status_code=404, detail=f"字段 '{column_name}' 不存在")
    
    db.commit()
    db.refresh(view)
    
    return view.to_dict()


@router.post("/{id}/columns/sync-from-source")
async def sync_columns_from_source(id: str, db: Session = Depends(get_db)):
    """
    从物理表/视图同步字段元数据
    
    对于单表视图：从基础表同步字段
    对于 JOIN 视图：从所有参与 JOIN 的表同步字段
    对于 SQL 视图：无法自动同步，需手动配置
    """
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    if view.view_type == ViewType.SQL:
        raise HTTPException(status_code=400, detail="SQL 视图无法自动同步，请手动配置字段")
    
    datasets = {d.id: d for d in db.query(Dataset).all()}
    existing_columns = view.columns or []
    existing_names = {c.get("name") for c in existing_columns}
    
    new_columns = []
    
    if view.view_type == ViewType.SINGLE_TABLE and view.base_table_id:
        dataset = datasets.get(view.base_table_id)
        if dataset and dataset.columns:
            for col in dataset.columns:
                col_name = col.get("name")
                if col_name not in existing_names:
                    new_columns.append({
                        "name": col_name,
                        "source_column": col_name,
                        "type": col.get("type"),
                        "display_name": col_name,
                        "description": "",
                        "default_comment": col.get("comment", ""),
                        "filterable": True,
                        "value_config": {"type": "none"}
                    })
    
    elif view.view_type == ViewType.JOINED and view.join_config:
        tables = view.join_config.get("tables", [])
        for t in tables:
            dataset_id = t.get("id")
            alias = t.get("alias", "")
            dataset = datasets.get(dataset_id)
            if dataset and dataset.columns:
                for col in dataset.columns:
                    col_name = f"{alias}.{col.get('name')}"
                    if col_name not in existing_names:
                        new_columns.append({
                            "name": col_name,
                            "source_table": alias,
                            "source_column": col.get("name"),
                            "type": col.get("type"),
                            "display_name": col.get("name"),
                            "description": "",
                            "default_comment": col.get("comment", ""),
                            "filterable": True,
                            "value_config": {"type": "none"}
                        })
    
    if new_columns:
        view.columns = existing_columns + new_columns
        db.commit()
        db.refresh(view)
    
    return {
        "message": f"同步完成，新增 {len(new_columns)} 个字段",
        "new_columns_count": len(new_columns),
        "view": view.to_dict()
    }


@router.get("/{id}/columns/{column_name}/values")
async def get_column_values(
    id: str, 
    column_name: str, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取字段的可选值列表
    
    根据字段的 value_config 配置返回可选值：
    - enum: 直接返回枚举值列表
    - dict: 从字典获取值
    - sql: 执行 SQL 查询获取值
    - range: 返回范围配置
    - none: 从实际数据中采样
    """
    view = db.query(View).filter(View.id == id).first()
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    
    # 查找字段配置
    column_config = None
    if view.columns:
        for col in view.columns:
            if col.get("name") == column_name:
                column_config = col
                break
    
    if not column_config:
        raise HTTPException(status_code=404, detail=f"字段 '{column_name}' 不存在")
    
    value_config = column_config.get("value_config", {"type": "none"})
    config_type = value_config.get("type", "none")
    
    from app.models.field_dict import FieldDictionary
    
    # 枚举类型
    if config_type == "enum":
        enum_values = value_config.get("enum_values", [])
        return {
            "type": "enum",
            "values": [{"value": v, "label": v} for v in enum_values],
            "total": len(enum_values)
        }
    
    # 字典类型
    elif config_type == "dict":
        dict_id = value_config.get("dict_id")
        if not dict_id:
            return {"type": "dict", "values": [], "error": "未配置字典"}
        
        dictionary = db.query(FieldDictionary).filter(FieldDictionary.id == dict_id).first()
        if not dictionary:
            return {"type": "dict", "values": [], "error": "字典不存在"}
        
        # 根据字典类型获取值
        if dictionary.source_type == "manual":
            values = dictionary.mappings or []
            return {"type": "dict", "values": values, "total": len(values)}
        else:
            # 动态查询
            # ... 这里可以复用 dictionaries API 的逻辑
            return {"type": "dict", "values": dictionary.mappings or [], "total": len(dictionary.mappings or [])}
    
    # 范围类型
    elif config_type == "range":
        r = value_config.get("range", {})
        return {
            "type": "range",
            "range": r
        }
    
    # SQL 类型
    elif config_type == "sql":
        sql_expr = value_config.get("sql_expression")
        if not sql_expr:
            return {"type": "sql", "values": [], "error": "未配置 SQL 表达式"}
        
        try:
            result = await execute_query(
                sql=sql_expr,
                datasource_id=view.datasource_id,
                limit=limit,
                db=db
            )
            value_col = value_config.get("value_column", 0)
            label_col = value_config.get("label_column", value_col)
            
            values = []
            for row in result.get("data", []):
                v = row[0] if isinstance(value_col, int) or value_col.isdigit() else row.get(value_col)
                l = row[int(label_col) if isinstance(label_col, int) or label_col.isdigit() else label_col] if label_col != value_col else v
                values.append({"value": str(v), "label": str(l) if l else str(v)})
            
            return {"type": "sql", "values": values, "total": len(values)}
        except Exception as e:
            return {"type": "sql", "values": [], "error": str(e)}
    
    # 默认：从实际数据采样
    else:
        datasets = {d.id: d for d in db.query(Dataset).all()}
        from_clause = view.generate_from_clause(datasets)
        
        # 确定列表达式
        source_table = column_config.get("source_table")
        source_column = column_config.get("source_column", column_name)
        
        if source_table and view.view_type == ViewType.JOINED:
            col_expr = f"{source_table}.{source_column}"
        else:
            col_expr = source_column
        
        sql = f"SELECT DISTINCT {col_expr} AS value FROM {from_clause} WHERE {col_expr} IS NOT NULL LIMIT {limit}"
        
        try:
            result = await execute_query(
                sql=sql,
                datasource_id=view.datasource_id,
                limit=limit,
                db=db
            )
            values = [{"value": str(row[0]), "label": str(row[0])} for row in result.get("data", [])]
            return {"type": "sampled", "values": values, "total": len(values)}
        except Exception as e:
            return {"type": "sampled", "values": [], "error": str(e)}


