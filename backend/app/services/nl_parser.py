import json
"""Natural Language Parser - Convert NL to MQL"""
from re import S
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.services.llm_client import call_llm
from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.settings import SystemSetting


# Few-shot prompt template
NL_TO_MQL_PROMPT = """你是一个专业的数据分析师，负责将自然语言查询转换为MQL（Metric Query Language）JSON格式。

MQL JSON结构及字段规范：
{{
  "dimensions": ["维度逻辑名"], // 必须从下方的"可用维度"列表中选择"逻辑名"。
  "metricDefinitions": {{
    "展示名": {{ // 必须从下方的"可用指标"列表中选择"展示名"
      "refMetric": "指标逻辑名", // 必须从下方的"可用指标"列表中选择"逻辑名"
      "indirections": ["修饰词"] // 可选：sameperiod__yoy__growth (年同比), sameperiod__mom__growth (环比)
    }}
  }},
  "timeConstraint": "时间过滤表达式", // ⚠️ 仅用于时间/日期相关的过滤
  "metrics": ["展示名"], // 必须从下方的"可用指标"列表中选择"展示名"
  "filters": [  // ⚠️ 所有非时间维度的过滤条件放这里
    "[字段展示名] = '值'",
    "[字段展示名] IN ('值1', '值2')",
    "[数值字段] > 100"
  ],
  "limit": 1000,
  "queryResultType": "DATA"
}}

⚠️ 关键规则：

1. **timeConstraint vs filters 区分**：
   - `timeConstraint`：仅用于时间/日期相关的过滤（如"2025年4月"、"最近7天"、"本月"）
   - `filters`：用于所有非时间维度的过滤（如"线上渠道"、"已完成订单"、"金额大于1000"）

2. **filters 语法规范**：
   - 字段名必须用中括号包裹：`[字段展示名]` 或 `[字段逻辑名]`
   - 字符串值必须用单引号：`'值'`
   - 支持的操作符：`=`、`!=`、`>`、`<`、`>=`、`<=`、`IN`、`NOT IN`、`LIKE`
   - 多个条件用数组表示，会自动用 AND 连接

3. **字段值选择**：
   - 必须从下方「可过滤字段」列表中选择字段
   - 值必须从字段的可选值中选择（如果提供了可选值列表）

重要说明：
1. **增量修改逻辑**：如果下方提供了"引用上下文 (Quoted MQL)"，你的任务是基于该上下文进行**增量修改**。
   - 保持原有的指标、维度和筛选，除非用户明确要求删除或替换。
   - 如果用户提出补充要求（如"再看下地区维度"），应将新维度合并到原有 dimensions 列表中。
   - 如果用户提出冲突要求（如"把月份改为4月"），应替换原 MQL 中的对应部分。
2. **元数据映射**：必须严格遵守下方提供的元数据映射列表。
3. **时间粒度选择**：对于涉及趋势查询（按月、按年等），必须直接从维度列表中选择对应的逻辑名（如 `日期__按月`）。

可用指标列表（展示名 | 逻辑名 | 物理列名）:
{metrics}

可用维度列表（展示名 | 逻辑名 | 物理列名）:
{dimensions}

可过滤字段列表（展示名 | 逻辑名 | 类型 | 物理说明 | 自定义说明 | 可选值）:
{filterable_fields}

时间函数规范（严格执行）：
1. 月度截断：DateTrunc([字段], 'MONTH') = 'YYYY-MM-01'
2. 年度截断：DateTrunc([字段], 'YEAR') = 'YYYY-01-01'
3. 月份加减：AddMonths([字段], -12) // 减 12 个月表示去年同期
4. 相对时间：[字段] >= TODAY(-7) 或 [字段] >= LAST_N_DAYS(30)
5. 范围查询：[字段] BETWEEN '2025-01-01' AND '2025-04-30'

重要禁令：
- 禁止将函数名放在中括号内，例如 [TODAY](-7) 是错误的，应为 TODAY(-7)。
- 禁止使用 DateAdd, INTERVAL, NOW() 等非白名单函数。
- 中括号 [] 在 timeConstraint 中只能用于包裹元数据列表中的"展示名"。

示例1：
用户："线上渠道2025年4月的销售额"
MQL：
{{
  "dimensions": [],
  "metricDefinitions": {{ "销售额": {{ "refMetric": "gmv" }} }},
  "timeConstraint": "DateTrunc([日期], 'MONTH') = '2025-04-01'",
  "metrics": ["销售额"],
  "filters": ["[渠道] = '线上'"],
  "limit": 1000,
  "queryResultType": "DATA"
}}

示例2：
用户："已完成订单中金额大于1000的订单数"
MQL：
{{
  "dimensions": [],
  "metricDefinitions": {{ "订单数": {{ "refMetric": "order_count" }} }},
  "timeConstraint": "true",
  "metrics": ["订单数"],
  "filters": ["[订单状态] = '完成'", "[订单金额] > 1000"],
  "limit": 1000,
  "queryResultType": "DATA"
}}

示例3：
用户："2025年4月各渠道的销售额及年同比"
MQL：
{{
  "dimensions": ["channel"],
  "metricDefinitions": {{
    "销售额": {{ "refMetric": "gmv" }},
    "销售额年同比": {{ "refMetric": "gmv", "indirections": ["sameperiod__yoy__growth"] }}
  }},
  "timeConstraint": "DateTrunc([日期], 'MONTH') = '2025-04-01'",
  "metrics": ["销售额", "销售额年同比"],
  "filters": [],
  "limit": 1000,
  "queryResultType": "DATA"
}}

请将以下自然语言转换为 MQL JSON。
注意：如果这是修复尝试，请参考下方的"错误信息"进行修正。
{error_info}
用户：{query}
MQL："""


async def parse_natural_language(
    natural_language: str,
    provider: str,
    model_name: str,
    api_key: Optional[str],
    api_base: Optional[str],
    config_params: Optional[dict],
    db: Session,
    context: Optional[dict] = None
) -> dict:
    """Parse natural language query to MQL with multi-turn correction"""
    from app.utils.mql_validator import MQLValidator
    validator = MQLValidator(db)
    
    # 1. Get available metadata
    metrics_query = db.query(Metric)
    dimensions_query = db.query(Dimension)
    
    # 获取全局时间格式配置
    time_formats = [
        {"name": "YYYY-MM-DD", "label": "按日", "suffix": "day", "is_default": True},
        {"name": "YYYY-MM", "label": "按月", "suffix": "month", "is_default": False},
        {"name": "YYYY", "label": "按年", "suffix": "year", "is_default": False},
        {"name": "YYYY-WW", "label": "按周", "suffix": "week", "is_default": False}
    ]
    try:
        time_formats_setting = db.query(SystemSetting).filter(SystemSetting.key == "time_formats").first()
        if time_formats_setting:
            val = time_formats_setting.value
            if isinstance(val, str):
                try:
                    time_formats = json.loads(val)
                except:
                    pass
            elif isinstance(val, list):
                time_formats = val
    except Exception as e:
        print(f"Error fetching time_formats from DB: {e}")
    
    if context and (context.get("suggested_metrics") or context.get("suggested_dimensions")):
        from sqlalchemy import or_
        if context.get("suggested_metrics"):
            metrics_query = metrics_query.filter(or_(
                Metric.name.in_(context["suggested_metrics"]),
                Metric.display_name.in_(context["suggested_metrics"])
            ))
        if context.get("suggested_dimensions"):
            dimensions_query = dimensions_query.filter(or_(
                Dimension.name.in_(context["suggested_dimensions"]),
                Dimension.display_name.in_(context["suggested_dimensions"])
            ))
        
        metrics = metrics_query.all()
        dimensions = dimensions_query.all()
    else:
        metrics = metrics_query.all() # 去掉 limit，确保获取全量元数据
        dimensions = dimensions_query.all()
    
    metrics_list = [f"- {m.display_name or m.name} | {m.name} | {m.measure_column}" for m in metrics]
    metrics_str = "\n".join(metrics_list) or "- 销售额 | gmv | retail_amt"
    
    dims_list = []
    for d in dimensions:
        # 规范化维度类型检查
        d_type = str(d.dimension_type).lower() if d.dimension_type else "normal"
        if hasattr(d.dimension_type, 'value'):
            d_type = d.dimension_type.value
            
        d_data_type = str(d.data_type).lower() if d.data_type else ""
        
        # 判断是否为时间维度：维度类型为 time OR 物理数据类型为 date/datetime
        is_time_dim = (d_type == "time") or (d_data_type in ["date", "datetime", "timestamp"])
        
        if not is_time_dim:
            dim_info = f"- {d.display_name or d.name} | {d.name} | {d.physical_column}"
            dims_list.append(dim_info)
            continue
            
        # 2. 处理时间维度：衍生出多个虚拟维度并替换原始维度
        format_options = []
        raw_config = d.format_config
        if raw_config:
            if isinstance(raw_config, str):
                try:
                    raw_config = json.loads(raw_config)
                except:
                    raw_config = {}
            if isinstance(raw_config, dict):
                format_options = raw_config.get("options", [])
        
        # 如果维度配置中没有指定 options，默认提供全局支持的所有格式
        if not format_options:
            format_options = [f["name"] for f in time_formats]
        
        added_any = False
        # 遍历系统配置的所有格式
        for fmt_cfg in time_formats:
            # 如果维度支持该格式，则添加衍生维度
            if fmt_cfg.get("name") in format_options:
                suffix = fmt_cfg.get("suffix")
                label = fmt_cfg.get("label")
                # 逻辑名：展示名__标签 (例如: 创建时间__按月)
                virtual_name = f"{d.display_name or d.name}__{label}"
                virtual_display = f"{d.display_name or d.name}({label})"
                dims_list.append(f"- {virtual_display} | {virtual_name} | {d.physical_column} | 类型: 时间虚拟维度")
                added_any = True
        
        # 兜底逻辑
        if not added_any:
            dim_info = f"- {d.display_name or d.name} | {d.name} | {d.physical_column} | 类型: 时间"
            dims_list.append(dim_info)
    
    dimensions_str = "\n".join(dims_list) or "- 日期 | date | create_time"

    # 3. 构建可过滤字段列表
    filterable_fields_list = []
    from app.models.view import View
    from app.models.field_dict import FieldDictionary
    
    # 从视图中获取可过滤字段
    views = db.query(View).all()
    for view in views:
        columns = view.columns or []
        for col in columns:
            # 检查字段是否可过滤
            if col.get("filterable", True):
                display_name = col.get("display_name") or col.get("name")
                field_name = col.get("name")
                field_type = col.get("type", "")
                
                # 获取物理说明和自定义说明
                source_comment = col.get("source_comment", "")
                description = col.get("description", "")
                
                # 获取可选值
                optional_values = ""
                value_config = col.get("value_config", {})
                if value_config:
                    config_type = value_config.get("type")
                    if config_type == "enum":
                        enum_vals = value_config.get("enum_values", [])
                        optional_values = f" | 可选值: {', '.join(enum_vals)}" if enum_vals else ""
                    elif config_type == "dict":
                        dict_id = value_config.get("dict_id")
                        if dict_id:
                            dict_obj = db.query(FieldDictionary).filter(FieldDictionary.id == dict_id).first()
                            if dict_obj and dict_obj.mappings:
                                labels = [m.get("label", m.get("value")) for m in dict_obj.mappings]
                                optional_values = f" | 可选值: {', '.join(labels)}"
                
                filterable_fields_list.append(f"- {display_name} | {field_name} | {field_type} | {source_comment} | {description} | {optional_values}")
    
    filterable_fields_str = "\n".join(filterable_fields_list) or "- 渠道 | channel | VARCHAR | 流量渠道 | 主要推广渠道 | 可选值: 直搜, 搜索引擎, 外部链接"

    # 2. Multi-turn correction loop
    max_retries = 3
    current_attempt = 0
    error_info = ""
    last_mql = None
    
    # 引用上下文处理
    quoted_mql_str = ""
    if context and context.get("quoted_mql"):
        quoted_mql_str = f"\n引用上下文 (Quoted MQL):\n{json.dumps(context['quoted_mql'], ensure_ascii=False, indent=2)}\n请基于该上下文进行修改或进一步分析。\n"

    while current_attempt < max_retries:
        prompt = NL_TO_MQL_PROMPT.format(
            metrics=metrics_str,
            dimensions=dimensions_str,
            filterable_fields=filterable_fields_str,
            query=natural_language,
            error_info=(f"\n上次生成的错误信息：\n{error_info}\n请根据错误信息修复后再输出全量 JSON。\n" if error_info else "") + quoted_mql_str
        )
        print(prompt)
        try:
            response = await call_llm(
                prompt=prompt,
                provider=provider,
                model_name=model_name,
                api_key=api_key,
                api_base=api_base,
                config_params=config_params
            )
            
            # Extract and parse JSON
            mql_str = response.strip()
            if "```json" in mql_str:
                mql_str = mql_str.split("```json")[1].split("```")[0].strip()
            elif "```" in mql_str:
                mql_str = mql_str.split("```")[1].split("```")[0].strip()
            
            mql = json.loads(mql_str)
            
            last_mql = mql
            
            # 3. Strong Validation Integration
            is_valid, msg = validator.validate_mql(mql)
            if is_valid:
                # Success! Generate steps for UI
                used_metrics = mql.get("metrics", [])
                used_dims = mql.get("dimensions", [])
                time_range_raw = mql.get("timeConstraint", "不限")
                
                # 增强时间范围展示
                time_range_display = time_range_raw
                if time_range_display == "true" or not time_range_display:
                    time_range_display = "全部时间"
                
                # 处理维度展示名 (解析衍生维度)
                formatted_dims = []
                for d in used_dims:
                    if "__" in d:
                        parts = d.split("__", 1)
                        formatted_dims.append(f"{parts[0]}({parts[1]})")
                    else:
                        formatted_dims.append(d)
                
                metrics_list_str = "\n".join([f"• {m}" for m in used_metrics])
                dims_list_str = "\n".join([f"• {d}" for d in formatted_dims])
                
                steps = [
                    {
                        "title": "意图识别",
                        "content": f"识别到查询需求：\n\n**指标**：\n{metrics_list_str or '无'}\n\n**维度**：\n{dims_list_str or '无'}\n\n**时间范围**：\n{time_range_display}",
                        "status": "success"
                    },
                    {
                        "title": "指标检索",
                        "content": f"已匹配数据集元数据：\n• 指标：{', '.join(used_metrics)}\n• 维度：{', '.join(used_dims)}",
                        "status": "success"
                    },
                    {
                        "title": "指标查询",
                        "content": f"MQL 生成成功。已根据问数配置应用时间粒度解析：\n\n**解析后的时间维度**：{', '.join([d for d in used_dims if '__' in d]) or '无'}",
                        "status": "success"
                    }
                ]
                
                return {
                    "mql": mql,
                    "steps": steps,
                    "confidence": 0.85,
                    "interpretation": f"查询：{natural_language}"
                }
            else:
                # Validation failed, prepare for next turn
                error_info = msg
                current_attempt += 1
                print(f"MQL Validation failed (Attempt {current_attempt}): {msg}")
                
        except Exception as e:
            error_info = f"JSON 解析或系统错误: {str(e)}"
            current_attempt += 1
            print(f"MQL Parsing error (Attempt {current_attempt}): {str(e)}")

    # 4. Final fallback or error return
    final_mql = last_mql or {
        "dimensions": [], "dimensionConfigs": {}, "metricDefinitions": {}, "metrics": [], 
        "timeConstraint": "1=1", "limit": 1000, "queryResultType": "DATA", "filters": []
    }
    
    return {
        "mql": final_mql,
        "steps": [
            {"title": "意图识别", "content": "识别过程已完成。", "status": "success"},
            {"title": "指标检索", "content": "已检索到候选指标，但生成过程中存在匹配风险。", "status": "warning"},
            {"title": "指标查询", "content": f"MQL 生成失败或校验未通过：{error_info}", "status": "error"}
        ],
        "confidence": 0.5,
        "interpretation": f"查询：{natural_language} (修正失败: {error_info})"
    }
