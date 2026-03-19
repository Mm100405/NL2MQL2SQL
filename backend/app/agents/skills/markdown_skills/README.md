# Markdown Skill 编写指南

本文档说明如何编写自定义的Markdown Skill。

## 📝 Markdown Skill 结构

一个标准的Markdown Skill文件包含以下部分：

```markdown
# Skill: Skill名称

## 描述
Skill的功能描述

## 输入
- `参数名` (类型): 参数说明
- `参数名` (类型, 可选): 可选参数说明

## 输出
- `输出字段` (类型): 输出说明

## Prompt 模板
```
这里编写LLM的Prompt模板，使用{参数名}作为占位符
```

## 实现逻辑
```yaml
model:
  temperature: 0.3
  max_tokens: 1024
output_format: json
```

## 示例
输入和输出示例
```

---

## 🎯 各部分详细说明

### 1. Skill名称（必需）

```markdown
# Skill: 结果解释
```

- 必须以 `# Skill:` 开头
- 名称应简洁、描述性强
- 使用中文或英文，建议使用英文（便于代码调用）

### 2. 描述（必需）

```markdown
## 描述
使用自然语言解释查询结果，生成易于理解的总结和洞察。
```

- 简要说明Skill的功能
- 帮助LLM路由器理解何时使用此Skill

### 3. 输入（必需）

```markdown
## 输入
- `query_result` (object): 查询结果，包含columns、data、total_count
- `natural_language` (string): 用户的原始查询
- `intent_type` (string, 可选): 意图类型
```

格式：`- 参数名 (类型): 说明`

类型包括：
- `string`: 字符串
- `number`: 数字
- `boolean`: 布尔值
- `object`: 对象
- `array`: 数组

在说明中添加"可选"表示可选参数。

### 4. 输出（必需）

```markdown
## 输出
- `summary` (string): 结果总结
- `insights` (array): 洞察列表
- `visualization` (object): 可视化建议
```

定义Skill的输出字段，帮助调用方理解返回的数据结构。

### 5. Prompt模板（必需）

```markdown
## Prompt 模板
```
你是一个专业的数据分析师。请解释查询结果：

用户查询：{natural_language}

查询结果：{query_result}

请返回JSON格式的分析结果。
```
```

**重要**：
- 使用 `{参数名}` 作为占位符
- 执行时会自动替换为实际值
- 如果参数是对象或数组，会自动转换为JSON字符串

### 6. 实现逻辑（可选）

```markdown
## 实现逻辑
```yaml
model:
  temperature: 0.3
  max_tokens: 1024
  top_p: 0.9
output_format: json
```
```

支持的配置：
- `model.temperature`: 温度参数（0-1）
- `model.max_tokens`: 最大Token数
- `model.top_p`: Top-p采样
- `output_format`: 输出格式（json/text）

### 7. 示例（推荐）

```markdown
## 示例

### 输入
```json
{
  "query_result": {...},
  "natural_language": "查询销售额"
}
```

### 输出
```json
{
  "summary": "结果总结",
  "insights": ["洞察1", "洞察2"]
}
```
```

提供输入输出示例，帮助理解Skill的用法。

---

## 🚀 创建自定义Skill的步骤

### Step 1: 创建文件

在以下目录创建 `.md` 文件：

- **系统Skill**: `backend/app/agents/skills/markdown_skills/`
- **用户Skill**: `.codebuddy/skills/`

### Step 2: 编写内容

按照上述结构编写Skill定义。

### Step 3: 测试验证

```python
from app.agents.skills.markdown_parser import MarkdownSkill
from app.agents.skills.markdown_executor import MarkdownSkillExecutor

# 加载Skill
skill = MarkdownSkill.from_file("path/to/your_skill.md")

# 创建执行器
executor = MarkdownSkillExecutor(skill, db)

# 执行
result = await executor.execute({
    "param1": "value1",
    "param2": "value2"
})

print(result)
```

---

## 📚 最佳实践

### 1. Prompt设计

✅ **好的Prompt**:
```
分析查询结果，返回JSON格式的总结和洞察。
要求：
1. 总结不超过2句话
2. 提供3-5个洞察
3. 推荐可视化类型
```

❌ **不好的Prompt**:
```
分析这个数据
```

### 2. 参数设计

✅ **推荐**:
- 参数数量控制在3-5个
- 必需参数和可选参数清晰区分
- 参数名使用下划线命名法（snake_case）

❌ **不推荐**:
- 参数过多（>10个）
- 参数命名不统一
- 缺少参数说明

### 3. 输出格式

✅ **推荐**:
- 使用JSON格式输出
- 字段命名清晰
- 包含示例

❌ **不推荐**:
- 输出格式不明确
- 字段命名混乱

---

## 🔧 高级功能

### 条件分支

在Prompt中使用条件判断：

```markdown
## Prompt 模板
```
{#if intent_type}
## 意图类型
{intent_type}
{/if}

请分析数据...
```
```

### 多语言支持

```markdown
## Prompt 模板
```
{#if language == "zh"}
请用中文回答...
{#else}
Please answer in English...
{/if}
```
```

---

## 📖 示例Skill

### 数据质量检查Skill

```markdown
# Skill: 数据质量检查

## 描述
检查查询结果的数据质量，发现异常值和缺失值。

## 输入
- `query_result` (object): 查询结果
- `check_rules` (array, 可选): 检查规则

## 输出
- `quality_score` (number): 质量评分（0-100）
- `issues` (array): 问题列表
- `suggestions` (array): 改进建议

## Prompt 模板
```
检查数据质量：

数据：{query_result}

请返回JSON格式的检查结果：
{
  "quality_score": 85,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}
```

## 实现逻辑
```yaml
model:
  temperature: 0.2
  max_tokens: 512
```
```

---

## ❓ 常见问题

### Q1: Skill文件放在哪里？

**系统内置**: `backend/app/agents/skills/markdown_skills/`
**用户自定义**: `.codebuddy/skills/`

### Q2: 如何调试Skill？

使用MarkdownSkillExecutor测试：

```python
from app.agents.skills.markdown_parser import MarkdownSkill
from app.agents.skills.markdown_executor import MarkdownSkillExecutor

skill = MarkdownSkill.from_file("your_skill.md")
executor = MarkdownSkillExecutor(skill, db)
result = await executor.execute(inputs)
```

### Q3: Skill如何被调用？

Skills通过SkillLoader加载，然后被Node调用：

```python
from app.agents.skills.skill_loader import SkillLoader

loader = SkillLoader(db)
skill = loader.get_skill("your_skill_name")
result = await skill.execute(inputs)
```

---

## 🎉 总结

Markdown Skill是一个轻量级的Skill定义方式，适合：

✅ **适合场景**：
- LLM驱动的任务
- 需要频繁调整Prompt
- 非技术用户也能修改

❌ **不适合场景**：
- 复杂的业务逻辑
- 需要数据库操作
- 需要高性能计算

开始创建你的第一个Markdown Skill吧！🚀
