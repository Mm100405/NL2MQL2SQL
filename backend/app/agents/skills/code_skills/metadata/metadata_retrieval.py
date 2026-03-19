# backend/app/agents/skills/code_skills/metadata/metadata_retrieval.py

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
import json

from app.agents.skills.base_skill import BaseSkill


class MetadataRetrievalSkill(BaseSkill):
    """元数据检索Skill
    
    根据自然语言查询检索相关的元数据，包括：
    - 指标（Metrics）
    - 维度（Dimensions）
    - 可过滤字段（Filterable Fields）
    - 时间格式（Time Formats）
    
    复用现有服务层的逻辑。
    """
    
    skill_name = "metadata_retrieval"
    skill_type = "retrieval"
    description = "根据自然语言查询检索相关元数据（指标、维度、可过滤字段）"
    required_inputs = ["natural_language"]
    optional_inputs = ["context"]
    outputs = ["metadata", "suggested_metrics", "suggested_dimensions"]
    
    def __init__(self, db: Session = None):
        super().__init__(db)
    
    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行元数据检索"""
        natural_language = inputs.get("natural_language", "")
        context = inputs.get("context", {})
        
        # 检索指标
        metrics = self._retrieve_metrics(natural_language, context)
        
        # 检索维度（包含时间维度衍生）
        dimensions = self._retrieve_dimensions(natural_language, context)
        
        # 检索可过滤字段
        filterable_fields = self._retrieve_filterable_fields()
        
        # 检索时间格式
        time_formats = self._retrieve_time_formats()
        
        # 构建元数据
        metadata = {
            "metrics": metrics,
            "dimensions": dimensions,
            "filterable_fields": filterable_fields,
            "time_formats": time_formats
        }
        
        return {
            "metadata": metadata,
            "suggested_metrics": [m["display_name"] for m in metrics[:10]],
            "suggested_dimensions": [d["display_name"] for d in dimensions[:10]]
        }
    
    def _retrieve_metrics(self, query: str, context: dict) -> list:
        """检索指标"""
        if not self.db:
            return []
        
        try:
            from app.models.metric import Metric
            
            metrics_query = self.db.query(Metric)
            
            if context.get("suggested_metrics"):
                metrics_query = metrics_query.filter(or_(
                    Metric.name.in_(context["suggested_metrics"]),
                    Metric.display_name.in_(context["suggested_metrics"])
                ))
            
            metrics = metrics_query.all()
            
            return [
                {
                    "name": m.name,
                    "display_name": m.display_name,
                    "measure_column": m.measure_column,
                    "aggregation": m.aggregation,
                    "description": m.description or ""
                }
                for m in metrics
            ]
        except Exception as e:
            print(f"⚠️  检索指标失败: {e}")
            return []
    
    def _retrieve_dimensions(self, query: str, context: dict) -> list:
        """检索维度（包含时间维度衍生）"""
        if not self.db:
            return []
        
        try:
            from app.models.dimension import Dimension
            
            dimensions_query = self.db.query(Dimension)
            
            if context.get("suggested_dimensions"):
                dimensions_query = dimensions_query.filter(or_(
                    Dimension.name.in_(context["suggested_dimensions"]),
                    Dimension.display_name.in_(context["suggested_dimensions"])
                ))
            
            dimensions = dimensions_query.all()
            time_formats = self._retrieve_time_formats()
            
            result = []
            
            for d in dimensions:
                # 判断是否为时间维度
                is_time_dim = (
                    (d.dimension_type and d.dimension_type == "time") or
                    (d.data_type and d.data_type.lower() in ["date", "datetime", "timestamp"])
                )
                
                if not is_time_dim:
                    # 普通维度
                    result.append({
                        "name": d.name,
                        "display_name": d.display_name,
                        "physical_column": d.physical_column,
                        "type": "normal",
                        "description": d.description or ""
                    })
                else:
                    # 时间维度：衍生多个时间格式
                    format_options = []
                    if d.format_config:
                        try:
                            config = json.loads(d.format_config) if isinstance(d.format_config, str) else d.format_config
                            format_options = config.get("options", [])
                        except:
                            pass
                    
                    if not format_options:
                        format_options = [f["name"] for f in time_formats]
                    
                    for fmt_cfg in time_formats:
                        if fmt_cfg["name"] in format_options:
                            suffix = fmt_cfg["suffix"]
                            label = fmt_cfg["label"]
                            result.append({
                                "name": f"{d.name}__{suffix}",
                                "display_name": f"{d.display_name}({label})",
                                "physical_column": d.physical_column,
                                "type": "time_virtual",
                                "format": fmt_cfg["name"]
                            })
            
            return result
        except Exception as e:
            print(f"⚠️  检索维度失败: {e}")
            return []
    
    def _retrieve_filterable_fields(self) -> list:
        """检索可过滤字段"""
        if not self.db:
            return []
        
        try:
            from app.models.view import View
            
            fields = []
            views = self.db.query(View).all()
            
            for view in views:
                for col in view.columns or []:
                    if col.get("filterable", True):
                        fields.append({
                            "display_name": col.get("display_name") or col.get("name"),
                            "name": col.get("name"),
                            "type": col.get("type", ""),
                            "view": view.name
                        })
            
            return fields
        except Exception as e:
            print(f"⚠️  检索可过滤字段失败: {e}")
            return []
    
    def _retrieve_time_formats(self) -> list:
        """检索时间格式"""
        if not self.db:
            return self._get_default_time_formats()
        
        try:
            from app.models.settings import SystemSetting
            
            time_formats_setting = self.db.query(SystemSetting).filter(
                SystemSetting.key == "time_formats"
            ).first()
            
            if time_formats_setting:
                val = time_formats_setting.value
                if isinstance(val, str):
                    try:
                        return json.loads(val)
                    except:
                        pass
                elif isinstance(val, list):
                    return val
        except Exception as e:
            print(f"⚠️  检索时间格式失败: {e}")
        
        return self._get_default_time_formats()
    
    def _get_default_time_formats(self) -> list:
        """返回默认时间格式"""
        return [
            {"name": "YYYY-MM-DD", "label": "按日", "suffix": "day"},
            {"name": "YYYY-MM", "label": "按月", "suffix": "month"},
            {"name": "YYYY", "label": "按年", "suffix": "year"},
            {"name": "YYYY-WW", "label": "按周", "suffix": "week"}
        ]
