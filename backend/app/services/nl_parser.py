import json
"""Natural Language Parser - Convert NL to MQL"""
from re import S
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.services.llm_client import call_llm
from app.models.metric import Metric
from app.models.dimension import Dimension


# Few-shot prompt template
NL_TO_MQL_PROMPT = """你是一个专业的数据分析师，负责将自然语言查询转换为MQL（Metric Query Language）JSON格式。

MQL JSON结构及字段规范：
{{
  "dimensions": ["维度逻辑名"], // 必须从下方的“可用维度”列表中选择“逻辑名”
  "metricDefinitions": {{
    "展示名": {{ // 用户友好的名称，可自由定义
      "refMetric": "指标逻辑名", // 必须从下方的“可用指标”列表中选择“逻辑名”
      "indirections": ["修饰词"] // 可选：sameperiod__yoy__growth (年同比), sameperiod__mom__growth (环比)
    }}
  }},
  "timeConstraint": "时间过滤SQL表达式", // 字段请用[维度逻辑名]或[指标逻辑名]包裹。仅允许使用：DateTrunc, AddMonths, CurrentDate, TODAY, LAST_N_DAYS, LAST_N_MONTHS
  "metrics": ["展示名"], // 必须对应 metricDefinitions 中的键
  "limit": 1000,
  "queryResultType": "DATA", // 取值范围：DATA, CHART
  "filters": ["其他过滤SQL表达式"] // 字段直接使用物理列名
}}

可用指标列表（展示名 | 逻辑名 | 物理列名）:
{metrics}

可用维度列表（展示名 | 逻辑名 | 物理列名）:
{dimensions}

时间函数规范（严格执行）：
1. 月度截断：DateTrunc([字段], 'MONTH') = 'YYYY-MM-01'
2. 年度截断：DateTrunc([字段], 'YEAR') = 'YYYY-01-01'
3. 月份加减：AddMonths([字段], -12) // 减 12 个月表示去年同期
4. 相对时间：[字段] >= TODAY(-7) 或 [字段] >= LAST_N_DAYS(30)
5. 范围查询：[字段] BETWEEN '2025-01-01' AND '2025-04-30'
禁止使用 DateAdd, INTERVAL 等非标准函数。

示例：
用户：2025年4月各渠道的销售额及年同比
MQL：
{{
  "dimensions": ["channel"],
  "metricDefinitions": {{
    "销售额": {{ "refMetric": "gmv" }},
    "销售额年同比": {{ "refMetric": "gmv", "indirections": ["sameperiod__yoy__growth"] }}
  }},
  "timeConstraint": "DateTrunc([date], 'MONTH') = '2025-04-01'",
  "metrics": ["销售额", "销售额年同比"],
  "limit": 1000,
  "queryResultType": "DATA",
  "filters": []
}}

请将以下自然语言转换为 MQL JSON。
注意：如果这是修复尝试，请参考下方的“错误信息”进行修正。
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
    
    if context and (context.get("suggested_metrics") or context.get("suggested_dimensions")):
        if context.get("suggested_metrics"):
            metrics_query = metrics_query.filter(Metric.name.in_(context["suggested_metrics"]))
        if context.get("suggested_dimensions"):
            dimensions_query = dimensions_query.filter(Dimension.name.in_(context["suggested_dimensions"]))
        
        metrics = metrics_query.all()
        dimensions = dimensions_query.all()
    else:
        metrics = metrics_query.limit(30).all()
        dimensions = dimensions_query.limit(30).all()
    
    metrics_list = [f"- {m.display_name or m.name} | {m.name} | {m.measure_column}" for m in metrics]
    metrics_str = "\n".join(metrics_list) or "- 销售额 | gmv | retail_amt"
    
    dims_list = [f"- {d.display_name or d.name} | {d.name} | {d.physical_column}" for d in dimensions]
    dimensions_str = "\n".join(dims_list) or "- 日期 | date | create_time"

    # 2. Multi-turn correction loop
    max_retries = 3
    current_attempt = 0
    error_info = ""
    last_mql = None

    while current_attempt < max_retries:
        prompt = NL_TO_MQL_PROMPT.format(
            metrics=metrics_str,
            dimensions=dimensions_str,
            query=natural_language,
            error_info=f"\n上次生成的错误信息：\n{error_info}\n请根据错误信息修复后再输出全量 JSON。\n" if error_info else ""
        )

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
                metrics_list_str = ", ".join([f"{m.name} ({m.measure_column})" for m in metrics[:5]])
                dims_list_str = ", ".join([f"{d.name} ({d.physical_column})" for d in dimensions[:5]])
                
                used_metrics = ", ".join(mql.get("metrics", []))
                used_dims = ", ".join(mql.get("dimensions", []))
                
                steps = [
                    {
                        "title": "意图识别",
                        "content": "识别到用户意图为：具体指标和维度的精准查询，数据解读或归因。",
                        "status": "success"
                    },
                    {
                        "title": "指标检索",
                        "content": f"• 查询相关指标：{metrics_list_str}等\n• 查询相关维度：{dims_list_str}等",
                        "status": "success"
                    },
                    {
                        "title": "指标查询",
                        "content": f"• 查询使用指标：{used_metrics}\n• 查询使用维度：{used_dims}\n• MQL 已通过元数据校验并生成。",
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
        "dimensions": [], "metricDefinitions": {}, "metrics": [], 
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
