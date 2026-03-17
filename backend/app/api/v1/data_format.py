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

        # 构建包含完整field信息的parameterMappings（使用实际field名称作为key）
        full_parameter_mappings = {}
        param_info_map = {
            param["name"]: param
            for param in valid_params
        }
        for name, mapping in parameter_mappings.items():
            param_info = param_info_map.get(name, {})
            # 使用实际的field名称作为key
            field_name = param_info.get("field_name", name)
            full_parameter_mappings[field_name] = {
                "source_field": mapping.get("source_field"),
                "field_type": mapping.get("field_type"),
                "field_name": mapping.get("field_name"),
                "view_id": mapping.get("view_id"),
                # 添加完整的field信息
                "display_name": param_info.get("display_name", name),
                "dict_values": param_info.get("dict_values"),
                "view_name": param_info.get("view_name"),
                "required": param_info.get("required", True),
                # 保留原始参数名
                "param_name": name
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

        # 构建包含完整field信息的parameterMappings（使用实际field名称作为key）
        full_parameter_mappings = {}
        param_info_map = {
            param["name"]: param
            for param in valid_params
        }
        for name, mapping in parameter_mappings.items():
            param_info = param_info_map.get(name, {})
            # 使用实际的field名称作为key
            field_name = param_info.get("field_name", name)
            full_parameter_mappings[field_name] = {
                "source_field": mapping.get("source_field"),
                "field_type": mapping.get("field_type"),
                "field_name": mapping.get("field_name"),
                "view_id": mapping.get("view_id"),
                # 添加完整的field信息
                "display_name": param_info.get("display_name", name),
                "dict_values": param_info.get("dict_values"),
                "view_name": param_info.get("view_name"),
                "required": param_info.get("required", True),
                # 保留原始参数名
                "param_name": name
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

    # 2. 获取MQL模板并替换参数
    mql_template = config.mql_template or {}
    mql = {
        "metrics": mql_template.get("metrics", []),
        "metricDefinitions": mql_template.get("metricDefinitions", {}),
        "dimensions": mql_template.get("dimensions", []),
        # 保留MQL模板中已有的filters作为基础
        "filters": list(mql_template.get("filters", [])),
        "timeConstraint": mql_template.get("timeConstraint", "true"),
        "limit": mql_template.get("limit", 1000),
        "queryResultType": mql_template.get("queryResultType", "DATA")
    }

    # 使用parameter_mappings生成动态过滤条件
    parameter_mappings = config.parameter_mappings or {}
    if parameter_mappings and isinstance(parameter_mappings, dict):
        for field_name, param_info in parameter_mappings.items():
            # 获取原始参数名（用户输入的参数名）
            param_name = param_info.get("param_name")
            if param_name and param_name in request:
                if field_name:
                    # 根据field类型生成不同的过滤条件
                    field_type = param_info.get("field_type", "string")
                    param_value = request[param_name]

                    if field_type in ["number", "int", "integer", "float"]:
                        # 数字类型不加引号
                        filter_condition = f"[{field_name}] = {param_value}"
                    else:
                        # 字符类型加引号
                        filter_condition = f"[{field_name}] = '{param_value}'"
                    print(filter_condition)
                    mql["filters"].append(filter_condition)

    # 3. 执行MQL查询
    print(mql)
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
