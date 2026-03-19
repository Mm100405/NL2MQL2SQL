# Skill: 结果解释

## 描述
使用自然语言解释查询结果，生成易于理解的总结和洞察。

## 输入
- `query_result` (object): 查询结果，包含columns、data、total_count
- `natural_language` (string): 用户的原始查询
- `intent_type` (string, 可选): 意图类型（trend、comparison、aggregation等）

## 输出
- `summary` (string): 结果总结
- `insights` (array): 洞察列表
- `visualization` (object): 可视化建议

## Prompt 模板
```
你是一个专业的数据分析师。请解释查询结果并生成洞察。

## 用户查询
{natural_language}

## 查询结果
{query_result}

## 要求
1. 用1-2句话概括查询结果
2. 从数据中发现3-5个有价值的洞察
3. 推荐最适合的可视化类型

## 可视化类型说明
- line: 折线图，适合趋势分析
- bar: 柱状图，适合对比分析
- pie: 饼图，适合占比分析
- table: 表格，适合详细数据展示

## 输出格式

请返回JSON格式的结果：

```json
{
  "summary": "结果总结",
  "insights": ["洞察1", "洞察2", "洞察3"],
  "visualization": {
    "type": "line",
    "description": "为什么选择这个可视化类型"
  }
}
```
```

## 实现逻辑
```yaml
model:
  temperature: 0.3
  max_tokens: 1024

output_format: json
```

## 示例

### 输入
```json
{
  "query_result": {
    "columns": ["日期", "销售额"],
    "data": [
      ["2025-01-01", 1000000],
      ["2025-01-02", 1200000],
      ["2025-01-03", 1150000]
    ],
    "total_count": 3
  },
  "natural_language": "查询最近3天的销售额",
  "intent_type": "trend"
}
```

### 输出
```json
{
  "summary": "最近3天销售额从100万增长到120万，整体呈上升趋势，日平均销售额约为111.7万元",
  "insights": [
    "销售额呈现上升趋势，从第1天的100万增长到第2天的120万，涨幅为20%",
    "第3天销售额略有回落，降至115万，但仍高于第1天水平",
    "3天总销售额为335万元，日平均销售额约为111.7万元"
  ],
  "visualization": {
    "type": "line",
    "description": "由于查询意图是趋势分析，折线图最适合展示销售额的变化趋势"
  }
}
```
