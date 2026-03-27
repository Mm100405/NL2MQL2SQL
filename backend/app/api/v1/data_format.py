"""
数据格式配置API接口
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
import logging

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
    existing_query_result: Optional[ExistingQueryResult] = None
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
            existing_query_result=request.existing_query_result
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
                "mqlTemplate": result["dynamicMql"]
            },
            used_view_id=filter_result.get("used_view_id"),
            db=db
        )

        return {
            "success": True,
            "configId": config.id,
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

        old_config.transform_script = result["transformScript"]
        old_config.parameter_mappings = full_parameter_mappings
        old_config.mql_template = result["dynamicMql"]

        # 重新生成API信息
        api_info = generate_api_info(
            config_id=config_id,
            name=old_config.name,
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
