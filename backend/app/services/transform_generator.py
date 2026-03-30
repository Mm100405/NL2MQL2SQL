"""
数据格式转换服务 - 大模型生成转换脚本
"""
import json
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """处理Decimal类型的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# 大模型生成转换脚本的Prompt模板
GENERATE_TRANSFORM_PROMPT = """你是一个数据转换专家。请根据以下信息生成数据转换脚本和API配置。

## 用户查询
{natural_language}

## 目标数据格式
```json
{target_format_example}
```

## API所需参数
{api_parameters}

## 原始数据示例
```json
{source_data_sample}
```

## 任务要求

### 1. 生成转换脚本
编写一个JavaScript转换函数，将原始数据转换为目标格式。

要求:
- 函数名为: `transformData`
- **输入参数名必须严格为 `sourceData` (注意大小写，不是 sourceDdata 或 sourcedata)**
- `sourceData` 结构: {{ columns: string[], data: any[][] }}
- 返回值: 转换后的目标格式数组 (必须是对象数组)
- 必须处理数据可能为空的情况
- 必须进行类型转换（如数字转字符串、字符串转数字）
- 字段映射要准确
- 使用 `sourceData.columns` 获取列名数组
- 使用 `sourceData.data` 获取二维数据数组
- 示例:
  ```javascript
  function transformData(sourceData) {{
    const columns = sourceData.columns || [];
    const data = sourceData.data || [];
    // ... 转换逻辑
    return result;
  }}
  ```

**重要**: 变量名 `sourceData` 不能有任何拼写错误！

### 2. 生成参数映射
分析API所需参数，从源数据中找到对应字段:
- 参数名
- 源字段名（如果映射）
- 参数类型
- 是否必填

### 3. 生成MQL模板
根据自然语言查询和API参数，生成MQL模板:
- 包含必要的维度和指标
- 设置API参数为可变参数（使用占位符格式: {{{{参数名}}}}）
- 设置合理的默认筛选条件

## 输出格式

请以JSON格式返回:

```json
{{
  "apiName": "中文接口名称（5-15字，概括性描述，如：街道问题统计查询、销售数据分析等）",
  "transformScript": "转换脚本内容",
  "parameterMappings": [
    {{
      "name": "参数名",
      "sourceField": "源字段名",
      "type": "string|number|date|enum",
      "required": true
    }}
  ],
  "mqlTemplate": {{
    "metrics": ["指标名"],
    "dimensions": ["维度名"],
    "filters": [
      "[字段名] = '{{{{参数名}}}}'"
    ],
    "timeConstraint": "时间约束或true"
  }}
}}
```

## 注意事项
1. 转换脚本必须严格符合JavaScript语法
2. **变量名 `sourceData` 必须完全一致，不能有任何拼写或大小写错误**
3. 参数映射必须与API所需参数对应
4. MQL模板要能正确执行查询
5. 考虑数据类型转换和边界情况
6. 如果某个参数在原数据中没有对应字段，需要在parameterMappings中使用sourceField为null，并在mqlTemplate中使用静态值或排除该过滤条件
7. 在生成代码后，请再次检查变量名是否正确拼写

## 正确的代码示例
```javascript
function transformData(sourceData) {{
  // 提取列名和数据
  const columns = sourceData.columns || [];
  const data = sourceData.data || [];

  // 处理空数据
  if (!data || data.length === 0) {{
    return [];
  }}

  // 转换数据
  return data.map(row => {{
    const obj = {{}};
    columns.forEach((col, index) => {{
      obj[col] = row[index];
    }});
    return obj;
  }});
}}
```
"""


async def generate_transform_config(
    natural_language: str,
    target_format_example: Dict[str, Any],
    api_parameters: str,  # 用"、"分隔的字符串
    db: Session,
    existing_mql: Optional[Dict[str, Any]] = None,  # 前面 generate-mql 的返回
    existing_sql: Optional[str] = None,  # 前面 mql2sql 的返回
    existing_query_result: Optional[Dict[str, Any]] = None  # 前面 execute 的返回结果（字典格式）
) -> Dict[str, Any]:
    """
    调用大模型生成转换脚本和配置

    Args:
        natural_language: 自然语言查询
        target_format_example: 目标格式JSON示例
        api_parameters: API所需参数列表（用"、"分隔的字符串）
        db: 数据库会话
        existing_mql: 可选，前面 generate-mql 的返回 mql，如果提供则不重新生成
        existing_sql: 可选，前面 mql2sql 的返回 sql，如果提供则不重新转换
        existing_query_result: 可选，前面 execute 的返回结果，如果提供则不重新查询

    Returns:
        生成结果字典
    """
    from app.services.llm_client import call_llm
    from app.models.model_config import ModelConfig
    from app.utils.encryption import decrypt_api_key

    # 1. 获取模型配置
    model_config = db.query(ModelConfig).filter(
        ModelConfig.is_default == True,
        ModelConfig.is_active == True
    ).first()

    if not model_config:
        return {
            "success": False,
            "error": "未配置AI模型"
        }

    api_key = decrypt_api_key(model_config.api_key) if model_config.api_key else None

    # 2. 获取基础MQL（优先使用传入的，否则重新生成）
    from app.services.nl_parser import parse_natural_language

    if existing_mql:
        # 使用传入的MQL
        base_mql = existing_mql
    else:
        # 解析自然语言获取基础MQL
        try:
            nl_result = await parse_natural_language(
                natural_language=natural_language,
                provider=model_config.provider,
                model_name=model_config.model_name,
                api_key=api_key,
                api_base=model_config.api_base,
                config_params=model_config.config_params,
                db=db
            )
            base_mql = nl_result.get("mql", {})
        except Exception as e:
            # 如果解析失败，使用空MQL
            base_mql = {
                "metrics": [],
                "dimensions": [],
                "filters": [],
                "timeConstraint": "true"
            }

    # 3. 获取样本数据（优先使用传入的，否则重新查询）
    from app.services.mql_engine import mql_to_sql
    from app.services.query_executor import execute_query

    logger.info(f"[TransformGenerator] 开始获取样本数据，existing_query_result: {existing_query_result is not None}")

    if existing_query_result:
        # 使用传入的查询结果作为样本数据（字典格式）
        logger.info(f"[TransformGenerator] 使用传入的查询结果")
        try:
            source_data_sample = {
                "columns": existing_query_result.get("columns", []),
                "data": existing_query_result.get("data", [])
            }
            logger.info(f"[TransformGenerator] 样本数据构建成功，columns: {len(source_data_sample['columns'])}, data: {len(source_data_sample['data'])}")
        except Exception as e:
            logger.error(f"[TransformGenerator] 构建样本数据失败: {e}", exc_info=True)
            raise
    else:
        # 需要重新查询获取样本数据
        try:
            if existing_sql:
                # 使用传入的SQL
                sql = existing_sql
                # 需要从 MQL 中获取数据源ID
                sql_result = {"sql": sql}
                datasource_id = None
            else:
                # 重新转换MQL为SQL
                sql_result = await mql_to_sql(base_mql, db)
                sql = sql_result.get("sql", "")
                datasource_id = sql_result.get("datasources", [None])[0]

            if datasource_id and sql:
                sample_result = await execute_query(sql, datasource_id, limit=5, db=db)
                source_data_sample = {
                    "columns": sample_result.get("columns", []),
                    "data": sample_result.get("data", [])
                }
            else:
                source_data_sample = {
                    "columns": [],
                    "data": []
                }
        except Exception as e:
            source_data_sample = {
                "columns": [],
                "data": [],
                "error": str(e)
            }

    # 4. 构建Prompt
    logger.info(f"[TransformGenerator] 开始构建Prompt，target_format_example type: {type(target_format_example)}")
    logger.info(f"[TransformGenerator] source_data_sample keys: {list(source_data_sample.keys())}")
    logger.info(f"[TransformGenerator] source_data_sample columns: {source_data_sample.get('columns', [])}")

    try:
        prompt = GENERATE_TRANSFORM_PROMPT.format(
            natural_language=natural_language,
            target_format_example=json.dumps(target_format_example, indent=2, ensure_ascii=False, cls=DecimalEncoder),
            api_parameters=api_parameters.replace("、", ", "),
            source_data_sample=json.dumps(source_data_sample, indent=2, ensure_ascii=False, cls=DecimalEncoder)
        )
        logger.info("[TransformGenerator] Prompt 构建成功")
    except Exception as e:
        logger.error(f"[TransformGenerator] Prompt 构建失败: {e}", exc_info=True)
        raise

    # 5. 调用大模型
    try:
        llm_response = await call_llm(
            prompt=prompt,
            provider=model_config.provider,
            model_name=model_config.model_name,
            api_key=api_key,
            api_base=model_config.api_base,
            config_params=model_config.config_params
        )

        # 6. 解析响应
        generation = _parse_llm_response(llm_response)

        if not generation:
            return {
                "success": False,
                "error": "大模型返回的不是有效JSON格式",
                "llm_output": llm_response
            }

        # 7. 验证生成结果
        validation_result = _validate_generation(generation, target_format_example, source_data_sample)

        if not validation_result["valid"]:
            return {
                "success": False,
                "error": "生成结果验证失败",
                "details": validation_result["errors"],
                "llm_output": generation
            }

        return {
            "success": True,
            "apiName": generation.get("apiName", f"数据接口_{natural_language[:10]}"),
            "transformScript": generation.get("transformScript", ""),
            "parameterMappings": generation.get("parameterMappings", []),
            "mqlTemplate": generation.get("mqlTemplate", {}),
            "baseMql": base_mql,
            "sourceDataSample": source_data_sample
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"[TransformGenerator] 生成失败: {e}\n{error_detail}")
        return {
            "success": False,
            "error": f"生成失败: {str(e)}",
            "detail": error_detail
        }


def _parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
    """
    解析大模型返回的JSON响应
    """
    import re

    if not response:
        return None

    # 尝试直接解析
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # 尝试提取JSON块
    json_pattern = r'```json\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, response)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试找到第一个 { 到最后一个 } 之间的内容
    start = response.find('{')
    end = response.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(response[start:end+1])
        except json.JSONDecodeError:
            pass

    return None


def _validate_generation(
    generation: Dict[str, Any],
    target_format: Dict[str, Any],
    source_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    验证生成结果的正确性
    """
    errors = []

    # 验证转换脚本
    if not generation.get("transformScript"):
        errors.append("缺少转换脚本")
    else:
        script = generation["transformScript"]
        # 检查基本的JavaScript语法
        if "function" not in script and "=>" not in script:
            errors.append("转换脚本必须是函数")
        if "transformData" not in script and "function" in script:
            errors.append("转换脚本必须包含 transformData 函数")

    # 验证参数映射
    if not generation.get("parameterMappings"):
        errors.append("缺少参数映射")

    # 验证MQL模板
    mql_template = generation.get("mqlTemplate", {})
    if not mql_template:
        errors.append("缺少MQL模板")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
