"""View Model - Virtual views for multi-table aggregation"""
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class ViewType:
    SINGLE_TABLE = "single_table"  # 单表模式
    JOINED = "joined"              # 多表聚合模式
    SQL = "sql"                    # 自定义SQL模式


class View(Base):
    """
    视图模型 - 支持三种类型：
    1. single_table: 基于单个物理表
    2. joined: 多表通过JOIN聚合
    3. sql: 自定义SQL语句
    """
    __tablename__ = "views"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=True)
    datasource_id = Column(String(36), ForeignKey("datasources.id"), nullable=False)

    # 分类管理
    category_id = Column(String(36), nullable=True, index=True)
    category_name = Column(String(255), nullable=True)

    # 是否为默认视图
    is_default = Column(Boolean, default=False, index=True)

    # 视图类型：single_table | joined | sql
    view_type = Column(String(20), nullable=False, default=ViewType.SINGLE_TABLE)
    
    # 基础表ID（单表模式）
    base_table_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)
    
    # JOIN配置（多表聚合模式）
    # 格式: {
    #   "tables": [{"id": "table_id", "alias": "t1", "position": {"x": 0, "y": 0}}],
    #   "joins": [{
    #     "left_table": "t1",
    #     "right_table": "t2", 
    #     "join_type": "LEFT",
    #     "conditions": [{"left_column": "id", "right_column": "user_id", "operator": "="}]
    #   }]
    # }
    join_config = Column(JSON, nullable=True)
    
    # 自定义SQL（SQL模式）
    custom_sql = Column(Text, nullable=True)
    
    # 视图字段列表
    # 格式: [{
    #   "name": "column_name",
    #   "source_table": "table_alias",
    #   "source_column": "original_column",
    #   "alias": "display_alias",
    #   "type": "VARCHAR",
    #   "description": "字段描述"
    # }]
    columns = Column(JSON, nullable=True)
    
    # 默认时间字段 ID（用于 MQL 查询时自动填充时间过滤）
    # 关联 Dimension 表的 ID，指定该视图的默认时间维度
    default_date_column_id = Column(String(36), nullable=True)
    
    # 画布布局配置（用于保存节点位置等）
    canvas_config = Column(JSON, nullable=True)
    
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "datasource_id": self.datasource_id,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "is_default": self.is_default or False,
            "view_type": self.view_type,
            "base_table_id": self.base_table_id,
            "join_config": self.join_config,
            "custom_sql": self.custom_sql,
            "columns": self.columns or [],
            "default_date_column_id": self.default_date_column_id,
            "canvas_config": self.canvas_config,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def generate_from_clause(self, datasets: dict, dialect: str = "mysql") -> str:
        """
        根据视图类型生成 FROM 子句
        """
        if self.view_type == ViewType.SINGLE_TABLE:
            if self.base_table_id and self.base_table_id in datasets:
                table = datasets[self.base_table_id]
                return f"{table.physical_name}"
            return "(SELECT 1) AS empty_view"
            
        elif self.view_type == ViewType.JOINED:
            return self._build_join_sql(datasets, dialect)
            
        elif self.view_type == ViewType.SQL:
            if self.custom_sql:
                return f"({self.custom_sql}) AS view_{self.id[:8]}"
            return "(SELECT 1) AS empty_view"
            
        return "(SELECT 1) AS empty_view"

    def _build_join_sql(self, datasets: dict, dialect: str) -> str:
        """
        构建多表JOIN的SQL
        """
        if not self.join_config:
            return "(SELECT 1) AS empty_view"
            
        tables = self.join_config.get("tables", [])
        joins = self.join_config.get("joins", [])
        
        if not tables:
            return "(SELECT 1) AS empty_view"
        
        # 构建表别名映射
        table_map = {}
        for t in tables:
            dataset_id = t.get("id")
            alias = t.get("alias", f"t{len(table_map)}")
            if dataset_id in datasets:
                table_map[alias] = datasets[dataset_id].physical_name
        
        if not table_map:
            return "(SELECT 1) AS empty_view"
        
        # 第一个表作为基础表
        first_table = tables[0]
        first_alias = first_table.get("alias", "t0")
        sql_parts = [f"{table_map.get(first_alias, 'unknown')} AS {first_alias}"]
        
        # 添加JOIN子句
        for join in joins:
            left_alias = join.get("left_table")
            right_alias = join.get("right_table")
            join_type = join.get("join_type", "INNER").upper()
            conditions = join.get("conditions", [])
            
            if right_alias not in table_map:
                continue
                
            right_table = table_map[right_alias]
            
            # 构建ON条件（包括连接条件和筛选条件）
            on_parts = []
            
            # 添加连接条件
            for cond in conditions:
                left_col = cond.get("left_column")
                right_col = cond.get("right_column")
                operator = cond.get("operator", "=")
                on_parts.append(f"{left_alias}.{left_col} {operator} {right_alias}.{right_col}")
            
            # 添加筛选条件（filters）
            filters = join.get("filters", [])
            for filter_cond in filters:
                column = filter_cond.get("column", "")
                operator = filter_cond.get("operator", "=")
                value = filter_cond.get("value", "")
                
                # 解析列名，提取表别名和列名
                if "." in column:
                    filter_alias, filter_col = column.split(".", 1)
                else:
                    # 如果没有表别名，默认使用右表
                    filter_alias = right_alias
                    filter_col = column
                
                if operator.upper() in ["IS NULL", "IS NOT NULL"]:
                    on_parts.append(f"{filter_alias}.{filter_col} {operator}")
                else:
                    # 对字符串值添加引号
                    if isinstance(value, str):
                        value = f"'{value}'"
                    on_parts.append(f"{filter_alias}.{filter_col} {operator} {value}")
            
            on_clause = " AND ".join(on_parts) if on_parts else "1=1"
            sql_parts.append(f"{join_type} JOIN {right_table} AS {right_alias} ON {on_clause}")
        
        return " ".join(sql_parts)
