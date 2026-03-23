"""
参数筛选和MQL生成服务
"""
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.orm import Session
import re


def filter_api_parameters(
    api_parameters_str: str,
    db: Session
) -> Dict[str, Any]:
    """
    从视图的可过滤字段中筛选API参数

    Args:
        api_parameters_str: API参数字符串（如"问题大类、问题小类、街道"）
        db: 数据库会话

    Returns:
        {
            "valid_parameters": [...],    # 有效参数
            "invalid_parameters": [...],  # 无效参数
            "parameter_mappings": {...},  # 参数映射
            "available_fields": [...]    # 所有可用的视图字段
        }
    """
    from app.models.view import View
    from app.models.field_dict import FieldDictionary

    # 1. 解析API参数字符串
    api_params = [p.strip() for p in api_parameters_str.split("、") if p.strip()]

    # 2. 获取所有视图及其可过滤字段
    views = db.query(View).all()

    # 收集所有可过滤字段
    all_filterable_fields = []
    for view in views:
        columns = view.columns or []
        for col in columns:
            # 只包含可过滤的字段
            if col.get("filterable", True):
                # 判断是否为时间字段
                field_type = col.get("type", "").lower()
                time_keywords = ["date", "time", "datetime", "timestamp"]
                is_time_field = any(kw in field_type for kw in time_keywords)
                
                all_filterable_fields.append({
                    "view_id": view.id,
                    "view_name": view.name,
                    "view_display_name": view.display_name,
                    "field_name": col.get("name"),
                    "display_name": col.get("display_name") or col.get("name"),
                    "type": col.get("type", "string"),
                    "source_column": col.get("source_column"),
                    "dict_id": col.get("dictionary_id"),
                    "value_config": col.get("value_config", {}),
                    "is_time_field": is_time_field
                })

    # 3. 筛选API参数
    valid_params = []
    invalid_params = []
    parameter_mappings = {}
    matched_fields = []

    for param_name in api_params:
        # 检查是否是时间范围参数（xxx_开始, xxx_结束 或 xxx_start, xxx_end）
        time_range_pattern = r'^(.+?)[_]?(开始|结束|start|end|from|to)$'
        match = re.match(time_range_pattern, param_name, re.IGNORECASE)
        
        if match:
            # 时间范围参数处理
            base_name = match.group(1)
            suffix = match.group(2).lower()
            range_type = None
            if suffix in ['开始', 'start', 'from']:
                range_type = 'start'
            elif suffix in ['结束', 'end', 'to']:
                range_type = 'end'
            
            # 查找对应的基础时间字段
            matched_field = None
            for field in all_filterable_fields:
                if field["is_time_field"] and (
                    field["display_name"] == base_name or 
                    field["field_name"] == base_name or
                    base_name in field["display_name"] or
                    base_name in (field.get("field_name") or "")
                ):
                    matched_field = field
                    break
            
            if matched_field and range_type:
                # 获取字典值（如果有）
                dict_values = None
                if matched_field.get("dict_id"):
                    field_dict = db.query(FieldDictionary).filter(
                        FieldDictionary.id == matched_field["dict_id"]
                    ).first()
                    if field_dict:
                        dict_values = field_dict.values

                param_entry = {
                    "name": param_name,
                    "field_name": matched_field["field_name"],
                    "display_name": f"{matched_field['display_name']}_{'开始' if range_type == 'start' else '结束'}",
                    "type": matched_field["type"],
                    "source_field": matched_field["source_column"],
                    "dict_id": matched_field.get("dict_id"),
                    "dict_values": dict_values,
                    "required": False,  # 时间范围参数默认可选
                    "view_id": matched_field["view_id"],
                    "view_name": matched_field["view_name"],
                    "is_time_range": True,
                    "range_type": range_type,
                    "base_field_name": matched_field["field_name"]
                }
                valid_params.append(param_entry)

                parameter_mappings[param_name] = {
                    "source_field": matched_field["source_column"],
                    "field_type": matched_field["type"],
                    "field_name": matched_field["field_name"],
                    "view_id": matched_field["view_id"],
                    "is_time_range": True,
                    "range_type": range_type
                }
                matched_fields.append(matched_field)
                continue
        
        # 非时间范围参数处理
        # 精确匹配
        matched_field = None
        for field in all_filterable_fields:
            if field["display_name"] == param_name or field["field_name"] == param_name:
                matched_field = field
                break

        # 模糊匹配（如果精确匹配没找到）
        if not matched_field:
            for field in all_filterable_fields:
                if (param_name in field["display_name"] or
                    field["display_name"] in param_name or
                    param_name in (field.get("field_name") or "")):
                    matched_field = field
                    break

        if matched_field:
            # 检查是否匹配到时间字段，如果是，需要拆分为开始和结束两个参数
            if matched_field["is_time_field"]:
                # 添加开始参数
                start_param_name = f"{param_name}_开始"
                dict_values = None
                if matched_field.get("dict_id"):
                    field_dict = db.query(FieldDictionary).filter(
                        FieldDictionary.id == matched_field["dict_id"]
                    ).first()
                    if field_dict:
                        dict_values = field_dict.values

                start_param_entry = {
                    "name": start_param_name,
                    "field_name": matched_field["field_name"],
                    "display_name": f"{matched_field['display_name']}_开始",
                    "type": matched_field["type"],
                    "source_field": matched_field["source_column"],
                    "dict_id": matched_field.get("dict_id"),
                    "dict_values": dict_values,
                    "required": False,
                    "view_id": matched_field["view_id"],
                    "view_name": matched_field["view_name"],
                    "is_time_range": True,
                    "range_type": "start",
                    "base_field_name": matched_field["field_name"]
                }
                valid_params.append(start_param_entry)
                parameter_mappings[start_param_name] = {
                    "source_field": matched_field["source_column"],
                    "field_type": matched_field["type"],
                    "field_name": matched_field["field_name"],
                    "view_id": matched_field["view_id"],
                    "is_time_range": True,
                    "range_type": "start"
                }

                # 添加结束参数
                end_param_name = f"{param_name}_结束"
                end_param_entry = {
                    "name": end_param_name,
                    "field_name": matched_field["field_name"],
                    "display_name": f"{matched_field['display_name']}_结束",
                    "type": matched_field["type"],
                    "source_field": matched_field["source_column"],
                    "dict_id": matched_field.get("dict_id"),
                    "dict_values": dict_values,
                    "required": False,
                    "view_id": matched_field["view_id"],
                    "view_name": matched_field["view_name"],
                    "is_time_range": True,
                    "range_type": "end",
                    "base_field_name": matched_field["field_name"]
                }
                valid_params.append(end_param_entry)
                parameter_mappings[end_param_name] = {
                    "source_field": matched_field["source_column"],
                    "field_type": matched_field["type"],
                    "field_name": matched_field["field_name"],
                    "view_id": matched_field["view_id"],
                    "is_time_range": True,
                    "range_type": "end"
                }
                matched_fields.append(matched_field)
                continue

            # 普通参数处理
            # 获取字典值（如果有）
            dict_values = None
            if matched_field.get("dict_id"):
                field_dict = db.query(FieldDictionary).filter(
                    FieldDictionary.id == matched_field["dict_id"]
                ).first()
                if field_dict:
                    dict_values = field_dict.values

            valid_params.append({
                "name": param_name,
                "field_name": matched_field["field_name"],
                "display_name": matched_field["display_name"],
                "type": matched_field["type"],
                "source_field": matched_field["source_column"],
                "dict_id": matched_field.get("dict_id"),
                "dict_values": dict_values,
                "required": True,
                "view_id": matched_field["view_id"],
                "view_name": matched_field["view_name"]
            })

            parameter_mappings[param_name] = {
                "source_field": matched_field["source_column"],
                "field_type": matched_field["type"],
                "field_name": matched_field["field_name"],
                "view_id": matched_field["view_id"]
            }

            matched_fields.append(matched_field)
        else:
            invalid_params.append(param_name)

    # 4. 确定使用的视图（如果有多个匹配，使用第一个）
    used_view_id = None
    used_view_name = None
    if matched_fields:
        used_view_id = matched_fields[0]["view_id"]
        used_view_name = matched_fields[0]["view_name"]

    return {
        "valid_parameters": valid_params,
        "invalid_parameters": invalid_params,
        "parameter_mappings": parameter_mappings,
        "available_fields": all_filterable_fields,
        "used_view_id": used_view_id,
        "used_view_name": used_view_name
    }


def generate_dynamic_mql(
    base_mql: Dict[str, Any],
    parameter_mappings: Dict[str, Any],
    valid_params: Optional[List[Dict[str, Any]]] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    根据参数映射生成动态MQL

    Args:
        base_mql: 基础MQL（由大模型生成）
        parameter_mappings: 参数映射关系
        valid_params: 有效参数的完整信息
        db: 数据库会话

    Returns:
        动态MQL对象
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[DynamicMQL] 开始生成，base_mql keys: {list(base_mql.keys()) if base_mql else 'None'}")

    # 复制基础MQL
    mql = {
        "metrics": base_mql.get("metrics", []),
        "metricDefinitions": base_mql.get("metricDefinitions", {}),
        "dimensions": base_mql.get("dimensions", []),
        "filters": list(base_mql.get("filters", [])),
        "timeConstraint": base_mql.get("timeConstraint", "true"),
        "limit": base_mql.get("limit", 1000),
        "queryResultType": base_mql.get("queryResultType", "DATA")
    }

    logger.info(f"[DynamicMQL] MQL 构建完成，keys: {list(mql.keys())}")

    # 为每个API参数生成过滤条件
    for param_name, mapping in parameter_mappings.items():
        source_field = mapping.get("source_field")
        if source_field:
            # 使用源字段名生成过滤条件
            filter_condition = f"[{source_field}] = {{{{{param_name}}}}}"
            mql["filters"].append(filter_condition)

    return mql


def generate_api_info(
    config_id: str,
    name: str,
    parameter_mappings: Dict[str, Any],
    target_format_example: Any,
    mql_template: Dict[str, Any]
) -> Dict[str, Any]:
    """
    生成API端点信息

    Args:
        config_id: 配置ID
        name: 配置名称
        parameter_mappings: 参数映射
        target_format_example: 目标格式示例
        mql_template: MQL模板

    Returns:
        API信息字典
    """
    # 生成请求体参数定义
    properties = {}
    required = []

    for field_name, mapping in parameter_mappings.items():
        # 获取原始参数名（用户输入的参数名）
        param_name = mapping.get("param_name", field_name)
        field_type = mapping.get("field_type", "string")
        
        # 检查是否是时间范围参数
        is_time_range = mapping.get("is_time_range", False)
        
        # 转换为JSON Schema类型
        json_type = "string"
        if field_type in ["int", "integer", "number", "float"]:
            json_type = "number"
        elif field_type == "boolean":
            json_type = "boolean"

        # 构建描述信息，对于时间范围参数添加额外说明
        description = f"API参数: {param_name}"
        if is_time_range:
            range_type = mapping.get("range_type", "")
            display_name = mapping.get("display_name", param_name)
            description = f"时间范围参数: {display_name}"

        properties[param_name] = {
            "type": json_type,
            "description": description
        }
        # 时间范围参数默认可选，其他参数根据required字段决定
        if not is_time_range or mapping.get("required", False):
            required.append(param_name)

    api_info = {
        "endpoint": f"/api/v1/data-format/custom/{config_id}",
        "method": "POST",
        "description": name,
        "parameters": [
            {
                "name": mapping.get("param_name", field_name),
                "sourceField": mapping.get("source_field"),
                "fieldName": mapping.get("field_name"),
                "type": mapping.get("field_type", "string"),
                "displayName": mapping.get("display_name", name),
                "required": mapping.get("required", True),
                "isTimeRange": mapping.get("is_time_range", False),
                "rangeType": mapping.get("range_type"),
                "baseFieldName": mapping.get("base_field_name"),
                "dictValues": mapping.get("dict_values"),
                "viewName": mapping.get("view_name")
            }
            for field_name, mapping in parameter_mappings.items()
        ],
        "parameterConfig": {
            name: {
                "sourceField": mapping.get("source_field"),
                "fieldType": mapping.get("field_type"),
                "fieldName": mapping.get("field_name"),
                "displayName": mapping.get("display_name", name),
                "dictValues": mapping.get("dict_values"),
                "viewName": mapping.get("view_name"),
                "required": mapping.get("required", True),
                # 添加paramName字段，用于前端请求时作为参数key
                "paramName": mapping.get("param_name", name),
                # 添加时间范围相关字段
                "isTimeRange": mapping.get("is_time_range", False),
                "rangeType": mapping.get("range_type"),
                "baseFieldName": mapping.get("base_field_name")
            }
            for name, mapping in parameter_mappings.items()
        },
        "requestBody": {
            "type": "object",
            "properties": properties,
            "required": required
        },
        "responseBody": {
            "type": "array",
            "items": target_format_example if isinstance(target_format_example, list) else [target_format_example]
        },
        "mqlTemplate": mql_template,
        "example": {
            "request": {
                mapping.get("param_name", field_name): (
                    "2023-01-01" if mapping.get("is_time_range") else "示例值"
                )
                for field_name, mapping in parameter_mappings.items()
            },
            "response": {
                "data": target_format_example if isinstance(target_format_example, list) else [target_format_example]
            }
        }
    }

    return api_info


def save_format_config(
    natural_language: str,
    target_format_example: Dict[str, Any],
    api_parameters_str: str,
    generation_result: Dict[str, Any],
    used_view_id: Optional[str],
    db: Session
) -> Any:
    """
    保存数据格式配置

    Args:
        natural_language: 自然语言查询
        target_format_example: 目标格式示例
        api_parameters_str: API参数字符串
        generation_result: 大模型生成结果
        used_view_id: 使用的视图ID
        db: 数据库会话

    Returns:
        保存的配置对象
    """
    from app.models.data_format_config import DataFormatConfig
    import uuid
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[SaveConfig] 开始保存配置，target_format_example type: {type(target_format_example)}")

    # 创建配置
    config = DataFormatConfig(
        id=str(uuid.uuid4()),
        name=f"配置_{natural_language[:20]}",
        natural_language=natural_language,
        target_format_example=target_format_example,
        api_parameters_str=api_parameters_str,
        transform_script=generation_result.get("transformScript"),
        parameter_mappings=generation_result.get("parameterMappings"),
        mql_template=generation_result.get("mqlTemplate"),
        view_id=used_view_id,
        status="validated"
    )


    logger.info(f"[SaveConfig] 配置对象创建成功，id: {config.id}")

    try:
        # 生成API信息
        logger.info(f"[SaveConfig] 生成API信息")
        api_info = generate_api_info(
            config_id=config.id,
            name=config.name,
            parameter_mappings=_convert_param_mappings(generation_result.get("parameterMappings", [])),
            target_format_example=target_format_example,
            mql_template=generation_result.get("mqlTemplate", {})
        )
        config.generated_api = api_info

        logger.info(f"[SaveConfig] 保存到数据库")
        db.add(config)
        db.commit()
        db.refresh(config)

        logger.info(f"[SaveConfig] 保存成功")
        return config
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"[SaveConfig] 保存配置失败: {e}\n{error_detail}")
        raise


def _convert_param_mappings(param_mappings: Union[List[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    """
    转换参数映射格式（从数组转字典，或保持字典格式）

    支持两种输入格式：
    1. 数组格式（大模型生成）：[{"name": "param1", "sourceField": "field1", "type": "string"}]
    2. 字典格式（数据库匹配）：{"param1": {"source_field": "field1", "field_type": "string"}}
    """
    # 如果已经是字典格式，直接返回（确保键值对格式正确）
    if isinstance(param_mappings, dict):
        result = {}
        for name, mapping in param_mappings.items():
            if isinstance(mapping, dict):
                result[name] = {
                    "source_field": mapping.get("source_field"),
                    "field_type": mapping.get("field_type", "string"),
                    # 保留param_name字段
                    "param_name": mapping.get("param_name")
                }
        return result

    # 如果是数组格式，转换为字典
    result = {}
    for mapping in param_mappings:
        name = mapping.get("name")
        if name:
            result[name] = {
                "source_field": mapping.get("sourceField"),
                "field_type": mapping.get("type", "string")
            }
    return result
