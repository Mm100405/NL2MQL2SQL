import json
"""
Natural Language Parser - Convert NL to MQL V2

MQL V2 完整字段（10个）：
1. metrics: 指标别名列表
2. metricDefinitions: 指标定义
3. dimensions: 维度列表
4. filters: WHERE 过滤（聚合前）- 维度/时间过滤
5. having: HAVING 过滤（聚合后）- 指标过滤
6. orderBy: 排序
7. distinct: 去重
8. limit: 结果限制
9. windowFunctions: 窗口函数
10. union: UNION 查询
11. cte: CTE 公共表表达式
"""
from re import S
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.services.llm_client import call_llm
from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.settings import SystemSetting


# Few-shot prompt template
NL_TO_MQL_PROMPT = """你是一个专业的数据分析师，负责将自然语言查询转换为MQL（Metric Query Language）V2 JSON格式。

你应该在简单判断后就给出答案，快速精准给出MQL。

MQL V2 JSON结构及字段规范：
{{
  "metrics": ["指标逻辑名"],         // 必须从下方"可用指标"的 [name:xxx] 中选择逻辑名
  "metricDefinitions": {{           // 指标定义映射（当使用衍生指标时才需要）
    "指标逻辑名": {{
      "refMetric": "基础指标逻辑名", // 必须从下方"可用指标"的 [name:xxx] 中选择逻辑名
      "aggregation": "SUM|COUNT|AVG|MAX|MIN|COUNT_DISTINCT",  // 聚合类型，默认 SUM
      "indirections": ["修饰词"]     // 可选：sameperiod__yoy__growth (年同比), sameperiod__mom__growth (环比)
    }}
  }},
  "dimensions": ["维度逻辑名"],      // 必须从下方"可用维度"的 [name:xxx] 中选择逻辑名
  "filters": {{                      // ⚠️ 聚合前过滤 - 维度/时间过滤放这里
    "operator": "AND",              // 顶层逻辑运算符：AND 或 OR（可选，默认 AND）
    "conditions": [                 // 条件列表
      {{"field": "字段逻辑名", "op": "=", "value": "值"}},
      {{"field": "字段逻辑名", "op": "IN", "value": ["值1", "值2"]}}
    ]
  }},
  "having": [                        // ⚠️ 聚合后过滤 - 指标过滤必须放这里！
    "[指标逻辑名] > 100",
    "[指标逻辑名] >= 1000"
  ],
  "orderBy": [                       // 可选：排序
    {{"field": "字段逻辑名或指标逻辑名", "direction": "ASC|DESC"}}
  ],
  "distinct": false,                 // 可选：去重，默认 false
  "limit": 1000,                     // 可选：结果限制，默认 1000
  "windowFunctions": [               // 可选：窗口函数
    {{
      "alias": "窗口别名",
      "func": "SUM|AVG|COUNT|MAX|MIN|ROW_NUMBER|RANK",
      "field": "字段名",
      "partition": ["分区字段"],     // 可选：PARTITION BY，数组格式
      "orderBy": [                  // 可选：ORDER BY，数组格式（与主查询 orderBy 一致）
        {{"field": "排序字段", "direction": "ASC|DESC"}}
      ]
    }}
  ],
  "union": null,                    // 可选：UNION 查询，格式 {{"type": "ALL", "queries": [子MQL数组]}}
  "cte": null,                      // 可选：CTE公共表表达式，格式 [{{"name": "CTE名", "query": 子MQL}}]
  "from_cte": null,                 // 可选：主查询引用 CTE 作为数据源，格式见规则 10
  "queryResultType": "DATA"
}}

⚠️ 元数据格式说明：
- 可用指标/维度格式：`展示名 [name:逻辑名] | 其他信息`
- 理解用户意图时参考"展示名"（如"销售额"、"街道"）
- 输出 MQL 时必须使用 [name:xxx] 中的"逻辑名"（如 "gmv"、"streetName"）
- 示例：用户说"查询各街道的销售额" → metrics: ["gmv"], dimensions: ["streetName"]

⚠️ 关键规则：

11. **UNION 查询特殊规则**：
   - 当使用 union 字段时，与 union 同一级的 json 字段（dimensions、metrics、filters、having 等）会被完全忽略
   - 所有查询逻辑（维度、指标、过滤、排序等）都必须在 union.queries 的每个子查询中独立定义
   - UNION 可以作为主查询，也可以作为 CTE 子查询使用
   - 如果 UNION 作为 CTE 子查询，主查询仍然可以使用 dimensions、metrics、filters 等字段
   - UNION 子查询中的 limit 会被自动移除，LIMIT 会在 UNION 的最外层应用
   - 示例1（UNION 作为主查询）：{{"union": {{"type": "ALL", "queries": [子查询1, 子查询2]}}, "queryResultType": "DATA"}}
   - 示例2（UNION 作为 CTE 子查询）：
     {{"cte": [{{"name": "union_data", "query": {{"union": {{"type": "ALL", "queries": [...]}}}}}}], "from_cte": "union_data", "dimensions": [...], "metrics": [...]}}

1. **时间过滤规则**：
   - 时间过滤统一使用 `filters` 字段，与普通维度过滤相同
   - 支持多个时间类型字段的过滤（如创建时间、更新时间等）
   - 如果用户未指定时间范围，系统会根据视图的默认时间字段自动填充
   - 时间函数支持：TODAY(), YESTERDAY(), LAST_N_DAYS(n), THIS_MONTH(), THIS_YEAR(), DATE_SUB(), DATE_ADD() 等
   - 示例：filters: {{"operator": "AND", "conditions": [{{"field": "created_at", "op": ">=", "value": "LAST_N_DAYS(30)"}}]}}

2. **filters vs having 区分（极其重要）**：
   - `filters`：在聚合之前执行，只能过滤下面可过滤字段列表里的字段
   - `having`：在聚合之后执行，只能过滤指标或维度（聚合结果）
   - ⚠️ 常见错误：用户说"销售额大于1000的记录"，这是聚合后的过滤，必须用 having！
   - 例如："销售额大于1000的月份" → filters: [], having: "[gmv] > 1000"
   - 例如："去掉数量小于1的记录" → having: "[case_count] > 1"

3. **filters 结构化语法**：
   - filters 是一个结构化对象，包含 operator 和 conditions 字段
   - operator 可选值："AND"（默认）、"OR"
   - 每个条件是叶子条件或嵌套分组：
     - 叶子条件：`{{"field": "字段逻辑名", "op": "操作符", "value": "值"}}`
     - 嵌套分组：`{{"operator": "AND|OR", "conditions": [...]}}`
   - 支持的操作符：`=`、`!=`、`>`、`<`、`>=`、`<=`、`IN`、`NOT IN`、`LIKE`、`IS NULL`、`IS NOT NULL`
   - IN/NOT IN 的 value 是数组
   - LIKE 的 value 需包含 % 通配符
   - 向后兼容：filters 也可以是字符串数组（但推荐使用结构化格式）
   - 简单过滤示例：`{{"operator": "AND", "conditions": [{{"field": "channel", "op": "=", "value": "线上"}}]}}`
   - 复杂 OR 示例：`{{"operator": "OR", "conditions": [{{"operator": "AND", "conditions": [{{"field": "A", "op": "=", "value": "1"}}, {{"field": "B", "op": "LIKE", "value": "%关键词%"}}]}}, {{"operator": "AND", "conditions": [{{"field": "A", "op": "=", "value": "1"}}, {{"field": "B", "op": "LIKE", "value": "%其他%"}}]}}]}}`

4. **字段值选择**：
   - 必须从下方「可过滤字段」列表中选择字段
   - 值必须从字段的可选值中选择（如果提供了可选值列表）

5. **orderBy 排序规则**：
   - 可以按指标逻辑名或维度排序
   - 格式：`[{{"field": "字段名", "direction": "ASC|DESC"}}]`
   - 例如："按销售额从高到低" → orderBy: `[{{"field": "gmv", "direction": "DESC"}}]`

6. **distinct 去重规则**：
   - 布尔值，默认为 false
   - 例如："统计不重复用户数" → distinct: true

7. **windowFunctions 窗口函数规则**：
   - 格式：`[{{"alias": "别名", "func": "函数", "field": "字段", "partition": ["分区字段"], "orderBy": [{{"field": "排序字段", "direction": "ASC|DESC"}}]}}]`
   - 支持函数：SUM, AVG, COUNT, MAX, MIN, ROW_NUMBER, RANK
   - partition 和 orderBy 都是数组格式，orderBy 格式与主查询 orderBy 完全一致
   - 例如："计算累计销售额" → windowFunctions: `[{{"alias": "cumulative_gmv", "func": "SUM", "field": "gmv", "partition": [], "orderBy": [{{"field": "date__month", "direction": "ASC"}}]}}]`
   - 例如："各渠道内按销售额排名" → windowFunctions: `[{{"alias": "channel_rank", "func": "RANK", "field": "gmv", "partition": ["channel"], "orderBy": [{{"field": "gmv", "direction": "DESC"}}]}}]`
   
8. **union 合并查询规则**：
   - 格式：`{{"type": "ALL"|"", "queries": [子MQL1, 子MQL2, ...]}}`
   - type 为 "ALL" 表示 UNION ALL，为空字符串表示 UNION（去重）
   - queries 数组中至少包含 2 个子 MQL
   - 子 MQL 与主 MQL 结构相同，不需要包含 union/cte 字段
   - 例如："分别查看北京和上海的销售额" → 用 union 合并两个地区的查询

9. **cte 公共表表达式规则**：
   - 格式：`[{{"name": "CTE名称", "query": 子MQL}}]`
   - name 必须唯一，不能重复
   - query 是一个完整的子 MQL（与主 MQL 结构相同，不需要包含 cte 字段）
   - 如果主查询需要从 CTE 读取数据（而不是从物理表），必须使用 from_cte 字段指定数据源

10. **from_cte 引用 CTE 作为数据源**：
   - 当主查询需要从 CTE 读取数据时使用（如 CTE 做了过滤/排名后，主查询查 CTE 结果）
   - 简单引用：`"from_cte": "CTE_名称"` → FROM CTE_名称
   - 多 CTE 关联：`"from_cte": {{"table": "CTE_A", "joins": [{{"table": "CTE_B", "type": "INNER", "on": "CTE_A.id = CTE_B.id"}}]}}`
   - **⚠️ 重要约束：主查询只能使用 CTE 返回的字段！**
     - 可用字段：CTE 中定义的 dimensions、metrics、windowFunctions 的别名、constants
     - 禁止使用：CTE 中未返回的原表字段、原表维度、原表时间字段
     - 例如：CTE 返回了 `街道`、`上报数`、`排名`（窗口函数），主查询只能使用这三个字段
     - 禁止：主查询的 filters 引用原表的 `创建时间`（CTE 已完成时间过滤）
     - 禁止：主查询的 dimensions 使用原表的其他维度（CTE 未返回）
   - 主查询不再需要 metricDefinitions（CTE 已完成聚合）
   - 窗口函数列（如 `排名`）虽然可以用于 GROUP BY，但不必要（CTE 已计算好）
   - 例如："前三街道各小类" → CTE 做街道排名过滤，主查询 from_cte 引用 CTE 补充小类维度

重要说明：
1. **增量修改逻辑**：如果下方提供了"引用上下文 (Quoted MQL)"，你的任务是基于该上下文进行**增量修改**。
   - 保持原有的指标、维度和筛选，除非用户明确要求删除或替换。
   - 如果用户提出补充要求（如"再看下地区维度"），应将新维度合并到原有 dimensions 列表中。
   - 如果用户提出冲突要求（如"把月份改为4月"），应替换原 MQL 中的对应部分。
2. **元数据映射**：必须严格遵守下方提供的元数据映射列表。
3. **时间粒度选择**：对于涉及趋势查询（按月、按年等），必须直接从维度列表中选择对应的逻辑名（如 `date__month`）。

可用指标列表（格式：展示名 [name:逻辑名]）:
{metrics}

可用维度列表（格式：展示名 [name:逻辑名]）:
{dimensions}

可过滤字段列表（格式：展示名 [name:逻辑名] | 类型 | 说明 | 可选值）:
{filterable_fields}

时间函数规范（严格执行）：
1. 月度截断：DateTrunc([字段], 'MONTH') = 'YYYY-MM-01'
2. 年度截断：DateTrunc([字段], 'YEAR') = 'YYYY-01-01'
3. 月份加减：AddMonths([字段], -12) // 减 12 个月表示去年同期
4. 相对时间：TODAY(), YESTERDAY(), LAST_N_DAYS(n), LAST_N_MONTHS(n), LAST_N_YEARS(n), THIS_WEEK(), THIS_MONTH(), THIS_YEAR()
5. 范围查询：[字段] BETWEEN '2025-01-01' AND '2025-04-30'
6. 日期计算：DATE_SUB(CURDATE(), INTERVAL 3 YEAR), DATE_ADD(CURDATE(), INTERVAL 3 MONTH)

重要说明：
- 时间过滤统一使用 filters 字段，字段名必须是 [name:xxx] 中的"逻辑名"
- 支持多个时间类型字段的过滤（如创建时间、更新时间等）
- 如果用户未指定时间范围，系统会自动应用默认时间范围
- 禁止将函数名放在中括号内，例如 [TODAY](-7) 是错误的，应为 TODAY(-7) 或 LAST_N_DAYS(7)
- 禁止在 filters 中使用非白名单函数

示例1（基础查询 - 使用 filters 进行时间过滤）：
用户："线上渠道2025年4月的销售额"
MQL：
{{
  "dimensions": [],
  "metricDefinitions": {{ "gmv_alias": {{ "refMetric": "gmv" }} }},
  "metrics": ["gmv_alias"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "channel", "op": "=", "value": "线上"}},
      {{"field": "date", "op": ">=", "value": "LAST_N_DAYS(30)"}}
    ]
  }},
  "having": [],
  "orderBy": [],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例2（having 聚合后过滤）：
用户："已完成订单中金额大于1000的订单数"
MQL：
{{
  "dimensions": [],
  "metricDefinitions": {{ "order_count_alias": {{ "refMetric": "order_count" }} }},
  "metrics": ["order_count_alias"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "order_status", "op": "=", "value": "完成"}}
    ]
  }},
  "having": ["[order_count_alias] > 1000"],
  "orderBy": [],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例3（排序 + 时间过滤）：
用户："2025年4月各渠道的销售额，按销售额从高到低排序"
MQL：
{{
  "dimensions": ["channel"],
  "metricDefinitions": {{}},
  "metrics": ["gmv"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "date", "op": ">=", "value": "THIS_MONTH()"}}
    ]
  }},
  "having": [],
  "orderBy": [{{"field": "gmv", "direction": "DESC"}}],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例3b（近N年过滤 - 使用 filters）：
用户："近三年各产品销售额"
MQL：
{{
  "dimensions": ["product"],
  "metricDefinitions": {{}},
  "metrics": ["gmv"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "created_at", "op": ">=", "value": "LAST_N_YEARS(3)"}}
    ]
  }},
  "having": [],
  "orderBy": [],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例3c（近N年 + having + orderBy）：
用户："近三年各街道立案数，立案数不能小于1，根据立案数降序"
MQL：
{{
  "dimensions": ["streetName"],
  "metricDefinitions": {{ "case_count": {{ "refMetric": "case_count", "aggregation": "SUM" }} }},
  "metrics": ["case_count"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "created_at", "op": ">=", "value": "LAST_N_YEARS(3)"}}
    ]
  }},
  "having": ["[case_count] >= 1"],
  "orderBy": [{{"field": "case_count", "direction": "DESC"}}],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例4（年同比 + 排序）：
用户："2025年4月各渠道的销售额及年同比，按年同比从高到低排序"
MQL：
{{
  "dimensions": ["channel"],
  "metricDefinitions": {{
    "gmv": {{ "refMetric": "gmv" }},
    "gmv_yoy": {{ "refMetric": "gmv", "indirections": ["sameperiod__yoy__growth"] }}
  }},
  "metrics": ["gmv", "gmv_yoy"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "date", "op": ">=", "value": "THIS_MONTH()"}}
    ]
  }},
  "having": [],
  "orderBy": [{{"field": "gmv_yoy", "direction": "DESC"}}],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例5（窗口函数 - 累计）：
用户："查看每月销售额及年度累计销售额"
MQL：
{{
  "dimensions": ["date__month"],
  "metricDefinitions": {{}},
  "metrics": ["gmv"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "date", "op": ">=", "value": "THIS_YEAR()"}}
    ]
  }},
  "having": [],
  "orderBy": [{{"field": "date__month", "direction": "ASC"}}],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [{{"alias": "yearly_cumulative", "func": "SUM", "field": "gmv", "partition": [], "orderBy": [{{"field": "date__month", "direction": "ASC"}}]}}],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例6（having 过滤 - 指标过滤）：
用户："找出销售额大于10000的月份"
MQL：
{{
  "dimensions": ["date__month"],
  "metricDefinitions": {{}},
  "metrics": ["gmv"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "date", "op": ">=", "value": "THIS_YEAR()"}}
    ]
  }},
  "having": ["[gmv] > 10000"],
  "orderBy": [{{"field": "gmv", "direction": "DESC"}}],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例7（distinct 去重）：
用户："统计2025年4月有多少不重复用户下单"
MQL：
{{
  "dimensions": [],
  "metricDefinitions": {{}},
  "metrics": ["user_count"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "date", "op": ">=", "value": "THIS_MONTH()"}}
    ]
  }},
  "having": [],
  "orderBy": [],
  "distinct": true,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例8（CTE 公共表表达式 - 先算中间结果）：
用户："先计算各月销售额，再找出销售额超过月均值的月份"
MQL：
{{
  "dimensions": [],
  "metricDefinitions": {{}},
  "metrics": ["gmv"],
  "filters": {{
    "operator": "AND",
    "conditions": [
      {{"field": "date", "op": ">=", "value": "THIS_YEAR()"}}
    ]
  }},
  "having": ["[gmv] > [monthly_avg_gmv]"],
  "orderBy": [{{"field": "gmv", "direction": "DESC"}}],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": [{{"name": "monthly_avg_gmv", "query": {{"dimensions": [], "metricDefinitions": {{}}, "metrics": ["gmv"], "filters": {{"operator": "AND", "conditions": [{{"field": "date", "op": ">=", "value": "THIS_YEAR()"}}]}}, "having": [], "orderBy": [], "distinct": false, "limit": 1, "windowFunctions": [], "union": null, "cte": null}}}}],
  "queryResultType": "DATA"
}}

示例8b（CTE + from_cte - 主查询引用 CTE 数据源）：
用户："近三年各街道上报数，取前三街道"
MQL：
{{
  "dimensions": ["streetName", "reportNum", "rn"],
  "metrics": [],
  "filters": {{}},
  "having": ["[rn] <= 3"],
  "orderBy": [{{"field": "rn", "direction": "ASC"}}],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": [{{"name": "CTE_street_report", "query": {{"dimensions": ["streetName"], "metricDefinitions": {{ "reportNum_alias": {{ "refMetric": "reportNum", "aggregation": "SUM" }} }}, "metrics": ["reportNum_alias"], "filters": {{"operator": "AND", "conditions": [{{"field": "created_at", "op": ">=", "value": "LAST_N_YEARS(3)"}}]}}, "having": [], "orderBy": [{{"field": "reportNum_alias", "direction": "DESC"}}], "distinct": false, "limit": 1000, "windowFunctions": [{{"alias": "rn", "func": "ROW_NUMBER", "field": "reportNum_alias", "partition": [], "orderBy": [{{"field": "reportNum_alias", "direction": "DESC"}}]}}], "union": null, "cte": null}}}}],
  "from_cte": "CTE_street_report",
  "queryResultType": "DATA"
}}

示例9（UNION 合并查询 - 合并多个不同指标查询结果）：
用户："分别查询线上和线下渠道2025年4月的销售额，合并为一个结果集"
MQL：
{{
  "union": {{"type": "ALL", "queries": [
    {{"dimensions": ["channel"], "metricDefinitions": {{}}, "metrics": ["gmv"], "filters": {{"operator": "AND", "conditions": [{{"field": "channel", "op": "=", "value": "线上"}}, {{"field": "date", "op": ">=", "value": "THIS_MONTH()"}}]}}, "having": [], "orderBy": [], "distinct": false, "limit": 1000, "windowFunctions": [], "cte": null}},
    {{"dimensions": ["channel"], "metricDefinitions": {{}}, "metrics": ["gmv"], "filters": {{"operator": "AND", "conditions": [{{"field": "channel", "op": "=", "value": "线下"}}, {{"field": "date", "op": ">=", "value": "THIS_MONTH()"}}]}}, "having": [], "orderBy": [], "distinct": false, "limit": 1000, "windowFunctions": [], "cte": null}}
  ]}},
  "cte": null,
  "queryResultType": "DATA"
}}

注意：使用 union 时，主查询的 dimensions、metrics、filters 等字段会被忽略。所有查询逻辑都应该在 union.queries 的每个子查询中定义。

示例10（复杂 OR 条件 - 多组 AND 条件用 OR 连接）：
用户："查询event_type_id为'1'且main_type_name包含'市容'或'宣传'或'施工'或'街面'或'其他'的所有记录"
MQL：
{{
  "dimensions": [],
  "metricDefinitions": {{ "inst_count_alias": {{ "refMetric": "inst_count", "aggregation": "COUNT" }} }},
  "metrics": ["inst_count_alias"],
  "filters": {{
    "operator": "OR",
    "conditions": [
      {{"operator": "AND", "conditions": [{{"field": "event_type_id", "op": "=", "value": "1"}}, {{"field": "main_type_name", "op": "LIKE", "value": "%市容%"}}]}},
      {{"operator": "AND", "conditions": [{{"field": "event_type_id", "op": "=", "value": "1"}}, {{"field": "main_type_name", "op": "LIKE", "value": "%宣传%"}}]}},
      {{"operator": "AND", "conditions": [{{"field": "event_type_id", "op": "=", "value": "1"}}, {{"field": "main_type_name", "op": "LIKE", "value": "%施工%"}}]}},
      {{"operator": "AND", "conditions": [{{"field": "event_type_id", "op": "=", "value": "1"}}, {{"field": "main_type_name", "op": "LIKE", "value": "%街面%"}}]}},
      {{"operator": "AND", "conditions": [{{"field": "event_type_id", "op": "=", "value": "1"}}, {{"field": "main_type_name", "op": "LIKE", "value": "%其他%"}}]}}
    ]
  }},
  "having": [],
  "orderBy": [],
  "distinct": false,
  "limit": 1000,
  "windowFunctions": [],
  "union": null,
  "cte": null,
  "queryResultType": "DATA"
}}

示例11（UNION + 常量列 - 在结果中返回固定的分类代码和单位）：
用户："统计市容环境、宣传广告等不同问题大类的案件数，返回分类代码（01, 02...）、分类名称和单位（件）"
MQL：
{{
  "union": {{
    "type": "ALL",
    "queries": [
      {{
        "constants": [
          {{"name": "code", "value": "01", "type": "string"}},
          {{"name": "category", "value": "市容环境", "type": "string"}},
          {{"name": "unit", "value": "件", "type": "string"}}
        ],
        "dimensions": [],
        "metricDefinitions": {{}},
        "metrics": ["case_count"],
        "filters": {{
          "operator": "AND",
          "conditions": [
            {{"field": "event_type_id", "op": "=", "value": "1"}},
            {{"field": "main_type_name", "op": "LIKE", "value": "%市容%"}}
          ]
        }},
        "having": [],
        "orderBy": [],
        "distinct": false,
        "limit": 1000,
        "windowFunctions": [],
        "cte": null
      }},
      {{
        "constants": [
          {{"name": "code", "value": "02", "type": "string"}},
          {{"name": "category", "value": "宣传广告", "type": "string"}},
          {{"name": "unit", "value": "件", "type": "string"}}
        ],
        "dimensions": [],
        "metricDefinitions": {{}},
        "metrics": ["case_count"],
        "filters": {{
          "operator": "AND",
          "conditions": [
            {{"field": "event_type_id", "op": "=", "value": "1"}},
            {{"field": "main_type_name", "op": "LIKE", "value": "%宣传%"}}
          ]
        }},
        "having": [],
        "orderBy": [],
        "distinct": false,
        "limit": 1000,
        "windowFunctions": [],
        "cte": null
      }}
    ]
  }},
  "cte": null,
  "queryResultType": "DATA"
}}

常量列（Constants）使用说明：
- 当查询需要在结果中返回固定值（如分类代码、单位、标签等）时，使用 constants 字段
- constants 是一个数组，每个常量定义包含三个字段：
  - name: 常量列的别名（如 "code", "category", "unit"）
  - value: 常量值（如 "01", "市容环境", "件"）
  - type: 常量类型（"string" 或 "number"），默认 "string"
- 常量列通常用于 UNION 查询，为每个子查询添加固定的分类信息
- 常量列不参与 GROUP BY，直接放在 SELECT 子句中

请将以下自然语言转换为 MQL JSON。
注意：如果这是修复尝试，请参考下方的"错误信息"进行修正。
{error_info}
用户：{query}
MQL："""


def _build_metadata_strings(
    db: Session, 
    context: Optional[dict] = None,
    metrics_objs: list = None,
    dimensions_objs: list = None
) -> tuple:
    """构建元数据字符串（metrics、dimensions、filterable_fields）
    
    从数据库中获取指标、维度、可过滤字段，格式化为 prompt 所需的字符串。
    提取为独立函数以便修正工具复用。
    
    Args:
        db: 数据库会话
        context: 可选上下文（suggested_metrics、suggested_dimensions）
        metrics_objs: 已查询的 Metric ORM 对象列表（如已查询可传入，避免重复查 DB）
        dimensions_objs: 已查询的 Dimension ORM 对象列表（如已查询可传入，避免重复查 DB）
    
    Returns:
        (metrics_str, dimensions_str, filterable_fields_str)
    """
    # 优先使用传入的 ORM 对象，避免重复查 DB
    if metrics_objs is None:
        metrics_query = db.query(Metric)
        if context and context.get("suggested_metrics"):
            from sqlalchemy import or_
            metrics_query = metrics_query.filter(or_(
                Metric.name.in_(context["suggested_metrics"]),
                Metric.display_name.in_(context["suggested_metrics"])
            ))
        metrics = metrics_query.all()
    else:
        metrics = metrics_objs

    if dimensions_objs is None:
        dimensions_query = db.query(Dimension)
        if context and context.get("suggested_dimensions"):
            from sqlalchemy import or_
            dimensions_query = dimensions_query.filter(or_(
                Dimension.name.in_(context["suggested_dimensions"]),
                Dimension.display_name.in_(context["suggested_dimensions"])
            ))
        dimensions = dimensions_query.all()
    else:
        dimensions = dimensions_objs
    
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
    
    # 格式：展示名 [name:逻辑名]，LLM 理解时用展示名，输出 MQL 时用逻辑名
    metrics_list = [f"- {m.display_name or m.name} [name:{m.name}]" for m in metrics]
    metrics_str = "\n".join(metrics_list) or "- 销售额 [name:gmv]"
    
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
            dim_info = f"- {d.display_name or d.name} [name:{d.name}]"
            dims_list.append(dim_info)
            continue
            
        # 处理时间维度：衍生出多个虚拟维度并替换原始维度
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
                # 逻辑名：name__标签 (例如: created_at__month)
                virtual_name = f"{d.name}__{suffix}"
                dims_list.append(f"- {d.display_name or d.name} {label} [name:{virtual_name}]")
                added_any = True
        
        # 兜底逻辑
        if not added_any:
            dim_info = f"- {d.display_name or d.name} [name:{d.name}]"
            dims_list.append(dim_info)
    
    dimensions_str = "\n".join(dims_list) or "- 日期 [name:date]"

    # 构建可过滤字段列表
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
                
                filterable_fields_list.append(f"- {display_name} [name:{field_name}] | 类型: {field_type} | 说明: {description or source_comment}{optional_values}")

    filterable_fields_str = "\n".join(filterable_fields_list) or "- 渠道 [name:channel] | 类型: VARCHAR | 说明: 主要推广渠道 | 可选值: 直搜, 搜索引擎, 外部链接"
    
    return metrics_str, dimensions_str, filterable_fields_str


async def parse_natural_language(
    natural_language: str,
    provider: str,
    model_name: str,
    api_key: Optional[str],
    api_base: Optional[str],
    config_params: Optional[dict],
    db: Session,
    context: Optional[dict] = None,
    prompt_strings: Optional[tuple] = None
) -> dict:
    """Parse natural language query to MQL with multi-turn correction
    
    Args:
        prompt_strings: 可选的预构建元数据字符串 (metrics_str, dimensions_str, filterable_fields_str)，
                        如果提供则跳过 DB 查询，直接复用准备阶段的结果
    """
    # 使用新的模块化校验器
    from app.utils.mql_validator.composite_validator import MQLCompositeValidator
    validator = MQLCompositeValidator(db)
    
    # 1. 获取元数据字符串（优先使用预构建的，否则查 DB）
    if prompt_strings:
        metrics_str, dimensions_str, filterable_fields_str = prompt_strings
    else:
        metrics_str, dimensions_str, filterable_fields_str = _build_metadata_strings(db, context)

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
            
            # 3. Strong Validation Integration (使用新的模块化校验器)
            result = validator.validate(mql)
            if result.is_valid:
                # Success! Generate steps for UI
                used_metrics = mql.get("metrics", [])
                used_dims = mql.get("dimensions", [])
                
                # 从 filters 中提取时间范围（已废弃 timeConstraint）
                time_range_display = "全部时间"
                filters = mql.get("filters", {})
                if filters and isinstance(filters, dict):
                    conditions = filters.get("conditions", [])
                    for cond in conditions:
                        if isinstance(cond, dict) and "field" in cond:
                            # 检查是否是时间字段（通过字段名判断）
                            field_name = cond.get("field", "")
                            if any(kw in field_name.lower() for kw in ["date", "time", "创建时间", "更新时间", "时间"]):
                                value = cond.get("value", "")
                                if value:
                                    time_range_display = str(value)
                                break
                
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
                # 将错误列表转换为错误信息字符串
                error_messages = [f"{e.code}: {e.message}" for e in result.errors]
                error_info = "; ".join(error_messages)
                current_attempt += 1
                print(f"MQL Validation failed (Attempt {current_attempt}): {error_info}")
                
        except Exception as e:
            error_info = f"JSON 解析或系统错误: {str(e)}"
            current_attempt += 1
            print(f"MQL Parsing error (Attempt {current_attempt}): {str(e)}")

    # 4. Final fallback or error return
    final_mql = last_mql or {
        "dimensions": [], "dimensionConfigs": {}, "metricDefinitions": {}, "metrics": [],
        "limit": 1000, "queryResultType": "DATA", "filters": {}
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
