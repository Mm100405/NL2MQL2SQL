"""AI-assisted semantic modeling API."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlglot import exp

from app.database import get_db
from app.models.dataset import Dataset
from app.models.dimension import Dimension
from app.models.datasource import DataSource
from app.models.field_dict import DictSourceType, FieldDictionary
from app.models.metric import Metric
from app.models.model_config import ModelConfig
from app.models.view import View, ViewType
from app.models.view_category import ViewCategory
from app.services.llm_client import call_llm
from app.services.mql_translator.dialect import get_dialect_name
from app.utils.encryption import decrypt_api_key

router = APIRouter()


class SemanticProfileRequest(BaseModel):
    datasource_id: str
    table_names: Optional[List[str]] = None


class SemanticDraftRequest(BaseModel):
    datasource_id: str
    business_goal: str = Field(..., min_length=1)
    main_table: Optional[str] = None
    related_tables: Optional[List[str]] = None
    max_fields: int = Field(80, ge=20, le=150)
    use_llm: bool = True


class SemanticPublishRequest(BaseModel):
    datasource_id: str
    draft: Dict[str, Any]
    set_default: bool = True


COMMON_LABELS = {
    "id": "主键",
    "rec_id": "案件编号",
    "create_time": "创建时间",
    "operate_time": "受理时间",
    "inst_time": "立案时间",
    "dispatch_time": "派遣时间",
    "dispose_begin_time": "处置开始时间",
    "dispose_end_time": "处置结束时间",
    "archive_time": "归档时间",
    "city_name": "城市",
    "district_name": "区县",
    "street_name": "街道",
    "community_name": "社区",
    "cell_name": "网格",
    "road_name": "道路",
    "main_type_name": "大类",
    "sub_type_name": "小类",
    "third_type_name": "三级分类",
    "event_src_name": "事件来源",
    "rec_type_name": "立案类型",
    "event_state_name": "案件状态",
    "event_grade_name": "事件等级",
    "event_level_name": "事件级别",
    "event_property_name": "事件属性",
    "first_unit_name": "一级处置单位",
    "second_unit_name": "二级处置单位",
    "third_unit_name": "三级处置单位",
    "dispose_unit_name": "处置单位",
    "accepter_name": "受理人",
    "dispatcher_name": "派遣人",
    "dispose_human_name": "处置人",
    "archive_human_name": "归档人",
    "report_num": "上报数",
    "valid_report_num": "有效上报数",
    "invalid_report_num": "无效上报数",
    "repeat_report_num": "重复上报数",
    "patrol_report_num": "巡查上报数",
    "public_report_num": "公众上报数",
    "operate_num": "受理数",
    "intime_operate_num": "按时受理数",
    "overtime_operate_num": "超时受理数",
    "inst_num": "立案数",
    "intime_inst_num": "按时立案数",
    "overtime_inst_num": "超时立案数",
    "dispatch_num": "派遣数",
    "intime_dispatch_num": "按时派遣数",
    "overtime_dispatch_num": "超时派遣数",
    "dispose_num": "处置数",
    "intime_dispose_num": "按时处置数",
    "overtime_dispose_num": "超时处置数",
    "archive_num": "归档数",
    "intime_archive_num": "按时归档数",
    "overtime_archive_num": "超时归档数",
    "cancel_num": "作废数",
    "rework_num": "返工数",
    "postpone_num": "延期数",
    "hang_num": "挂起数",
    "used_time": "总用时",
    "used_work_time": "工作用时",
}

TIME_KEYWORDS = ("date", "time", "日期", "时间")
NUMERIC_TYPES = ("int", "number", "decimal", "numeric", "float", "double", "real")
DIMENSION_KEYWORDS = (
    "name", "type", "state", "status", "src", "source", "grade", "level",
    "region", "district", "street", "community", "cell", "road", "unit", "human",
)
METRIC_SUFFIXES = ("num", "count", "cnt", "amount", "total", "rate", "duration", "times")
ID_SUFFIXES = ("id", "_id", "code", "no")


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _safe_name(value: str, fallback: str) -> str:
    text = _lower(value)
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"n_{text}"
    return text[:80]


def _column_name(column: Dict[str, Any]) -> str:
    return str(column.get("name") or "")


def _column_type(column: Dict[str, Any]) -> str:
    return str(column.get("type") or "string")


def _is_time_column(column: Dict[str, Any]) -> bool:
    name = _lower(_column_name(column))
    typ = _lower(_column_type(column))
    return any(k in name for k in TIME_KEYWORDS) or any(k in typ for k in ("date", "time"))


def _is_numeric_column(column: Dict[str, Any]) -> bool:
    typ = _lower(_column_type(column))
    return any(k in typ for k in NUMERIC_TYPES)


def _is_identifier_column(column: Dict[str, Any]) -> bool:
    name = _lower(_column_name(column))
    if name in {"id", "rec_id", "case_id", "event_id"}:
        return True
    return any(name.endswith(suffix) for suffix in ID_SUFFIXES)


def _is_metric_column(column: Dict[str, Any]) -> bool:
    name = _lower(_column_name(column))
    if _is_time_column(column) or name == "id":
        return False
    if name.endswith("_id") or name.endswith("id"):
        return False
    if any(name.endswith(f"_{suffix}") or name == suffix for suffix in METRIC_SUFFIXES):
        return True
    if any(token in name for token in ("amount", "total", "rate", "duration", "used_time", "work_time")):
        return True
    return _is_numeric_column(column) and not _is_identifier_column(column)


def _is_dimension_column(column: Dict[str, Any]) -> bool:
    name = _lower(_column_name(column))
    if _is_time_column(column):
        return True
    if _is_metric_column(column):
        return False
    if name.endswith("_name"):
        return True
    return any(keyword in name for keyword in DIMENSION_KEYWORDS)


def _data_type(column: Dict[str, Any]) -> str:
    if _is_time_column(column):
        return "datetime" if "time" in _lower(_column_name(column)) or "time" in _lower(_column_type(column)) else "date"
    if _is_numeric_column(column):
        return "number"
    return "string"


def _dimension_type(column: Dict[str, Any]) -> str:
    name = _lower(_column_name(column))
    if _is_time_column(column):
        return "time"
    if any(k in name for k in ("city", "district", "street", "community", "cell", "region", "road")):
        return "geo"
    if _is_numeric_column(column):
        return "numerical"
    return "categorical"


def _display_name(column: Dict[str, Any]) -> str:
    name = _column_name(column)
    lower = _lower(name)
    comment = str(column.get("comment") or "").strip()
    if comment:
        return comment[:80]
    if lower in COMMON_LABELS:
        return COMMON_LABELS[lower]
    if lower.endswith("_name") and lower[:-5] in COMMON_LABELS:
        return COMMON_LABELS[lower[:-5]]
    if lower.endswith("_id") and f"{lower[:-3]}_name" in COMMON_LABELS:
        return f"{COMMON_LABELS[f'{lower[:-3]}_name']}编码"
    return name.replace("_", " ").strip().title() or name


def _description(column: Dict[str, Any]) -> str:
    display_name = _display_name(column)
    name = _column_name(column)
    if _is_time_column(column):
        return f"用于按{display_name}进行时间筛选和趋势分析"
    if _is_metric_column(column):
        return f"可用于计算{display_name}相关指标"
    if _is_dimension_column(column):
        return f"用于按{display_name}分组、筛选和下钻"
    return f"来源字段：{name}"


def _table_lookup_key(dataset: Dataset) -> set[str]:
    return {
        dataset.id,
        _lower(dataset.name),
        _lower(dataset.physical_name),
        f"{_lower(dataset.schema_name)}.{_lower(dataset.physical_name)}" if dataset.schema_name else _lower(dataset.physical_name),
    }


def _find_dataset(db: Session, datasource_id: str, token: Optional[str]) -> Optional[Dataset]:
    if not token:
        return None
    token_lower = _lower(token)
    datasets = db.query(Dataset).filter(Dataset.datasource_id == datasource_id).all()
    for dataset in datasets:
        if token == dataset.id or token_lower in _table_lookup_key(dataset):
            return dataset
    return None


def _score_dataset(dataset: Dataset, business_goal: str) -> int:
    name = _lower(f"{dataset.name} {dataset.physical_name}")
    goal = _lower(business_goal)
    columns = dataset.columns or []
    score = 0
    for token in re.split(r"[\s,，;；/]+", goal):
        if token and token in name:
            score += 12
    if any(k in goal for k in ("案件", "事件", "上报")) and any(k in name for k in ("stat", "event", "case", "rec", "info")):
        score += 20
    if "stat_info" in name:
        score += 15
    score += min(len(columns), 80) // 8
    score += sum(1 for col in columns if _is_time_column(col)) * 2
    score += sum(1 for col in columns if _is_dimension_column(col)) // 4
    score += sum(1 for col in columns if _is_metric_column(col)) // 4
    return score


def _select_main_dataset(db: Session, datasource_id: str, business_goal: str, main_table: Optional[str]) -> Dataset:
    explicit = _find_dataset(db, datasource_id, main_table)
    if explicit:
        return explicit
    datasets = db.query(Dataset).filter(Dataset.datasource_id == datasource_id).all()
    if not datasets:
        raise HTTPException(status_code=400, detail="该数据源下没有已同步的物理表，请先同步物理表")
    return max(datasets, key=lambda dataset: _score_dataset(dataset, business_goal))


def _profile_dataset(dataset: Dataset, business_goal: str = "") -> Dict[str, Any]:
    columns = dataset.columns or []
    time_columns = [col for col in columns if _is_time_column(col)]
    dimension_columns = [col for col in columns if _is_dimension_column(col)]
    metric_columns = [col for col in columns if _is_metric_column(col)]
    id_columns = [col for col in columns if _is_identifier_column(col)]
    return {
        "id": dataset.id,
        "name": dataset.name,
        "physical_name": dataset.physical_name,
        "schema_name": dataset.schema_name,
        "description": dataset.description,
        "column_count": len(columns),
        "score": _score_dataset(dataset, business_goal),
        "time_columns": [_column_name(col) for col in time_columns[:20]],
        "dimension_candidates": [_column_name(col) for col in dimension_columns[:30]],
        "metric_candidates": [_column_name(col) for col in metric_columns[:30]],
        "identifier_candidates": [_column_name(col) for col in id_columns[:20]],
    }


def _rank_columns(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def score(column: Dict[str, Any]) -> tuple[int, str]:
        name = _lower(_column_name(column))
        value = 0
        if name in ("rec_id", "case_id", "event_id", "id"):
            value += 100
        if _is_time_column(column):
            value += 90
        if name.endswith("_name"):
            value += 80
        if name.endswith("_id"):
            paired_name = f"{name[:-3]}_name"
            if any(_lower(_column_name(c)) == paired_name for c in columns):
                value += 70
        if _is_metric_column(column):
            value += 60
        if _is_dimension_column(column):
            value += 50
        if any(k in name for k in ("desc", "content", "address", "title")):
            value += 20
        return (-value, name)

    return sorted(columns, key=score)


def _build_view_columns(dataset: Dataset, max_fields: int) -> List[Dict[str, Any]]:
    selected = _rank_columns(dataset.columns or [])[:max_fields]
    return [
        {
            "name": _column_name(col),
            "source_column": _column_name(col),
            "type": _column_type(col),
            "display_name": _display_name(col),
            "description": _description(col),
            "filterable": _is_dimension_column(col) or _is_time_column(col),
            "value_config": {"type": "none"},
        }
        for col in selected
        if _column_name(col)
    ]


def _build_custom_sql(dataset: Dataset, columns: List[Dict[str, Any]], datasource: DataSource) -> str:
    dialect = get_dialect_name(datasource.normalized_type)
    select_expressions = [
        exp.alias_(
            exp.Column(this=exp.Identifier(this=col["name"], quoted=True)),
            col["name"],
            quoted=True,
        )
        for col in columns
        if col.get("name")
    ]
    table = exp.Table(this=exp.Identifier(this=dataset.physical_name, quoted=True))
    if dataset.schema_name:
        table.set("db", exp.Identifier(this=dataset.schema_name, quoted=True))
    return exp.select(*select_expressions).from_(table).sql(dialect=dialect)


def _default_time_column(columns: List[Dict[str, Any]]) -> Optional[str]:
    preferred = ("create_time", "stat_date", "date", "archive_time", "operate_time")
    by_name = {_lower(col["name"]): col["name"] for col in columns}
    for name in preferred:
        if name in by_name:
            return by_name[name]
    for col in columns:
        if _is_time_column(col):
            return col["name"]
    return None


def _build_dimensions(columns: List[Dict[str, Any]], default_time: Optional[str]) -> List[Dict[str, Any]]:
    dimensions: List[Dict[str, Any]] = []
    for col in columns:
        if not col.get("filterable"):
            continue
        name = col["name"]
        source = {"name": name, "type": col.get("type")}
        if not (_is_dimension_column(source) or name == default_time):
            continue
        dimensions.append({
            "name": _safe_name(name, "dimension"),
            "display_name": col.get("display_name") or name,
            "physical_column": name,
            "data_type": _data_type(source),
            "dimension_type": _dimension_type(source),
            "synonyms": [col.get("display_name") or name, name],
            "description": col.get("description") or _description(source),
        })
    dimensions.sort(key=lambda dim: 0 if dim["physical_column"] == default_time else 1)
    return dimensions[:40]


def _build_metrics(columns: List[Dict[str, Any]], business_goal: str) -> List[Dict[str, Any]]:
    by_name = {_lower(col["name"]): col for col in columns}
    metrics: List[Dict[str, Any]] = []
    count_col = by_name.get("rec_id") or by_name.get("case_id") or by_name.get("event_id") or by_name.get("id")
    subject = "案件" if "案件" in business_goal or "事件" in business_goal else "记录"
    if count_col:
        metrics.append({
            "name": f"{_safe_name(subject, 'record')}_count" if subject != "案件" else "case_count",
            "display_name": f"{subject}数量",
            "aggregation": "COUNT_DISTINCT" if _lower(count_col["name"]) != "id" else "COUNT",
            "measure_column": count_col["name"],
            "unit": "件" if subject == "案件" else "条",
            "synonyms": [f"{subject}数", f"{subject}总数", "数量"],
            "description": f"按{count_col['name']}统计{subject}数量",
        })
    for col in columns:
        source = {"name": col["name"], "type": col.get("type")}
        if not _is_metric_column(source):
            continue
        lower = _lower(col["name"])
        aggregation = "AVG" if any(k in lower for k in ("rate", "duration", "used_time", "work_time")) else "SUM"
        prefix = "avg" if aggregation == "AVG" else "sum"
        display_suffix = "平均" if aggregation == "AVG" else "合计"
        metrics.append({
            "name": _safe_name(f"{prefix}_{col['name']}", "metric"),
            "display_name": f"{col.get('display_name') or col['name']}{display_suffix}",
            "aggregation": aggregation,
            "measure_column": col["name"],
            "unit": "%" if "rate" in lower else None,
            "synonyms": [col.get("display_name") or col["name"], col["name"]],
            "description": f"基于字段 {col['name']} 的{display_suffix}指标",
        })
        if len(metrics) >= 16:
            break
    seen: set[str] = set()
    result: List[Dict[str, Any]] = []
    for metric in metrics:
        if metric["name"] in seen:
            continue
        seen.add(metric["name"])
        result.append(metric)
    return result


def _build_dictionaries(dimensions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    dictionaries: List[Dict[str, Any]] = []
    for dim in dimensions:
        col = dim["physical_column"]
        name = _lower(col)
        if dim.get("dimension_type") == "time" or not any(k in name for k in DIMENSION_KEYWORDS):
            continue
        dictionaries.append({
            "name": _safe_name(f"{col}_dict", "field_dict"),
            "display_name": f"{dim.get('display_name') or col}字典",
            "target_column": col,
            "value_column": col,
            "label_column": col,
            "description": f"用于字段 {col} 的筛选值域和自然语言匹配",
        })
        if len(dictionaries) >= 12:
            break
    return dictionaries


def _build_questions(metrics: List[Dict[str, Any]], dimensions: List[Dict[str, Any]], default_time: Optional[str]) -> List[str]:
    metric_name = metrics[0]["display_name"] if metrics else "记录数量"
    questions = [f"今年{metric_name}是多少？"] if default_time else [f"{metric_name}是多少？"]
    for dim in dimensions:
        if dim.get("dimension_type") in {"categorical", "geo"}:
            questions.append(f"按{dim['display_name']}统计{metric_name}")
        if len(questions) >= 5:
            break
    return questions


def _build_rule_draft(dataset: Dataset, datasource: DataSource, request: SemanticDraftRequest) -> Dict[str, Any]:
    view_columns = _build_view_columns(dataset, request.max_fields)
    if not view_columns:
        raise HTTPException(status_code=400, detail="主表没有可用于建模的字段")
    default_time = _default_time_column(view_columns)
    dimensions = _build_dimensions(view_columns, default_time)
    metrics = _build_metrics(view_columns, request.business_goal)
    dictionaries = _build_dictionaries(dimensions)
    for col in view_columns:
        if any(d["target_column"] == col["name"] for d in dictionaries):
            col["value_config"] = {"type": "dict", "dict_id": None}
    subject_name = request.business_goal.strip()[:24] or dataset.name
    view_name = _safe_name(f"{dataset.physical_name}_ai_view", "ai_view")
    return {
        "business_subject": subject_name,
        "generation_method": "rule_based",
        "category_name": "AI生成问数主题",
        "datasource": datasource.to_dict(),
        "main_dataset": dataset.to_dict(),
        "view": {
            "name": view_name,
            "display_name": f"{subject_name}视图",
            "view_type": ViewType.SQL,
            "base_table_id": dataset.id,
            "custom_sql": _build_custom_sql(dataset, view_columns, datasource),
            "columns": view_columns,
            "default_time_column": default_time,
            "description": f"由 AI 语义建模助手基于 {dataset.physical_name} 生成，面向“{request.business_goal}”场景。",
        },
        "dimensions": dimensions,
        "metrics": metrics,
        "dictionaries": dictionaries,
        "validation_questions": _build_questions(metrics, dimensions, default_time),
        "warnings": [],
    }


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _merge_llm_enrichment(draft: Dict[str, Any], enrichment: Dict[str, Any]) -> None:
    if enrichment.get("business_subject"):
        draft["business_subject"] = str(enrichment["business_subject"])[:50]
    if isinstance(enrichment.get("validation_questions"), list):
        draft["validation_questions"] = [str(q)[:120] for q in enrichment["validation_questions"][:8] if q]
    column_labels = enrichment.get("column_display_names") or {}
    if isinstance(column_labels, dict):
        for col in draft["view"]["columns"]:
            label = column_labels.get(col["name"])
            if label:
                col["display_name"] = str(label)[:80]
    metric_labels = enrichment.get("metric_display_names") or {}
    if isinstance(metric_labels, dict):
        for metric in draft["metrics"]:
            label = metric_labels.get(metric["name"])
            if label:
                metric["display_name"] = str(label)[:80]
    dimension_labels = enrichment.get("dimension_display_names") or {}
    if isinstance(dimension_labels, dict):
        for dim in draft["dimensions"]:
            label = dimension_labels.get(dim["name"])
            if label:
                dim["display_name"] = str(label)[:80]
    draft["generation_method"] = "rule_based_with_llm_enrichment"


async def _enrich_with_default_model(draft: Dict[str, Any], business_goal: str, db: Session) -> None:
    config = db.query(ModelConfig).filter(ModelConfig.is_default.is_(True), ModelConfig.is_active.is_(True)).first()
    if not config:
        draft["warnings"].append("未配置默认模型，已使用规则引擎生成草案")
        return
    prompt = f"""
你是数据语义建模助手。请基于业务目标和规则草案，只润色中文展示名、同义业务问题，不要改变字段名、指标名和表名。

业务目标：{business_goal}

规则草案摘要：
{json.dumps({
    "business_subject": draft.get("business_subject"),
    "view_columns": [{"name": c.get("name"), "display_name": c.get("display_name"), "type": c.get("type")} for c in draft["view"]["columns"][:80]],
    "dimensions": [{"name": d.get("name"), "display_name": d.get("display_name"), "physical_column": d.get("physical_column")} for d in draft["dimensions"]],
    "metrics": [{"name": m.get("name"), "display_name": m.get("display_name"), "measure_column": m.get("measure_column")} for m in draft["metrics"]],
}, ensure_ascii=False)}

只返回 JSON，不要 Markdown。格式如下：
{{
  "business_subject": "主题中文名",
  "column_display_names": {{"字段名": "中文展示名"}},
  "dimension_display_names": {{"维度name": "中文展示名"}},
  "metric_display_names": {{"指标name": "中文展示名"}},
  "validation_questions": ["验收问题1", "验收问题2"]
}}
""".strip()
    try:
        api_key = decrypt_api_key(config.api_key) if config.api_key else None
        content = await asyncio.wait_for(
            call_llm(
                prompt=prompt,
                provider=config.provider,
                model_name=config.model_name,
                api_key=api_key,
                api_base=config.api_base,
                config_params=config.config_params,
                timeout=15.0,
            ),
            timeout=15.0,
        )
        enrichment = _extract_json_object(content)
        if enrichment:
            _merge_llm_enrichment(draft, enrichment)
        else:
            draft["warnings"].append("默认模型返回内容不是合法 JSON，已保留规则草案")
    except Exception as exc:
        draft["warnings"].append(f"默认模型润色失败，已保留规则草案：{exc}")


def _unique_name(db: Session, model: Any, attr: str, base: str) -> str:
    safe_base = _safe_name(base, "item")
    name = safe_base
    index = 2
    column = getattr(model, attr)
    while db.query(model).filter(column == name).first():
        name = f"{safe_base}_{index}"
        index += 1
    return name


def _get_or_create_category(db: Session, name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not name:
        return None, None
    category = db.query(ViewCategory).filter(ViewCategory.name == name).first()
    if not category:
        category = ViewCategory(name=name, description="由 AI 语义建模助手创建")
        db.add(category)
        db.flush()
    return category.id, category.name


def _publish_view(db: Session, datasource_id: str, draft: Dict[str, Any]) -> View:
    view_data = draft.get("view") or {}
    if not view_data.get("custom_sql"):
        raise HTTPException(status_code=400, detail="草案缺少视图 SQL")
    category_id, category_name = _get_or_create_category(db, draft.get("category_name"))
    view = View(
        name=_unique_name(db, View, "name", view_data.get("name") or "ai_view"),
        display_name=view_data.get("display_name"),
        datasource_id=datasource_id,
        category_id=category_id,
        category_name=category_name,
        view_type=ViewType.SQL,
        base_table_id=view_data.get("base_table_id"),
        custom_sql=view_data.get("custom_sql"),
        columns=view_data.get("columns") or [],
        description=view_data.get("description"),
    )
    db.add(view)
    db.flush()
    return view


def _publish_dictionaries(db: Session, view: View, draft: Dict[str, Any]) -> Dict[str, str]:
    dict_ids_by_column: Dict[str, str] = {}
    for item in draft.get("dictionaries") or []:
        target_column = item.get("target_column")
        if not target_column:
            continue
        dictionary = FieldDictionary(
            name=_unique_name(db, FieldDictionary, "name", item.get("name") or f"{target_column}_dict"),
            display_name=item.get("display_name") or f"{target_column}字典",
            source_type=DictSourceType.VIEW_REF,
            ref_view_id=view.id,
            ref_value_column=item.get("value_column") or target_column,
            ref_label_column=item.get("label_column") or item.get("value_column") or target_column,
            description=item.get("description"),
        )
        db.add(dictionary)
        db.flush()
        dict_ids_by_column[target_column] = dictionary.id
    if dict_ids_by_column:
        updated_columns = []
        for col in view.columns or []:
            col = dict(col)
            if col.get("name") in dict_ids_by_column:
                col["filterable"] = True
                col["value_config"] = {"type": "dict", "dict_id": dict_ids_by_column[col["name"]]}
            updated_columns.append(col)
        view.columns = updated_columns
    return dict_ids_by_column


def _publish_dimensions(db: Session, view: View, draft: Dict[str, Any], dict_ids_by_column: Dict[str, str]) -> Dict[str, Dimension]:
    dimensions_by_column: Dict[str, Dimension] = {}
    for item in draft.get("dimensions") or []:
        column_name = item.get("physical_column")
        if not column_name:
            continue
        value_config = None
        if column_name in dict_ids_by_column:
            value_config = {"dict_id": dict_ids_by_column[column_name], "type": "dict"}
        dimension = Dimension(
            view_id=view.id,
            name=_unique_name(db, Dimension, "name", item.get("name") or column_name),
            display_name=item.get("display_name"),
            physical_column=column_name,
            data_type=item.get("data_type") or "string",
            dimension_type=item.get("dimension_type") or "normal",
            hierarchy=item.get("hierarchy"),
            format_config=item.get("format_config"),
            value_config=value_config,
            synonyms=item.get("synonyms") or [],
            description=item.get("description"),
        )
        db.add(dimension)
        db.flush()
        dimensions_by_column[column_name] = dimension
    return dimensions_by_column


def _publish_metrics(db: Session, view: View, draft: Dict[str, Any], dimensions_by_column: Dict[str, Dimension]) -> List[Metric]:
    dimension_ids = [dimension.id for dimension in dimensions_by_column.values()]
    metrics: List[Metric] = []
    for item in draft.get("metrics") or []:
        metric = Metric(
            name=_unique_name(db, Metric, "name", item.get("name") or "metric"),
            display_name=item.get("display_name"),
            metric_type="basic",
            view_id=view.id,
            aggregation=item.get("aggregation") or "COUNT",
            calculation_method="field",
            measure_column=item.get("measure_column"),
            analysis_dimensions=dimension_ids,
            synonyms=item.get("synonyms") or [],
            unit=item.get("unit"),
            description=item.get("description"),
        )
        db.add(metric)
        db.flush()
        metrics.append(metric)
    return metrics


@router.post("/profile")
def profile_semantic_tables(request: SemanticProfileRequest, db: Session = Depends(get_db)):
    datasource = db.query(DataSource).filter(DataSource.id == request.datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    query = db.query(Dataset).filter(Dataset.datasource_id == request.datasource_id)
    datasets = query.all()
    if request.table_names:
        wanted = {_lower(name) for name in request.table_names}
        datasets = [dataset for dataset in datasets if _table_lookup_key(dataset) & wanted]
    profiles = [_profile_dataset(dataset) for dataset in datasets]
    profiles.sort(key=lambda item: item["score"], reverse=True)
    return {"datasource": datasource.to_dict(), "tables": profiles}


@router.post("/draft")
async def generate_semantic_draft(request: SemanticDraftRequest, db: Session = Depends(get_db)):
    datasource = db.query(DataSource).filter(DataSource.id == request.datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    main_dataset = _select_main_dataset(db, request.datasource_id, request.business_goal, request.main_table)
    draft = _build_rule_draft(main_dataset, datasource, request)
    related_profiles = []
    for token in request.related_tables or []:
        related = _find_dataset(db, request.datasource_id, token)
        if related and related.id != main_dataset.id:
            related_profiles.append(_profile_dataset(related, request.business_goal))
    if related_profiles:
        draft["related_datasets"] = related_profiles
        draft["warnings"].append("MVP 当前优先生成单主表 SQL 视图，相关表仅作为人工审核参考，暂不自动建 JOIN")
    if request.use_llm:
        await _enrich_with_default_model(draft, request.business_goal, db)
    return {"draft": draft, "profile": _profile_dataset(main_dataset, request.business_goal)}


@router.post("/publish")
def publish_semantic_draft(request: SemanticPublishRequest, db: Session = Depends(get_db)):
    datasource = db.query(DataSource).filter(DataSource.id == request.datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="DataSource not found")
    try:
        view = _publish_view(db, request.datasource_id, request.draft)
        dict_ids_by_column = _publish_dictionaries(db, view, request.draft)
        dimensions_by_column = _publish_dimensions(db, view, request.draft, dict_ids_by_column)
        metrics = _publish_metrics(db, view, request.draft, dimensions_by_column)
        default_time_column = (request.draft.get("view") or {}).get("default_time_column")
        if default_time_column and default_time_column in dimensions_by_column:
            view.default_date_column_id = dimensions_by_column[default_time_column].id
        if request.set_default:
            db.query(View).filter(View.is_default.is_(True)).update({"is_default": False})
            view.is_default = True
        db.commit()
        db.refresh(view)
        dictionaries = db.query(FieldDictionary).filter(FieldDictionary.ref_view_id == view.id).all()
        dimensions = db.query(Dimension).filter(Dimension.view_id == view.id).all()
        metrics = db.query(Metric).filter(Metric.view_id == view.id).all()
        return {
            "view": view.to_dict(),
            "dimensions": [dimension.to_dict() for dimension in dimensions],
            "metrics": [metric.to_dict() for metric in metrics],
            "dictionaries": [dictionary.to_dict() for dictionary in dictionaries],
            "validation_questions": request.draft.get("validation_questions") or [],
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"发布语义配置失败：{exc}") from exc
