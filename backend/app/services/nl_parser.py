"""Natural Language Parser - Convert NL to MQL"""
from typing import Optional
from sqlalchemy.orm import Session

from app.services.llm_client import call_llm
from app.models.metric import Metric
from app.models.dimension import Dimension


# Few-shot prompt template
NL_TO_MQL_PROMPT = """你是一个专业的数据分析师，负责将自然语言查询转换为MQL（Metric Query Language）查询。

MQL语法说明：
- SELECT: 指定要查询的指标和维度，如 SELECT SUM(销售额), 日期
- WHERE: 过滤条件，支持 =, !=, >, <, >=, <=, IN, BETWEEN, LIKE
- GROUP BY: 分组维度
- ORDER BY: 排序，ASC升序，DESC降序
- LIMIT: 限制返回行数

时间函数：
- TODAY(): 今天
- TODAY(-N): N天前
- LAST_N_DAYS(N): 过去N天
- LAST_N_MONTHS(N): 过去N个月
- THIS_WEEK(): 本周
- THIS_MONTH(): 本月
- THIS_YEAR(): 本年

可用的指标：
{metrics}

可用的维度：
{dimensions}

示例：
用户：最近7天每天的销售额
MQL：SELECT SUM(销售额) AS 总销售额, 日期 WHERE 日期 >= LAST_N_DAYS(7) GROUP BY 日期 ORDER BY 日期 ASC

用户：北京地区销售额前10的产品
MQL：SELECT 产品名称, SUM(销售额) AS 总销售额 WHERE 地区 = '北京' GROUP BY 产品名称 ORDER BY 总销售额 DESC LIMIT 10

用户：本月各渠道的订单数和客单价
MQL：SELECT 渠道, COUNT(订单ID) AS 订单数, SUM(销售额) / COUNT(订单ID) AS 客单价 WHERE 日期 >= THIS_MONTH() GROUP BY 渠道

现在，请将以下自然语言转换为MQL：
用户：{query}
MQL："""


async def parse_natural_language(
    natural_language: str,
    provider: str,
    model_name: str,
    api_key: Optional[str],
    api_base: Optional[str],
    config_params: Optional[dict],
    db: Session
) -> dict:
    """Parse natural language query to MQL"""
    
    # Get available metrics and dimensions
    metrics = db.query(Metric).all()
    dimensions = db.query(Dimension).all()
    
    metrics_str = "\n".join([f"- {m.name}: {m.description or m.display_name or ''}" for m in metrics]) or "- 销售额\n- 订单数\n- 客单价"
    dimensions_str = "\n".join([f"- {d.name}: {d.description or d.display_name or ''}" for d in dimensions]) or "- 日期\n- 地区\n- 产品类别\n- 渠道"
    
    # Build prompt
    prompt = NL_TO_MQL_PROMPT.format(
        metrics=metrics_str,
        dimensions=dimensions_str,
        query=natural_language
    )
    
    # Call LLM
    try:
        mql = await call_llm(
            prompt=prompt,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            config_params=config_params
        )
        
        # Clean up response
        mql = mql.strip()
        if mql.startswith("MQL：") or mql.startswith("MQL:"):
            mql = mql[4:].strip()
        
        return {
            "mql": mql,
            "confidence": 0.85,
            "interpretation": f"查询：{natural_language}"
        }
    except Exception as e:
        # Fallback to demo MQL if LLM fails
        return {
            "mql": f"SELECT SUM(销售额) AS 总销售额, 日期 WHERE 日期 >= LAST_N_DAYS(7) GROUP BY 日期 ORDER BY 日期 ASC",
            "confidence": 0.5,
            "interpretation": f"[Demo] {natural_language} (LLM Error: {str(e)})"
        }
