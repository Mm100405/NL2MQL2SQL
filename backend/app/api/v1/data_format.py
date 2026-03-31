"""
数据格式配置API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import logging
import json

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.data_format_config import DataFormatConfig
from app.services.transform_generator import generate_transform_config
from app.services.sandbox_validator import validate_transform_script, SandboxValidator
from app.services.parameter_filter import (
    filter_api_parameters,
    generate_dynamic_mql,
    save_format_config,
    generate_api_info
)
from app.services.query_executor import convert_decimal

router = APIRouter()


# ============ Schemas ============
class ExistingQueryResult(BaseModel):
    """前置查询结果"""
    columns: List[str]
    data: List[List[Any]]
    total_count: int
    execution_time: int

class GenerateConfigRequest(BaseModel):
    """生成配置请求"""
    natural_language: str
    target_format_example: Union[Dict[str, Any], List[Dict[str, Any]]]  # 支持对象或数组
    api_parameters: str  # 用"、"分隔的字符串
    # 可选的前置查询结果，避免重复执行
    existing_mql: Optional[Dict[str, Any]] = None  # 前面 generate-mql 的返回 mql
    existing_sql: Optional[str] = None  # 前面 mql2sql 的返回 sql
    existing_query_result: Optional[ExistingQueryResult] = None  # 前面 execute 的返回结果（包含样本数据）
    view_id: Optional[str] = None  # 结果面板绑定的视图ID


class ValidateScriptRequest(BaseModel):
    """验证脚本请求"""
    script: str
    test_data: Optional[Dict[str, Any]] = None


class CustomApiRequest(BaseModel):
    """自定义API请求（动态参数）"""
    # 动态参数将在运行时定义，此处不声明固定字段


class UpdateConfigRequest(BaseModel):
    """更新配置请求"""
    name: Optional[str] = None
    status: Optional[str] = None


# ============ Internal Functions ============
async def _process_generation(
    natural_language: str,
    target_format_example: Any,
    api_parameters: str,
    db: Session,
    existing_mql: Optional[Dict[str, Any]] = None,
    existing_sql: Optional[str] = None,
    existing_query_result: Optional[ExistingQueryResult] = None,
    view_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理配置生成的核心逻辑（生成、验证、筛选）

    Returns:
        {
            "success": bool,
            "error": str (可选),
            "transformScript": str,
            "dynamicMql": dict,
            "filterResult": dict,
            "validationError": str (可选),
            "suggestion": str (可选),
            "phase": str (可选)
        }
    """
    # 处理传入的查询结果，转换Decimal类型
    if existing_query_result:
        existing_query_result_dict = {
            "columns": existing_query_result.columns,
            "data": convert_decimal(existing_query_result.data),
            "total_count": existing_query_result.total_count,
            "execution_time": existing_query_result.execution_time
        }
    else:
        existing_query_result_dict = None

    # 1. 调用大模型生成转换脚本和配置
    generation_result = await generate_transform_config(
        natural_language=natural_language,
        target_format_example=target_format_example,
        api_parameters=api_parameters,
        db=db,
        existing_mql=existing_mql,
        existing_sql=existing_sql,
        existing_query_result=existing_query_result_dict
    )

    if not generation_result.get("success"):
        return {
            "success": False,
            "error": generation_result.get("error", "生成失败"),
            "details": generation_result.get("details")
        }

    transform_script = generation_result.get("transformScript")
    base_mql = generation_result.get("baseMql", {})

    # 2. 沙箱验证转换脚本
    validation_result = validate_transform_script(
        script=transform_script,
        test_data=generation_result.get("sourceDataSample")
    )

    if not validation_result.get("valid"):
        return {
            "success": False,
            "error": "转换脚本验证失败",
            "validationError": validation_result.get("error"),
            "suggestion": validation_result.get("suggestion"),
            "phase": validation_result.get("phase"),
            "transformScript": transform_script
        }

    # 3. 筛选API参数
    filter_result = filter_api_parameters(
        api_parameters_str=api_parameters,
        db=db
    )
    
    # 如果 filter_result 中没有 used_view_id，使用传入的 view_id
    if not filter_result.get("used_view_id") and view_id:
        filter_result["used_view_id"] = view_id
        logger.info(f"[ProcessGeneration] 使用传入的 view_id: {view_id}")

    # 4. 生成动态MQL
    valid_params = filter_result.get("valid_parameters", [])
    dynamic_mql = generate_dynamic_mql(
        base_mql=base_mql,
        parameter_mappings=filter_result.get("parameter_mappings", {}),
        valid_params=valid_params,
        db=db
    )

    return {
        "success": True,
        "apiName": generation_result.get("apiName"),
        "transformScript": transform_script,
        "dynamicMql": dynamic_mql,
        "filterResult": filter_result
    }


# ============ Routes ============
@router.post("/generate-config")
async def generate_format_config(
    request: GenerateConfigRequest,
    db: Session = Depends(get_db)
):
    """
    根据用户输入生成数据格式配置

    流程：
    1. 调用大模型生成转换脚本和参数映射
    2. 沙箱验证转换脚本
    3. 筛选API参数（从视图可过滤字段中匹配）
    4. 生成动态MQL
    5. 保存配置并生成API

    支持传入前置查询结果：
    - existing_mql: 前面 generate-mql 的返回，避免重复生成 MQL
    - existing_sql: 前面 mql2sql 的返回，避免重复转换为 SQL
    - existing_query_result: 前面 execute 的返回，避免重复查询获取样本数据
    """
    try:
        logger.info(f"收到生成配置请求")
        logger.info(f"  natural_language={request.natural_language}")
        logger.info(f"  target_format_example type: {type(request.target_format_example)}")

        if request.existing_query_result:
            logger.info(f"  existing_query_result.columns: {request.existing_query_result.columns}")

        # 调用内部处理函数
        result = await _process_generation(
            natural_language=request.natural_language,
            target_format_example=request.target_format_example,
            api_parameters=request.api_parameters,
            db=db,
            existing_mql=request.existing_mql,
            existing_sql=request.existing_sql,
            existing_query_result=request.existing_query_result,
            view_id=request.view_id
        )

        # 验证失败
        if not result.get("success"):
            if result.get("error") == "转换脚本验证失败":
                # 保存失败状态
                config = DataFormatConfig(
                    name=f"配置_{request.natural_language[:20]}",
                    natural_language=request.natural_language,
                    target_format_example=request.target_format_example,
                    api_parameters_str=request.api_parameters,
                    transform_script=result.get("transformScript"),
                    status="failed",
                    error_message=result.get("validationError")
                )
                db.add(config)
                db.commit()

                return {
                    "success": False,
                    "error": result.get("error"),
                    "validationError": result.get("validationError"),
                    "suggestion": result.get("suggestion"),
                    "phase": result.get("phase")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error"),
                    "details": result.get("details")
                }

        # 成功，保存配置
        filter_result = result["filterResult"]
        parameter_mappings = filter_result.get("parameter_mappings", {})
        valid_params = filter_result.get("valid_parameters", [])
        api_name = result.get("apiName")  # 获取LLM生成的接口名称

        # 构建包含完整field信息的parameterMappings（使用参数名作为key，支持时间范围参数）
        full_parameter_mappings = {}
        for param in valid_params:
            name = param["name"]  # 使用参数名作为key（可能是 create_time_开始 或 create_time_结束）
            mapping = parameter_mappings.get(name, {})
            field_name = mapping.get("field_name", name)
            
            full_parameter_mappings[name] = {
                "source_field": mapping.get("source_field"),
                "field_type": mapping.get("field_type"),
                "field_name": field_name,
                "view_id": mapping.get("view_id"),
                "display_name": param.get("display_name", name),
                "dict_values": param.get("dict_values"),
                "view_name": param.get("view_name"),
                "required": param.get("required", True),
                # 保留原始参数名
                "param_name": name,
                # 保留时间范围相关字段
                "is_time_range": mapping.get("is_time_range", False),
                "range_type": mapping.get("range_type"),
                "base_field_name": param.get("base_field_name")
            }

        config = save_format_config(
            natural_language=request.natural_language,
            target_format_example=request.target_format_example,
            api_parameters_str=request.api_parameters,
            generation_result={
                "transformScript": result["transformScript"],
                "parameterMappings": full_parameter_mappings,
                "mqlTemplate": result["dynamicMql"],
                "apiName": api_name
            },
            used_view_id=filter_result.get("used_view_id"),
            db=db,
            api_name=api_name
        )

        return {
            "success": True,
            "configId": config.id,
            "apiName": config.name,
            "apiEndpoint": config.generated_api.get("endpoint") if config.generated_api else None,
            "parameters": filter_result.get("valid_parameters", []),
            "invalidParameters": filter_result.get("invalid_parameters", []),
            "transformScript": result["transformScript"],
            "mqlTemplate": result["dynamicMql"],
            "validation": {
                "passed": True,
                "phase": "all"
            }
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"生成配置时出错: {str(e)}\n{error_detail}")
        print(f"[ERROR] 生成配置时出错: {str(e)}\n{error_detail}")
        return {
            "success": False,
            "error": f"生成配置时出错: {str(e)}",
            "detail": error_detail
        }


@router.post("/validate-script")
async def validate_script_endpoint(
    request: ValidateScriptRequest,
    db: Session = Depends(get_db)
):
    """
    验证转换脚本（用于实时预览）
    """
    result = validate_transform_script(
        script=request.script,
        test_data=request.test_data
    )

    return result


@router.get("/configs")
async def list_configs(
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取用户的数据格式配置列表
    """
    query = db.query(DataFormatConfig)

    if user_id:
        query = query.filter(DataFormatConfig.user_id == user_id)

    configs = query.order_by(DataFormatConfig.created_at.desc()).all()

    return {
        "configs": [c.to_dict() for c in configs]
    }


@router.post("/configs/{config_id}/regenerate")
async def regenerate_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    重新生成数据格式配置

    流程：
    1. 获取旧配置信息
    2. 调用生成逻辑（重新生成转换脚本和参数映射）
    3. 更新配置
    """
    try:
        # 1. 获取旧配置
        old_config = db.query(DataFormatConfig).filter(
            DataFormatConfig.id == config_id
        ).first()

        if not old_config:
            raise HTTPException(status_code=404, detail="配置不存在")

        logger.info(f"[Regenerate] 重新生成配置，config_id={config_id}")

        # 2. 调用内部处理函数（使用旧的MQL和SQL以提高效率）
        # 使用旧的MQL可以避免重复的NL解析
        # 使用旧的SQL可以避免重复的MQL到SQL转换
        result = await _process_generation(
            natural_language=old_config.natural_language,
            target_format_example=old_config.target_format_example,
            api_parameters=old_config.api_parameters_str,
            db=db,
            existing_mql=old_config.mql_template,  # 使用旧的MQL
            existing_sql=None,  # SQL不需要保存，可以从MQL重新生成
            existing_query_result=None  # 查询结果重新获取
        )

        # 验证失败
        if not result.get("success"):
            if result.get("error") == "转换脚本验证失败":
                # 更新为失败状态
                old_config.transform_script = result.get("transformScript")
                old_config.status = "failed"
                old_config.error_message = result.get("validationError")
                db.commit()
                db.refresh(old_config)

                return {
                    "success": False,
                    "error": result.get("error"),
                    "validationError": result.get("validationError"),
                    "suggestion": result.get("suggestion"),
                    "phase": result.get("phase")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error"),
                    "details": result.get("details")
                }

        # 成功，更新配置
        filter_result = result["filterResult"]
        parameter_mappings = filter_result.get("parameter_mappings", {})
        valid_params = filter_result.get("valid_parameters", [])
        api_name = result.get("apiName")  # 获取LLM生成的接口名称

        # 构建包含完整field信息的parameterMappings（使用参数名作为key，支持时间范围参数）
        full_parameter_mappings = {}
        for param in valid_params:
            name = param["name"]  # 使用参数名作为key（可能是 create_time_开始 或 create_time_结束）
            mapping = parameter_mappings.get(name, {})
            field_name = mapping.get("field_name", name)
            
            full_parameter_mappings[name] = {
                "source_field": mapping.get("source_field"),
                "field_type": mapping.get("field_type"),
                "field_name": field_name,
                "view_id": mapping.get("view_id"),
                "display_name": param.get("display_name", name),
                "dict_values": param.get("dict_values"),
                "view_name": param.get("view_name"),
                "required": param.get("required", True),
                # 保留原始参数名
                "param_name": name,
                # 保留时间范围相关字段
                "is_time_range": mapping.get("is_time_range", False),
                "range_type": mapping.get("range_type"),
                "base_field_name": param.get("base_field_name")
            }

        # 更新配置，包括名称
        old_config.name = api_name or old_config.name  # 使用LLM生成的新名称
        old_config.transform_script = result["transformScript"]
        old_config.parameter_mappings = full_parameter_mappings
        old_config.mql_template = result["dynamicMql"]

        # 重新生成API信息
        api_info = generate_api_info(
            config_id=config_id,
            name=api_name or old_config.name,  # 使用新的名称
            parameter_mappings=filter_result.get("parameter_mappings", {}),
            target_format_example=old_config.target_format_example,
            mql_template=result["dynamicMql"]
        )
        old_config.generated_api = api_info
        old_config.status = "validated"
        old_config.error_message = None

        db.commit()
        db.refresh(old_config)

        logger.info(f"[Regenerate] 重新生成成功")

        return {
            "success": True,
            "configId": old_config.id,
            "apiEndpoint": old_config.generated_api.get("endpoint") if old_config.generated_api else None,
            "parameters": filter_result.get("valid_parameters", []),
            "invalidParameters": filter_result.get("invalid_parameters", []),
            "transformScript": result["transformScript"],
            "mqlTemplate": result["dynamicMql"],
            "validation": {
                "passed": True,
                "phase": "all"
            }
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"重新生成配置时出错: {str(e)}\n{error_detail}")
        print(f"[ERROR] 重新生成配置时出错: {str(e)}\n{error_detail}")
        return {
            "success": False,
            "error": f"重新生成配置时出错: {str(e)}",
            "detail": error_detail
        }


@router.get("/configs/{config_id}")
async def get_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    获取单个配置详情
    """
    config = db.query(DataFormatConfig).filter(
        DataFormatConfig.id == config_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    return config.to_dict()


@router.put("/configs/{config_id}")
async def update_config(
    config_id: str,
    request: UpdateConfigRequest,
    db: Session = Depends(get_db)
):
    """
    更新配置
    """
    config = db.query(DataFormatConfig).filter(
        DataFormatConfig.id == config_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    if request.name is not None:
        config.name = request.name
    if request.status is not None:
        config.status = request.status

    db.commit()
    db.refresh(config)

    return config.to_dict()


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    删除配置
    """
    config = db.query(DataFormatConfig).filter(
        DataFormatConfig.id == config_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    db.delete(config)
    db.commit()

    return {"message": "删除成功"}


@router.post("/custom/{config_id}")
async def call_custom_api(
    config_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    调用自定义API

    Args:
        config_id: 配置ID
        request: API参数

    Returns:
        转换后的数据结果
    """
    from app.services.mql_engine import mql_to_sql
    from app.services.query_executor import execute_query
    import json

    # 1. 获取配置
    config = db.query(DataFormatConfig).filter(
        DataFormatConfig.id == config_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    if config.status != "validated":
        raise HTTPException(status_code=400, detail="配置未通过验证")

    # 2. 获取MQL模板并构建 MQL（filters 使用 MQL Engine V2 结构化格式）
    mql_template = config.mql_template or {}
    template_filters = mql_template.get("filters", []) or []

    # 规范化模板 filters：与 MQL Engine V2 FilterValidator 一致
    # V2 使用 extract_field_refs（字符串）和 extract_field_refs_from_structured（dict）校验
    import re as _re

    def _has_field_ref(expr: str) -> bool:
        """V2 extract_field_refs: 匹配 [字段名] 格式"""
        return bool(_re.findall(r"\[([^\]]+)\]", expr))

    def _has_structured_field_ref(condition) -> bool:
        """V2 extract_field_refs_from_structured: 递归提取 dict 条件中的 field"""
        if not isinstance(condition, dict):
            return False
        if "field" in condition:
            return True
        for sub in condition.get("conditions", []):
            if _has_structured_field_ref(sub):
                return True
        return False

    base_conditions = []
    if isinstance(template_filters, dict):
        # V2 结构化格式 {"operator": "AND", "conditions": [...]}，提取 conditions
        base_conditions = list(template_filters.get("conditions", []))
    elif isinstance(template_filters, list):
        for f in template_filters:
            if isinstance(f, dict):
                # 结构化条件：用 extract_field_refs_from_structured 校验是否含有效 field
                if _has_structured_field_ref(f):
                    base_conditions.append(f)
            elif isinstance(f, str) and f.strip():
                # 字符串条件：用 extract_field_refs 校验是否含有效 [field] 引用
                if _has_field_ref(f):
                    base_conditions.append(f)
                # 无 field 引用的无效字符串（如 "operator", "conditions"）自动跳过

    mql = {
        "metrics": mql_template.get("metrics", []),
        "metricDefinitions": mql_template.get("metricDefinitions", {}),
        "dimensions": mql_template.get("dimensions", []),
        "filters": base_conditions,
        "timeConstraint": mql_template.get("timeConstraint", "true"),
        "limit": mql_template.get("limit", 1000),
        "queryResultType": mql_template.get("queryResultType", "DATA")
    }

    # 注意：不再单独调用 correct_mql，mql_to_sql 内部的 MQLTranslator.translate()
    # 已调用 MQLCorrector.correct_and_validate() 进行验证和修正

    # 使用parameter_mappings生成动态过滤条件（V2 结构化格式）
    parameter_mappings = config.parameter_mappings or {}

    if parameter_mappings and isinstance(parameter_mappings, dict):
        # 先收集所有时间范围参数，按base_field_name分组
        time_range_params = {}
        regular_params = []
        
        for field_name, param_info in parameter_mappings.items():
            param_name = param_info.get("param_name")
            is_time_range = param_info.get("is_time_range", False)
            
            # 兼容性检查：如果is_time_range不存在，通过参数名判断
            if not is_time_range and param_name:
                time_range_pattern = r'^(.+?)[_]?(开始|结束|start|end|from|to)$'
                match = _re.match(time_range_pattern, param_name, _re.IGNORECASE)
                is_time_range = match is not None
            
            if is_time_range:
                base_field_name = param_info.get("base_field_name")
                range_type = param_info.get("range_type")
                
                # 如果没有显式的base_field_name和range_type，从param_name解析
                if param_name and (not base_field_name or not range_type):
                    time_range_pattern = r'^(.+?)[_]?(开始|结束|start|end|from|to)$'
                    match = _re.match(time_range_pattern, param_name, _re.IGNORECASE)
                    if match:
                        base_field_name = base_field_name or match.group(1)
                        suffix = match.group(2).lower()
                        range_type = range_type or ('start' if suffix in ['开始', 'start', 'from'] else 'end')
                
                if base_field_name not in time_range_params:
                    time_range_params[base_field_name] = {"start": None, "end": None, "source_field": param_info.get("source_field") or param_info.get("field_name", field_name)}
                
                if param_name and param_name in request and request[param_name]:
                    time_range_params[base_field_name][range_type] = request[param_name]
                    source_field = param_info.get("source_field") or param_info.get("field_name", field_name)
                    time_range_params[base_field_name]["source_field"] = source_field
            else:
                # 普通参数
                regular_params.append((field_name, param_info))
        
        # 处理时间范围参数（V2 结构化条件格式）
        for base_field_name, time_range in time_range_params.items():
            source_field = time_range["source_field"] or base_field_name
            start_value = time_range["start"]
            end_value = time_range["end"]
            
            if start_value and end_value:
                mql["filters"].append({"field": source_field, "op": ">=", "value": start_value})
                mql["filters"].append({"field": source_field, "op": "<=", "value": end_value})
            elif start_value:
                mql["filters"].append({"field": source_field, "op": ">=", "value": start_value})
            elif end_value:
                mql["filters"].append({"field": source_field, "op": "<=", "value": end_value})
        
        # 处理普通参数（V2 结构化条件格式）
        for field_name, param_info in regular_params:
            param_name = param_info.get("param_name")
            if param_name and param_name in request:
                field_type = param_info.get("field_type", "string")
                param_value = request[param_name]
                
                if not param_value:
                    continue
                
                source_field = param_info.get("source_field") or param_info.get("field_name", field_name)
                
                # 数字类型转换为数值
                if field_type in ["number", "int", "integer", "float"]:
                    try:
                        param_value = float(param_value)
                        if param_value == int(param_value):
                            param_value = int(param_value)
                    except (ValueError, TypeError):
                        pass
                
                mql["filters"].append({"field": source_field, "op": "=", "value": param_value})

    # 将 filters 统一为 V2 标准结构化格式
    all_filters = mql["filters"]
    if all_filters:
        if all(isinstance(f, dict) for f in all_filters):
            # 全部为 dict，包装为 V2 结构化格式
            mql["filters"] = {"operator": "AND", "conditions": all_filters}
        # 否则保持混合列表格式（V2 AST Builder 同样支持）
    else:
        mql["filters"] = []

    # 3. 执行MQL查询
    try:
        sql_result = await mql_to_sql(mql, db)
        sql = sql_result.get("sql", "")
        datasource_id = sql_result.get("datasources", [None])[0]

        if not datasource_id or not sql:
            return {
                "data": [],
                "message": "无法获取数据源"
            }

        query_result = await execute_query(sql, datasource_id, limit=1000, db=db)

        # 4. 应用转换脚本（使用Node.js执行JavaScript）
        # 构建source_data格式
        source_data = {
            "columns": query_result.get("columns", []),
            "data": query_result.get("data", [])
        }
        
        # 使用SandboxValidator执行JavaScript转换脚本
        validator = SandboxValidator(timeout=30)
        transform_result = validator._execute_mock(config.transform_script, source_data)
        
        if not transform_result["success"]:
            raise HTTPException(status_code=500, detail=f"转换脚本执行失败: {transform_result.get('error')}")
        
        transformed_data = transform_result.get("result", [])

        # return {
        #     "data": transformed_data,
        #     "columns": query_result.get("columns", []),
        #     "total": query_result.get("total_count", 0)
        # }

        return transformed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行查询失败: {str(e)}")


@router.get("/custom/{config_id}/docs")
async def get_custom_api_docs(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    获取自定义API文档
    """
    config = db.query(DataFormatConfig).filter(
        DataFormatConfig.id == config_id
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    return {
        "configId": config.id,
        "name": config.name,
        "api": config.generated_api,
        "status": config.status
    }


@router.get("/parameters/available")
async def get_available_parameters(
    view_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取视图的所有可过滤参数
    """
    from app.models.view import View
    from app.models.field_dict import FieldDictionary

    views = db.query(View).all()

    if view_id:
        views = [v for v in views if v.id == view_id]

    all_params = []

    for view in views:
        columns = view.columns or []
        for col in columns:
            if col.get("filterable", True):
                param = {
                    "name": col.get("display_name") or col.get("name"),
                    "fieldName": col.get("name"),
                    "type": col.get("type", "string"),
                    "viewId": view.id,
                    "viewName": view.name
                }

                # 获取字典值
                dict_id = col.get("dictionary_id")
                if dict_id:
                    field_dict = db.query(FieldDictionary).filter(
                        FieldDictionary.id == dict_id
                    ).first()
                    if field_dict:
                        param["dictionary"] = {
                            "id": dict_id,
                            "values": field_dict.values
                        }

                all_params.append(param)

    return {
        "parameters": all_params
    }


# ============ External Integration APIs ============
# 外部系统对接接口，供第三方系统调用

@router.get("/external/categories")
async def get_external_categories(
    db: Session = Depends(get_db)
):
    """
    获取API分类类别树（供外部系统对接）
    
    返回视图分类和视图组成的树形结构，只包含有实际数据的节点：
    - 视图节点：只有当该视图下有接口数据时才显示
    - 分类节点：只有当该分类下有视图或子分类时才显示（递归检查）
    
    Returns:
        [
            {
                "id": "1",
                "name": "城管接口",
                "parentId": null,
                "children": [
                    {
                        "id": "view_xxx",
                        "name": "事件类型视图",
                        "parentId": "1",
                        "children": null
                    }
                ]
            }
        ]
    """
    from app.models.view import View
    from app.models.view_category import ViewCategory
    
    # 1. 查询所有有接口的视图ID
    config_view_ids = db.query(DataFormatConfig.view_id).filter(
        DataFormatConfig.status == "validated"
    ).distinct().all()
    valid_view_ids = {str(vid[0]) for vid in config_view_ids if vid[0]}
    
    # 2. 获取所有分类
    categories = db.query(ViewCategory).all()
    
    # 3. 获取所有视图
    views = db.query(View).all()
    
    # 4. 按分类ID组织视图（只保留有接口的视图）
    views_by_category = {}
    views_no_category = []
    
    for view in views:
        # 只添加有接口的视图
        if str(view.id) not in valid_view_ids:
            continue
        
        if view.category_id:
            if view.category_id not in views_by_category:
                views_by_category[view.category_id] = []
            views_by_category[view.category_id].append({
                "id": f"view_{view.id}",
                "name": view.display_name or view.name,
                "parentId": view.category_id,
                "children": None
            })
        else:
            views_no_category.append({
                "id": f"view_{view.id}",
                "name": view.display_name or view.name,
                "parentId": None,
                "children": None
            })
    
    # 5. 构建分类树（递归过滤空分类）
    def build_category_tree(categories: list) -> list:
        """构建分类树，只保留有实际数据的分类"""
        # 找出根分类
        root_categories = [c for c in categories if not c.parent_id]
        
        def build_node(category):
            """构建分类节点，返回 None 表示该分类应该被过滤"""
            # 找出子分类
            children_categories = [c for c in categories if c.parent_id == category.id]
            
            # 构建子节点：先添加子分类，再添加视图
            children = []
            
            # 添加子分类（递归构建，过滤掉返回 None 的子分类）
            for child_cat in children_categories:
                child_node = build_node(child_cat)
                if child_node:  # 只添加非空的子分类
                    children.append(child_node)
            
            # 添加该分类下的视图
            if category.id in views_by_category:
                children.extend(views_by_category[category.id])
            
            # 如果没有任何子节点，返回 None（表示该分类应该被过滤）
            if not children:
                return None
            
            node = {
                "id": category.id,
                "name": category.name,
                "parentId": category.parent_id,
                "children": children if children else None
            }
            
            return node
        
        tree = []
        for root in root_categories:
            node = build_node(root)
            if node:  # 只添加非空的根分类
                tree.append(node)
        
        return tree
    
    # 6. 构建最终结果
    result = build_category_tree(categories)
    
    # 7. 添加没有分类的视图作为一级节点
    if views_no_category:
        result.extend(views_no_category)
    
    return result


@router.get("/external/apis")
async def get_external_apis_by_category(
    categoryId: Optional[str] = None,
    name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    根据视图ID获取接口列表（供外部系统对接）
    
    Args:
        categoryId: 视图ID（格式：view_xxx），可选
        - 如果是分类ID：返回空数组（接口在视图级别，不在分类级别）
        - 如果是视图ID（view_xxx）：返回该视图下的接口列表
        - 如果不传：返回所有接口
        
        name: 接口名称，可选，支持模糊搜索
        - 如果提供，则按接口名称模糊匹配
        
    注意：每次只返回下一级，不递归查找
    
    Returns:
        [
            {
                "id": "23cce64e5ce808b7036fe82726b5f120",
                "url": "/api/v1/data-format/custom/xxx",
                "categoryName": "事件类型接口",
                "categoryId": "17660cdc67933d6accf4561f4b504e7d",
                "name": "事件类型树接口",
                "method": 1,
                "header": null,
                "bodyType": 1,
                "queryParams": null,
                "pathParams": null,
                "body": null,
                "parentId": null,
                "timeout": null,
                "docUrl": null
            }
        ]
    """
    from app.models.view import View
    
    # 1. 如果不传categoryId，直接返回空数组
    if not categoryId:
        return []
    
    # 2. 如果是分类ID，直接返回空数组（接口在视图级别）
    if not categoryId.startswith("view_"):
        return []
    
    # 3. 查询API配置
    query = db.query(DataFormatConfig).filter(
        DataFormatConfig.status == "validated"
    )
    
    # 4. 过滤该视图下的接口
    view_id = categoryId.replace("view_", "")
    query = query.filter(DataFormatConfig.view_id == view_id)
    
    # 5. 如果提供了name参数，添加模糊搜索条件
    if name:
        query = query.filter(DataFormatConfig.name.ilike(f"%{name}%"))
    
    configs = query.all()
    
    # 3. 获取视图和分类信息
    views = db.query(View).all()
    view_map = {v.id: v for v in views}
    
    # 4. 构建返回结果
    result = []
    for config in configs:
        view = view_map.get(config.view_id)
        
        # 处理 parameter_mappings（可能是JSON字符串或列表）
        parameter_mappings = config.parameter_mappings
        if isinstance(parameter_mappings, str):
            try:
                parameter_mappings = json.loads(parameter_mappings)
            except:
                parameter_mappings = []
        elif parameter_mappings is None:
            parameter_mappings = []
        
        # 构建请求体示例
        body_example = {}
        if parameter_mappings:
            for mapping in parameter_mappings:
                if isinstance(mapping, dict):
                    param_name = mapping.get("param_name", "")
                    if param_name:
                        body_example[param_name] = ""
        
        # 处理 generated_api（可能是JSON字符串或字典）
        generated_api = config.generated_api
        if isinstance(generated_api, str):
            try:
                generated_api = json.loads(generated_api)
            except:
                generated_api = None
        
        result.append({
            "id": config.id,
            "url": generated_api.get("endpoint") if isinstance(generated_api, dict) else None,
            "categoryName": view.display_name or view.name if view else None,
            "categoryId": f"view_{view.id}" if view else None,
            "name": config.name,
            "method": 1,  # POST
            "header": {"Content-Type": "application/json"} if body_example else None,
            "bodyType": 1 if body_example else None,  # JSON
            "queryParams": None,
            "pathParams": None,
            "body": body_example if body_example else None,
            "parentId": None,
            "timeout": None,
            "docUrl": None
        })
    
    return result


@router.get("/external/detail/{config_id}")
async def get_external_api_detail(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    获取单个API接口详情（供外部系统对接）
    
    Returns:
        {
            "hasError": false,
            "result": {
                "url": "API端点URL",
                "sourceType": null,
                "sourceId": null,
                "categoryName": "分类名称",
                "categoryId": "分类ID",
                "name": "接口名称",
                "method": "POST",
                "bodyType": "JSON",
                "header": {},
                "queryParams": {},
                "pathParams": {},
                "body": {},
                "parentId": null,
                "timeout": null,
                "createTime": "2024-01-01 00:00:00"
            },
            "message": null,
            "tag": null,
            "totalCount": 1
        }
    """
    from app.models.view import View
    
    # 1. 获取配置
    config = db.query(DataFormatConfig).filter(
        DataFormatConfig.id == config_id
    ).first()
    
    if not config:
        return {
            "hasError": True,
            "result": None,
            "message": "配置不存在",
            "tag": None,
            "totalCount": 0
        }
    
    # 2. 获取关联的视图
    view = db.query(View).filter(View.id == config.view_id).first() if config.view_id else None
    
    # 3. 构建请求体示例
    body_example = {}
    if config.parameter_mappings:
        for param_name, mapping in config.parameter_mappings.items():
            if isinstance(mapping, dict):
                actual_name = mapping.get("param_name", param_name)
                body_example[actual_name] = ""
    
    # 4. 构建返回结果
    result = {
        "url": config.generated_api.get("endpoint", "") if config.generated_api else "",
        "sourceType": "AI_ASK",
        "sourceId": config.view_id,
        "categoryName": view.display_name or view.name if view else None,
        "categoryId": f"view_{view.id}" if view else None,
        "name": config.name,
        "method": "POST",
        "bodyType": "JSON",
        "header": {
            "Content-Type": "application/json"
        },
        "queryParams": {},
        "pathParams": {},
        "body": body_example,
        "parentId": f"view_{view.id}" if view else None,
        "timeout": 6000,
        "createTime": config.created_at.strftime("%Y-%m-%d %H:%M:%S") if config.created_at else None
    }
    
    return {
        "hasError": False,
        "result": result,
        "message": None,
        "tag": None,
        "totalCount": 1
    }


@router.post("/external/call/{config_id}")
async def call_external_api(
    config_id: str,
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    调用API接口（供外部系统对接）
    
    Args:
        config_id: 配置ID
        request: API参数
        
    Returns:
        转换后的数据结果（数组格式）
    """
    from app.services.mql_engine import mql_to_sql
    from app.services.query_executor import execute_query
    from app.services.sandbox_validator import SandboxValidator
    from app.models.view import View
    import json
    
    # 1. 获取配置
    config = db.query(DataFormatConfig).filter(
        DataFormatConfig.id == config_id
    ).first()
    
    if not config:
        return {
            "hasError": True,
            "result": None,
            "message": "配置不存在",
            "totalCount": 0
        }
    
    if config.status != "validated":
        return {
            "hasError": True,
            "result": None,
            "message": "配置未通过验证",
            "totalCount": 0
        }
    
    # 2. 获取MQL模板并构建MQL
    mql_template = config.mql_template or {}
    template_filters = mql_template.get("filters", []) or []
    
    # 规范化模板filters
    import re as _re
    
    def _has_field_ref(expr: str) -> bool:
        return bool(_re.findall(r"\[([^\]]+)\]", expr))
    
    def _has_structured_field_ref(condition) -> bool:
        if not isinstance(condition, dict):
            return False
        if "field" in condition:
            return True
        for sub in condition.get("conditions", []):
            if _has_structured_field_ref(sub):
                return True
        return False
    
    base_conditions = []
    if isinstance(template_filters, dict):
        base_conditions = list(template_filters.get("conditions", []))
    elif isinstance(template_filters, list):
        for f in template_filters:
            if isinstance(f, dict):
                if _has_structured_field_ref(f):
                    base_conditions.append(f)
            elif isinstance(f, str) and f.strip():
                if _has_field_ref(f):
                    base_conditions.append(f)
    
    mql = {
        "metrics": mql_template.get("metrics", []),
        "metricDefinitions": mql_template.get("metricDefinitions", {}),
        "dimensions": mql_template.get("dimensions", []),
        "filters": base_conditions,
        "timeConstraint": mql_template.get("timeConstraint", "true"),
        "limit": mql_template.get("limit", 1000),
        "queryResultType": mql_template.get("queryResultType", "DATA")
    }
    
    # 3. 使用parameter_mappings生成动态过滤条件
    parameter_mappings = config.parameter_mappings or {}
    
    if parameter_mappings and isinstance(parameter_mappings, dict):
        time_range_params = {}
        regular_params = []
        
        for field_name, param_info in parameter_mappings.items():
            param_name = param_info.get("param_name")
            is_time_range = param_info.get("is_time_range", False)
            
            if not is_time_range and param_name:
                time_range_pattern = r'^(.+?)[_]?(开始|结束|start|end|from|to)$'
                match = _re.match(time_range_pattern, param_name, _re.IGNORECASE)
                is_time_range = match is not None
            
            if is_time_range:
                base_field_name = param_info.get("base_field_name")
                range_type = param_info.get("range_type")
                
                if param_name and (not base_field_name or not range_type):
                    time_range_pattern = r'^(.+?)[_]?(开始|结束|start|end|from|to)$'
                    match = _re.match(time_range_pattern, param_name, _re.IGNORECASE)
                    if match:
                        base_field_name = base_field_name or match.group(1)
                        suffix = match.group(2).lower()
                        range_type = range_type or ('start' if suffix in ['开始', 'start', 'from'] else 'end')
                
                if base_field_name not in time_range_params:
                    time_range_params[base_field_name] = {
                        "start": None, 
                        "end": None, 
                        "source_field": param_info.get("source_field") or param_info.get("field_name", field_name)
                    }
                
                if param_name and param_name in request and request[param_name]:
                    time_range_params[base_field_name][range_type] = request[param_name]
                    source_field = param_info.get("source_field") or param_info.get("field_name", field_name)
                    time_range_params[base_field_name]["source_field"] = source_field
            else:
                regular_params.append((field_name, param_info))
        
        # 处理时间范围参数
        for base_field_name, time_range in time_range_params.items():
            source_field = time_range["source_field"] or base_field_name
            start_value = time_range["start"]
            end_value = time_range["end"]
            
            if start_value and end_value:
                mql["filters"].append({"field": source_field, "op": ">=", "value": start_value})
                mql["filters"].append({"field": source_field, "op": "<=", "value": end_value})
            elif start_value:
                mql["filters"].append({"field": source_field, "op": ">=", "value": start_value})
            elif end_value:
                mql["filters"].append({"field": source_field, "op": "<=", "value": end_value})
        
        # 处理普通参数
        for field_name, param_info in regular_params:
            param_name = param_info.get("param_name")
            if param_name and param_name in request:
                field_type = param_info.get("field_type", "string")
                param_value = request[param_name]
                
                if not param_value:
                    continue
                
                source_field = param_info.get("source_field") or param_info.get("field_name", field_name)
                
                if field_type in ["number", "int", "integer", "float"]:
                    try:
                        param_value = float(param_value)
                        if param_value == int(param_value):
                            param_value = int(param_value)
                    except (ValueError, TypeError):
                        pass
                
                mql["filters"].append({"field": source_field, "op": "=", "value": param_value})
    
    # 将filters统一为V2标准结构化格式
    all_filters = mql["filters"]
    if all_filters:
        if all(isinstance(f, dict) for f in all_filters):
            mql["filters"] = {"operator": "AND", "conditions": all_filters}
    else:
        mql["filters"] = []
    
    # 4. 执行MQL查询
    try:
        sql_result = await mql_to_sql(mql, db)
        sql = sql_result.get("sql", "")
        datasource_id = sql_result.get("datasources", [None])[0]
        
        if not datasource_id or not sql:
            return {
                "hasError": False,
                "result": [],
                "message": "无法获取数据源",
                "totalCount": 0
            }
        
        query_result = await execute_query(sql, datasource_id, limit=1000, db=db)
        
        # 5. 应用转换脚本
        source_data = {
            "columns": query_result.get("columns", []),
            "data": query_result.get("data", [])
        }
        
        validator = SandboxValidator(timeout=30)
        transform_result = validator._execute_mock(config.transform_script, source_data)
        
        if not transform_result["success"]:
            return {
                "hasError": True,
                "result": None,
                "message": f"转换脚本执行失败: {transform_result.get('error')}",
                "totalCount": 0
            }
        
        transformed_data = transform_result.get("result", [])
        
        return {
            "hasError": False,
            "result": transformed_data,
            "message": None,
            "totalCount": len(transformed_data)
        }
        
    except Exception as e:
        return {
            "hasError": True,
            "result": None,
            "message": f"执行查询失败: {str(e)}",
            "totalCount": 0
        }
