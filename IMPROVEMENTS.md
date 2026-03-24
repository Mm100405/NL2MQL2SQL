# 系统改进方向与方案

## 📋 概述

本文档记录 NL2MQL2SQL 系统的改进方向、已完成方案和未来规划，包括自主决策机制优化、WrenAI 集成分析等。

**架构对比**：
- **NL2MQL2SQL**：LangGraph + Deep Agents（自研）+ MQL V2（sqlglot）
- **WrenAI**：Wren Engine（Rust + DataFusion）+ AI Service + MDL

---

## 一、自主决策机制分析

### 1.1 当前实现分析

**文件**: `backend/app/agents/deep_agents/workflow.py`

**当前工作流**：
```
preparation (准备)
    ↓
generation (生成 MQL)
    ↓
validation (验证)
    ↓
    correction (修正) ← 唯一的条件路由
    ↓
translation (转换为 SQL)
    ↓
execution (执行查询)
    ↓
interpretation (结果分析)
```

**唯一条件路由**：`should_correct` 函数

```python
def should_correct(state: DeepAgentState) -> str:
    """判断是否需要修正 MQL"""
    mql_errors = state.get("mql_errors", [])
    mql_attempts = state.get("mql_attempts", 0)
    max_retries = state.get("max_retries", 3)

    if mql_errors and mql_attempts < max_retries:
        return "correction"
    else:
        return "translation"
```

---

### 1.2 问题诊断

#### 核心问题

1. **固定流程，无真正决策**
   - 工作流是预设的 7 节点线性流程
   - 所有查询都走相同的流程

2. **Deep Agents 自主决策能力被限制**
   - 虽然启用了 `enable_planning=True`
   - 但将整个工作流打包成一个工具

3. **Planning Tool 未真正使用**
   - Deep Agents 的 Planning Tool 可以自动规划任务
   - 但当前实现绕过了这个能力

---

### 1.3 对比分析

#### 当前实现（固定流程）

```
用户问题 → 固定工作流 → 结果
             ↓
    preparation → generation → validation → correction → translation → execution → interpretation
```

**特点**：
- ✅ 流程可控，易于调试
- ✅ 逻辑清晰，可预测
- ❌ 无法根据问题类型调整流程
- ❌ 无法智能跳过不必要的步骤

#### 理想实现（自主决策）

```
用户问题 → Deep Agents Planning → 动态工具选择 → 结果
```

**特点**：
- ✅ 根据问题复杂度自动调整流程
- ✅ 可以跳过不必要的步骤
- ✅ 可以并行执行独立任务
- ❌ 流程不可控，难以调试

---

## 二、改进方案

### 方案 1: 混合模式（推荐 ⭐）

**思路**: 保留固定工作流作为默认，对特定场景启用自主决策

```python
# 创建多个独立工具
tools = [
    retrieve_metadata_tool,      # 元数据检索
    generate_mql_tool,          # MQL 生成
    validate_mql_tool,          # MQL 验证
    translate_to_sql_tool,      # SQL 转换
    execute_query_tool,         # 查询执行
    analyze_result_tool         # 结果分析
]

agent = create_deep_agent(
    model=self.config["model"],
    system_prompt=self.config["system_prompt"],
    tools=tools,  # 提供独立工具，让 Agent 自主选择
    enable_planning=True,  # ✅ 启用任务规划
    enable_file_system=False
)
```

---

### 方案 2: 完全自主决策模式

**思路**: 完全依赖 Deep Agents 的自主决策能力

```python
agent = create_deep_agent(
    model=self.config["model"],
    system_prompt=system_prompt,
    tools=tools,
    enable_planning=True,
    enable_file_system=True,
    file_system_root="./data/skills",
)
```

---

### 方案 3: 增强条件路由

**思路**: 在固定工作流中增加更多条件路由

```python
def should_skip_mql(state: DeepAgentState) -> str:
    intent_type = state.get("intent_type", "aggregation")
    if intent_type == "list":
        return "translation"
    else:
        return "generation"
```

---

## 三、方案对比

| 方案 | 优点 | 缺点 | 实施难度 | 推荐度 |
|------|------|------|----------|--------|
| **方案1: 混合模式** | 兼顾可控性和灵活性<br>渐进式改进<br>风险低 | 需要维护两套逻辑 | ⭐⭐ 中 | ⭐⭐⭐⭐⭐ 强烈推荐 |
| **方案2: 完全自主** | 最大化 AI 能力 | 不可控<br>难以调试 | ⭐⭐⭐ 高 | ⭐⭐⭐ 中等推荐 |
| **方案3: 增强路由** | 保持可控<br>易于调试 | 决策仍有限 | ⭐ 低 | ⭐⭐ 中等推荐 |

---

## 四、推荐实施计划

### Phase 1: 快速改进（1-2周）

**任务**：
1. ✅ 实现 `should_skip_mql` 条件路由
2. ✅ 实现 `should_skip_translation` 条件路由
3. ✅ 优化提示词，增加决策指导

**预期效果**: 简单查询节省 20-30% 步骤

---

### Phase 2: 混合模式（2-4周）

**任务**：
1. ✅ 实现问题复杂度分析
2. ✅ 创建独立工具集（不打包工作流）
3. ✅ 实现自主决策模式的执行逻辑

**预期效果**: 复杂查询成功率提升 30%，整体效率提升 20%

---

### Phase 3: 完全自主（可选，4-6周）

**任务**：
1. ✅ 定义丰富的工具集
2. ✅ 启用所有 Deep Agents 特性
3. ✅ 实现完整的错误处理和回退机制

---

## 五、已完成的重要改进

### 5.1 P0 问题修复

#### correct_mql 修复
- ✅ 改为异步函数
- ✅ 添加 LLM 智能修正逻辑
- ✅ 实现 `_build_correction_prompt()` 辅助函数

#### intent_analysis 添加
- ✅ 创建 `analyze_intent` 工具
- ✅ 实现 `_build_intent_analysis_prompt()` 辅助函数
- ✅ 集成到 `preparation_node` 工作流

### 5.2 Result Analysis 功能迁移

将旧架构中的 `ResultAnalysisSkill` 迁移到新架构的 `analyze_result` 工具

### 5.3 Agent API 启用 Skills

- ✅ 替换管理器为 `EnhancedDeepAgentsManager`
- ✅ 支持动态加载的 Skills

### 5.4 MQL Engine V2 重构

基于 sqlglot AST 重建 SQL 生成管线

**支持的 MQL V2 字段（11个）**：
| 字段 | 状态 |
|------|------|
| metrics | ✅ |
| metricDefinitions | ✅ |
| dimensions | ✅ |
| timeConstraint | ✅ |
| filters | ✅ |
| orderBy | ✅ |
| having | ✅ |
| distinct | ✅ |
| limit | ✅ |
| windowFunctions | ✅ |
| union/cte | ✅ |

---

## 六、WrenAI 架构分析

### 6.1 WrenAI 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (React + Next.js)                 │
│              Wren Dashboard / Wren AI UI                  │
└───────────────────────┬─────────────────────────────────┘
                        ↓ REST API / WebSocket
┌─────────────────────────────────────────────────────────┐
│              Wren AI Service (Python + LangChain)         │
│  - Agent Pipeline Manager                                │
│  - LLM Integration                                       │
│  - Model Metadata Management                             │
└───────────────────────┬─────────────────────────────────┘
                        ↓ gRPC / REST
┌─────────────────────────────────────────────────────────┐
│            Wren Engine (Rust + Apache DataFusion)       │
│  - MDL (Model Definition Language) Parser               │
│  - Semantic Layer Engine                                │
│  - SQL Generator (sqlglot)                              │
│  - Query Optimizer (DataFusion)                          │
│  - Ibis Server (Data Query)                              │
└───────────────────────┬─────────────────────────────────┘
                        ↓ SQL / Ibis Protocol
┌─────────────────────────────────────────────────────────┐
│               数据源 (11+ 数据源)                        │
│  MySQL, PostgreSQL, BigQuery, Snowflake, ...             │
└─────────────────────────────────────────────────────────┘
```

---

### 6.2 核心组件分析

#### 6.2.1 Wren Engine（Rust + Apache DataFusion）

**文件位置**: `otherproj/WrenAI/wren-engine/`

**核心功能**：
- ✅ **MDL Parser**：解析 Model Definition Language（语义层定义）
- ✅ **Semantic Layer Engine**：语义层解析和验证
- ✅ **SQL Generator**：基于 sqlglot 生成 SQL
- ✅ **Query Optimizer**：Apache DataFusion 查询优化
- ✅ **Ibis Server**：提供 Ibis 协议接口

**技术栈**：
```toml
[dependencies]
sqlglot = "19.0"  # SQL 解析和生成
datafusion = "38.0"  # 查询引擎
tonic = "0.11"  # gRPC
prost = "0.12"  # Protocol Buffers
```

**架构优势**：
- ✅ Rust 高性能：比 Python 性能高 10-50 倍
- ✅ Apache DataFusion：企业级查询引擎，支持复杂查询优化
- ✅ 内存安全：Rust 类型系统保证

**对比 NL2MQL2SQL**：
| 模块 | NL2MQL2SQL | WrenAI | 说明 |
|------|-----------|---------|------|
| SQL 引擎 | sqlglot (纯 Python) | Apache DataFusion (Rust) | WrenAI 性能更优 |
| 语义层 | MQL V2 (自研) | MDL (标准 JSON Schema) | WrenAI 标准化更好 |
| 查询优化 | 基础（sqlglot） | 高级（DataFusion） | WrenAI 优化更强 |

---

#### 6.2.2 Wren AI Service（Python + LangChain）

**文件位置**: `otherproj/WrenAI/wren-ai-service/`

**核心功能**：
- ✅ **Agent Pipeline Manager**：Agent Pipeline 管理
- ✅ **LLM Integration**：LLM 集成（OpenAI、Azure、Anthropic 等）
- ✅ **Model Metadata Management**：模型元数据管理
- ✅ **Query Generation**：自然语言查询生成

**技术栈**：
```python
langchain-core = "^0.1"
langchain-openai = "^0.0"
langchain-anthropic = "^0.1"
sqlglot = "^19.0"
fastapi = "^0.104"
```

**工作流程**：
```
用户自然语言
    ↓
Agent Pipeline (LangChain)
    ↓
1. Schema Understanding (理解语义层)
2. Intent Recognition (意图识别)
3. Query Generation (生成查询)
    ↓
Wren Engine (Rust)
    ↓
SQL Execution (DataFusion)
```

**对比 NL2MQL2SQL**：
| 模块 | NL2MQL2SQL | WrenAI | 说明 |
|------|-----------|---------|------|
| LLM 框架 | LangChain | LangChain | 相同 |
| 工作流 | LangGraph 7节点固定 | Pipeline-based 可配置 | NL2MQL2SQL 更简单直观 |
| 智能体 | 自研 Deep Agents | LangChain Agents | NL2MQL2SQL 更灵活 |

---

#### 6.2.3 MDL（Model Definition Language）

**文件位置**: `otherproj/WrenAI/wren-mdl/`

**MDL Schema**：
```json
{
  "$schema": "https://mdl.getwren.ai/mdl.json",
  "models": [
    {
      "name": "orders",
      "refSql": "SELECT * FROM raw_orders",
      "columns": [
        {
          "name": "order_id",
          "type": "integer",
          "notNull": true
        },
        {
          "name": "order_amount",
          "type": "decimal",
          "notNull": true
        }
      ]
    },
    {
      "name": "sales",
      "refSql": "SELECT * FROM raw_sales",
      "relationships": [
        {
          "name": "order",
          "models": ["orders"],
          "joinType": "inner",
          "condition": "sales.order_id = orders.order_id"
        }
      ]
    }
  ]
}
```

**核心特性**：
- ✅ **Models**：定义数据模型
- ✅ **Relationships**：定义模型关系（JOIN）
- ✅ **Metrics**：定义指标
- ✅ **Access Control**：行列级权限控制
- ✅ **Calculations**：计算字段

**对比 NL2MQL2SQL**：
| 特性 | NL2MQL2SQL | WrenAI | 说明 |
|------|-----------|---------|------|
| 语义层定义 | MQL V2 (自研) | MDL (标准) | WrenAI 标准化更好 |
| 关系定义 | Views (SQL) | Relationships (JSON) | WrenAI 更直观 |
| 权限控制 | 未实现 | Access Control | WrenAI 更完整 |
| 计算字段 | 指标定义 | Calculations | 功能相似 |

---

### 6.3 核心差异总结

| 维度 | NL2MQL2SQL | WrenAI | 优势方 |
|------|-----------|---------|--------|
| **架构复杂度** | 单容器架构 | 多服务架构 | NL2MQL2SQL（更简单） |
| **SQL 引擎** | sqlglot (Python) | Apache DataFusion (Rust) | WrenAI（性能更优） |
| **语义层** | MQL V2 (自研) | MDL (标准) | WrenAI（标准化） |
| **工作流** | 7节点固定 | Pipeline-based 可配置 | NL2MQL2SQL（更直观） |
| **技能系统** | 动态 Skills | 无 | NL2MQL2SQL（更灵活） |
| **数据源支持** | 2 个（MySQL、PostgreSQL） | 11+ 个 | WrenAI（更丰富） |
| **权限控制** | 未实现 | 行列级权限 | WrenAI（更完整） |
| **MCP 协议** | 未实现 | 支持 | WrenAI（更生态） |
| **部署难度** | 低 | 高 | NL2MQL2SQL（更简单） |

---

## 七、WrenAI 集成方案

### 7.1 方案 A: 直接调用 Wren Engine（推荐 ⭐⭐⭐⭐⭐）

**思路**: 保留 NL2MQL2SQL 的工作流和技能系统，将 MQL Engine V2 替换为 Wren Engine。

**架构**：
```
前端 (Vue 3)
    ↓
Deep Agents Manager (LangGraph 7节点)
    ↓
    ├─ analyze_intent (LLM) ← 保留
    ├─ retrieve_metadata (DB) ← 保留
    ├─ generate_mql (LLM) ← 保留
    ├─ validate_mql (jsonschema) ← 保留
    ├─ correct_mql (LLM) ← 保留
    ├─ translate_to_sql → Wren Engine (替换)
    └─ execute_query → Ibis (保留)
```

**实施步骤**：
1. ✅ 部署 Wren Engine（Docker）
2. ✅ 将 MDL 语义层定义迁移到 Wren Engine
3. ✅ 修改 `translate_to_sql` 工具，调用 Wren Engine API
4. ✅ 测试验证 SQL 生成质量

**优点**：
- ✅ 保留 NL2MQL2SQL 的工作流和技能系统
- ✅ 利用 Wren Engine 的高性能查询优化
- ✅ 渐进式改进，风险低
- ✅ 部署相对简单（仅需 Wren Engine 服务）

**缺点**：
- ⚠️ 需要额外部署 Wren Engine
- ⚠️ 需要维护两套语义层定义

**预期收益**：
- 查询性能提升 2-5 倍（DataFusion 优化）
- 支持 11+ 数据源
- SQL 生成质量提升（Wren Engine 优化器）

**实施周期**: 2-3 周

---

### 7.2 方案 B: 深度集成 Wren AI Service

**思路**: 完全替换 LLM 调用部分，使用 Wren AI Service 的 Agent Pipeline。

**架构**：
```
前端 (Vue 3)
    ↓
Wren AI Service (替换 Deep Agents Manager)
    ↓
Wren Engine (Rust + DataFusion)
    ↓
Ibis Server
```

**实施步骤**：
1. ✅ 部署 Wren AI Service（Python）
2. ✅ 部署 Wren Engine（Rust）
3. ✅ 迁移语义层到 MDL
4. ✅ 修改前端 API 调用
5. ✅ 移除 Deep Agents Manager 和 MQL Engine V2

**优点**：
- ✅ 利用 WrenAI 的完整能力
- ✅ 不需要维护 LLM 调用逻辑
- ✅ 企业级稳定性

**缺点**：
- ❌ 失去技能系统
- ❌ 失去工作流灵活性
- ❌ 部署复杂度高（多服务）
- ❌ 依赖 WrenAI 生态

**预期收益**：
- 查询性能提升 5-10 倍
- 减少 50% 代码维护量
- 企业级稳定性

**实施周期**: 4-6 周

---

### 7.3 方案 C: 参考 WrenAI 架构自研

**思路**: 参考 WrenAI 的架构，但保留 NL2MQL2SQL 的优势。

**架构**：
```
前端 (Vue 3)
    ↓
Deep Agents Manager (保留)
    ↓
MQL Engine V2 (升级)
    ├─ sqlglot (Python)
    └─ Apache DataFusion (Rust, 集成)
```

**实施步骤**：
1. ✅ 使用 Apache DataFusion Python 绑定
2. ✅ 增强 MQL Engine V2 的查询优化
3. ✅ 标准化 MQL Schema（参考 MDL）
4. ✅ 增加数据源支持

**优点**：
- ✅ 完全可控
- ✅ 保留工作流和技能系统
- ✅ 性能接近 WrenAI

**缺点**：
- ⚠️ 开发周期长
- ⚠️ 需要大量测试

**预期收益**：
- 查询性能提升 3-5 倍
- 支持 5+ 数据源
- 保留所有现有特性

**实施周期**: 8-12 周

---

### 7.4 方案对比

| 方案 | 性能提升 | 实施周期 | 风险 | 推荐度 |
|------|---------|---------|------|--------|
| **A: Wren Engine** | 2-5倍 | 2-3周 | 低 | ⭐⭐⭐⭐⭐ 强烈推荐 |
| **B: Wren AI Service** | 5-10倍 | 4-6周 | 中 | ⭐⭐⭐ 中等推荐 |
| **C: 自研** | 3-5倍 | 8-12周 | 高 | ⭐⭐ 低推荐 |

---

## 八、推荐集成路线图

### 阶段 1: 方案 A - Wren Engine 集成（2-3周）

**目标**: 替换 MQL Engine V2，提升查询性能

**任务**：
1. ✅ 部署 Wren Engine（Docker）
2. ✅ 迁移语义层到 MDL
3. ✅ 修改 `translate_to_sql` 工具
4. ✅ 测试验证

**预期收益**：
- 查询性能提升 2-5 倍
- 支持 11+ 数据源

---

### 阶段 2: 增强权限控制（1-2周）

**目标**: 参考 MDL 的 accessControl，实现行列级权限

**任务**：
1. ✅ 设计权限数据模型
2. ✅ 实现权限检查中间件
3. ✅ 集成到查询执行流程

**预期收益**：
- 支持行列级权限
- 满足企业级安全需求

---

### 阶段 3: MCP 协议支持（可选，2-3周）

**目标**: 实现 MCP Server，支持 Claude、Cursor 等 MCP 客户端

**任务**：
1. ✅ 研究 MCP 协议规范
2. ✅ 实现 MCP Server
3. ✅ 测试集成

**预期收益**：
- 可集成到 Claude、Cursor 等
- 扩展使用场景

---

## 九、预期收益

| 指标 | 当前 | 阶段 1 | 阶段 2 | 阶段 3 |
|------|------|--------|--------|--------|
| **查询性能** | 基准 | +200-500% | - | - |
| **数据源支持** | 2个 | 11+个 | 11+个 | 11+个 |
| **简单查询时间** | 3-5秒 | 1-2秒 (-60%) | 1-2秒 | 1-2秒 |
| **复杂查询时间** | 10-15秒 | 3-5秒 (-70%) | 3-5秒 | 3-5秒 |
| **权限控制** | 无 | 无 | 行列级权限 | 行列级权限 |
| **MCP 协议** | 不支持 | 不支持 | 不支持 | 支持 |

---

## 十、总结

### 改进方向

1. **短期**: 集成 Wren Engine，提升查询性能
2. **中期**: 增强权限控制，满足企业级需求
3. **长期**: 支持 MCP 协议，扩展使用场景

### 推荐方案

**优先推荐**: **方案 A - Wren Engine 集成**

**理由**：
- ✅ 渐进式改进，风险低
- ✅ 保留现有优势（工作流、技能系统）
- ✅ 预期收益高（2-5倍性能提升）
- ✅ 实施周期短（2-3周）

## 十一、MQL SQL语法限制与改进方案

### 11.1 当前MQL不支持的SQL语法

#### 限制1: CTE子查询不能嵌套CTE
**问题描述**:
- 当前实现中,CTE子查询不能再包含CTE定义
- 代码限制: `_build_without_cte` 方法用于构建CTE子查询,该方法不支持CTE嵌套

**不支持场景**:
```sql
WITH cte1 AS (
    WITH cte2 AS (SELECT ... FROM table)
    SELECT ... FROM cte2  -- ❌ 不支持CTE嵌套
)
SELECT ... FROM cte1
```

**改进方案**:
- 在`_build_without_cte`中增加CTE嵌套支持
- 允许CTE子查询包含自己的CTE定义
- 预期实施周期: 1-2周

---

#### 限制2: CTE作为数据源时主查询字段处理不完整
**问题描述**:
- 当使用`from_cte`时,主查询的`dimensions`和`metrics`应直接引用CTE已聚合的列
- 当前实现在`_build_metric_expression`中只是简单返回列名,无法正确处理所有CTE返回的列

**代码位置**: `ast_builder.py` 第460-461行
```python
if self._is_cte_source:
    return exp.column(metric_alias).as_(metric_alias)
```

**问题**:
- 只处理了指标,未处理维度
- 无法支持CTE返回的计算列或别名列
- CTE中的常量列(constants)无法被主查询引用

**改进方案**:
1. ✅ 在`SemanticContext`中增加CTE元数据存储
2. ✅ 当使用`from_cte`时,从CTE定义中提取列结构
3. ✅ 主查询的`dimensions`和`metrics`直接映射到CTE的列名,不再查找语义层
4. ✅ 在SELECT子句中支持CTE的常量列引用

**实施情况**:
- ✅ 已完成（2026-03-24）
- ✅ 采用方案A（SemanticContext）
- ✅ 在SemanticContext中添加CTE元数据存储方法
- ✅ 在ASTBuilder._build_with_cte中收集CTE列信息
- ✅ 修改_build_metric_expression支持CTE列引用
- ✅ 修改_build_dimension_expression支持CTE列引用
- ✅ 在_build_select_clause中支持CTE常量列引用

---

#### 限制3: UNION字段忽略机制未完全实现
**问题描述**:
- Prompt规则11说明:"当使用union字段时,与union同级的json字段会被完全忽略"
- 但代码中并未实现这个忽略逻辑

**代码位置**: `ast_builder.py` 第74-75行
```python
# === 构建（支持 UNION 和基础 SELECT，但不支持 CTE） ===
return self._build_without_cte(mql)
```

**问题**:
- 如果主查询MQL同时包含`union`和其他字段(dimensions、metrics等),这些字段可能会被错误处理
- 应该在检测到`union`时,忽略同级其他字段

**改进方案**:
1. ✅ 在`_build_without_cte`中增加字段忽略逻辑
2. ✅ 检测到`union`时,只处理`union`、`limit`、`queryResultType`等字段
3. ✅ 自动跳过其他字段校验

**实施情况**:
- ✅ 已完成（2026-03-24）
- ✅ 在_build_without_cte中添加UNION检测和字段过滤逻辑
- ✅ 创建_build_union_query_or_select辅助方法
- ✅ 当使用UNION时只处理允许的字段

---

#### 限制4: 不支持CTE之间的相互引用
**问题描述**:
- 虽然支持`from_cte`引用单个CTE或多个CTE的JOIN
- 但不支持CTE之间相互引用(CTE A引用CTE B)

**不支持场景**:
```sql
WITH cte_a AS (SELECT ... FROM table),
     cte_b AS (SELECT ... FROM cte_a)  -- ❌ 不支持CTE引用另一个CTE
SELECT * FROM cte_b
```

**改进方案**:
1. 修改`_build_with_cte`逻辑,允许CTE按依赖顺序构建
2. 增加CTE依赖分析,确定构建顺序
3. 在CTE子查询中也支持`from_cte`引用其他已定义的CTE
4. 预期实施周期: 2-3周

---

#### 限制5: 窗口函数不支持在CTE中使用
**问题描述**:
- 当前`_build_base_select`会构建窗口函数(第126-128行)
- CTE子查询使用`_build_without_cte`,后者调用`_build_base_select`
- 但CTE中使用窗口函数可能导致语义混乱(CTE已计算窗口函数,主查询又使用)

**代码位置**: `ast_builder.py` 第126-128行
```python
# 1.5 窗口函数（追加到 SELECT 子句）
window_expressions = self._build_window_function_expressions(mql)
```

**改进方案**:
1. 增加配置参数控制是否在CTE中构建窗口函数
2. 默认情况下CTE子查询禁用窗口函数
3. 如果需要在CTE中使用窗口函数,可通过明确配置启用
4. 预期实施周期: 1周

---

#### 限制6: 只支持UNION子查询,不支持通用子查询
**问题描述**:
- 当前只支持`union`字段定义的UNION子查询
- 不支持WHERE子句中的子查询、FROM子句中的子查询(CTE除外)

**不支持场景**:
```sql
-- WHERE子查询
SELECT * FROM orders WHERE amount > (SELECT AVG(amount) FROM orders)  -- ❌ 不支持

-- FROM子查询(非CTE)
SELECT * FROM (SELECT ... FROM table) AS sub  -- ❌ 不支持
```

**改进方案**:
1. 在MQL中增加`subquery`字段,支持在WHERE、FROM中使用子查询
2. 增加子查询语法解析能力
3. 实施难度高,建议优先级低
4. 预期实施周期: 4-6周

---

#### 限制7: 不支持CASE表达式
**问题描述**:
- 当前MQL不支持CASE WHEN THEN ELSE END语法
- 无法实现条件逻辑和计算列

**不支持场景**:
```sql
SELECT
    CASE
        WHEN amount > 1000 THEN '高'
        WHEN amount > 500 THEN '中'
        ELSE '低'
    END AS amount_level
FROM orders
```

**改进方案**:
1. 在`ExpressionParser`中增加CASE表达式解析
2. 在指标定义或维度定义中增加`caseWhen`字段
3. 示例:
```json
{
  "dimensions": ["amount_level"],
  "dimensionConfigs": {
    "amount_level": {
      "type": "case_when",
      "cases": [
        {"condition": "[amount] > 1000", "value": "高"},
        {"condition": "[amount] > 500", "value": "中"}
      ],
      "else": "低"
    }
  }
}
```
4. 预期实施周期: 2-3周

---

#### 限制8: 不支持复杂的聚合函数计算
**问题描述**:
- 当前只支持基础聚合函数(SUM、COUNT、AVG、MAX、MIN)
- 不支持标准差、方差、百分位等统计函数
- 不支持聚合函数的复杂计算(如SUM(A)/SUM(B))

**不支持场景**:
```sql
SELECT
    STDDEV(amount) AS std_amount,  -- ❌ 不支持标准差
    SUM(amount) / COUNT(*) AS avg_amount,  -- ❌ 不支持聚合函数计算
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount) AS median  -- ❌ 不支持百分位
FROM orders
```

**改进方案**:
1. 扩展`_get_agg_func`支持的聚合函数
2. 在`ExpressionParser`中支持聚合函数的复合表达式
3. 增加统计函数(STDDEV、VARIANCE、PERCENTILE等)
4. 预期实施周期: 2-3周

---

#### 限制9: 不支持INTERSECT和EXCEPT
**问题描述**:
- 当前只支持UNION和UNION ALL
- 不支持INTERSECT(交集)和EXCEPT(差集)

**不支持场景**:
```sql
-- 交集
SELECT id FROM orders_2024
INTERSECT
SELECT id FROM orders_2025  -- ❌ 不支持

-- 差集
SELECT id FROM orders_2024
EXCEPT
SELECT id FROM orders_2025  -- ❌ 不支持
```

**改进方案**:
1. 在`_build_without_cte`中增加INTERSECT和EXCEPT支持
2. MQL语法: `{"type": "INTERSECT"|"EXCEPT", "queries": [...]}`
3. 实施难度低,建议优先级中
4. 预期实施周期: 1-2周

---

#### 限制10: 不支持PIVOT和UNPIVOT
**问题描述**:
- 不支持行转列(PIVOT)和列转行(UNPIVOT)
- 无法实现数据透视和透视撤销

**不支持场景**:
```sql
-- 行转列
SELECT * FROM
(SELECT product, month, amount FROM sales)
PIVOT (SUM(amount) FOR month IN ('1月', '2月', '3月'))  -- ❌ 不支持

-- 列转行
SELECT * FROM sales
UNPIVOT (amount FOR month IN (amount_1, amount_2, amount_3))  -- ❌ 不支持
```

**改进方案**:
1. 实施复杂度高,建议优先级低
2. 可通过CTE+CASE WHEN模拟
3. 预期实施周期: 6-8周

---

#### 限制11: CTE/子查询不支持未定义View的原始表或自定义SQL
**问题描述**:
- 当前CTE子查询必须通过`fromView`引用已定义的View
- 无法直接查询数据库中未定义View的原始表
- 无法使用自定义SQL语句作为CTE数据源

**不支持场景**:
```sql
-- 查询原始表（未定义View）
WITH temp_sales AS (
    SELECT * FROM raw_sales  -- ❌ 不支持，raw_sales表没有对应的View
)
SELECT * FROM temp_sales

-- 自定义SQL
WITH temp_data AS (
    SELECT id, amount, DATE(created_at) AS date
    FROM orders
    WHERE amount > 100  -- ❌ 不支持自定义SQL
)
SELECT * FROM temp_data
```

**改进方案**:

**方案A: 在CTE定义中增加`rawSql`字段**
- MQL语法示例：
```json
{
  "cte": [
    {
      "name": "temp_sales",
      "rawSql": "SELECT * FROM raw_sales WHERE amount > 100"
    }
  ],
  "from_cte": "temp_sales",
  "dimensions": ["category"],
  "metrics": ["total_amount"]
}
```
- 优点：灵活性最高，支持任意SQL
- 缺点：失去语义层保护，SQL注入风险
- 实施周期：1-2周

**方案B: 在CTE定义中增加`rawTable`字段**
- MQL语法示例：
```json
{
  "cte": [
    {
      "name": "temp_sales",
      "rawTable": "raw_sales",
      "datasourceId": "mysql_prod",
      "dimensions": ["category", "date"],
      "metrics": ["total_amount"]
    }
  ],
  "from_cte": "temp_sales",
  "dimensions": ["category"],
  "metrics": ["total_amount"]
}
```
- 优点：相对安全，仍需定义字段
- 缺点：需要管理datasource_id，灵活性低于方案A
- 实施周期：1周

**方案C: 自动创建临时View**
- 当检测到CTE引用未定义的表时，自动创建临时View
- 优点：保持语义层一致性，用户无感知
- 缺点：实现复杂，可能导致View定义混乱
- 实施周期：2-3周

**推荐方案**: 方案A（rawSql）+ 安全检查
- 允许`rawSql`字段，但增加SQL安全检查（只读权限、语法验证）
- 实施周期：1-2周
---

### 11.2 优先级排序与实施路线图

| 限制 | 优先级 | 影响范围 | 实施周期 | 推荐顺序 | 状态 |
|------|--------|----------|----------|----------|------|
| 限制1: CTE嵌套 | P1 | 中 | 1-2周 | 2 | 待实施 |
| 限制2: CTE字段处理 | P0 | 高 | 1-2周 | 1 | ✅ 已完成 |
| 限制3: UNION字段忽略 | P1 | 中 | 1周 | 3 | ✅ 已完成 |
| 限制4: CTE相互引用 | P1 | 中 | 2-3周 | 4 | 待实施 |
| 限制5: CTE窗口函数 | P2 | 低 | 1周 | 5 | 待实施 |
| 限制6: 通用子查询 | P3 | 低 | 4-6周 | 9 | 待实施 |
| 限制7: CASE表达式 | P1 | 高 | 2-3周 | 6 | 待实施 |
| 限制8: 复杂聚合函数 | P2 | 中 | 2-3周 | 7 | 待实施 |
| 限制9: INTERSECT/EXCEPT | P2 | 中 | 1-2周 | 8 | 待实施 |
| 限制10: PIVOT/UNPIVOT | P3 | 低 | 6-8周 | 10 | 待实施 |
| 限制11: 原始表/自定义SQL | P1 | 高 | 1-2周 | 5.5 | 待实施 |

---

### 11.3 快速改进计划(2-4周)

#### Week 1-2: P0问题修复
- ✅ 修复限制2: CTE作为数据源时的字段处理（方案A：SemanticContext）
  - ✅ 在SemanticContext中增加CTE元数据存储
    - `_cte_columns`: {cte_name: [column_names]}
    - `_cte_metrics`: {cte_name: {metric_names}}
    - `_cte_dimensions`: {cte_name: {dimension_names}}
    - `_cte_constants`: {cte_name: [constants]}
    - 新增方法：`register_cte_columns()`, `is_cte_column()`, `get_cte_constants()`
  - ✅ 在ASTBuilder._build_with_cte中收集CTE列信息
    - 修复bug：初始化`cte_nodes = []`
  - ✅ 修改_build_metric_expression支持CTE列引用
    - 优先检查CTE列，直接返回列引用（无需metricDefinitions）
    - 实现方案A：CTE场景下不需要metricDefinitions
  - ✅ 修改_build_dimension_expression支持CTE列引用
    - CTE列：直接返回列引用
  - ✅ 在_build_select_clause中支持CTE常量列引用
  - ✅ 修复_build_base_select调用顺序问题
    - CTE场景：提前设置`_used_view`（在`_build_select_clause`之前）
  - ✅ 修改_build_cte_from设置`_used_view`
  - ✅ 修改MQLCompositeValidator支持from_cte
    - from_cte场景：跳过MetricValidator和DimensionValidator

- ✅ 修复限制3: UNION字段忽略机制
  - ✅ 在MQLCompositeValidator中集中处理UNION逻辑
    - 检测到UNION时只处理：{union, limit, queryResultType, cte}
    - 跳过其他字段的验证
  - ✅ 修改UnionValidator支持递归验证
    - 验证union.queries中的子MQL
  - ✅ 修改CTEValidator支持递归验证
    - 验证cte[].query中的子MQL
  - ✅ 修复导入路径为相对导入

#### Week 2-3: P1问题修复
- 修复限制1: CTE嵌套支持
- 实现限制7: CASE表达式
- 修复限制11: 原始表/自定义SQL支持（方案A：rawSql）

#### Week 3-4: P1问题继续
- 修复限制4: CTE相互引用

---

## 十二、总结

### 改进方向

1. **短期(2-4周)**: 修复P0和P1问题,提升CTE和UNION的完整性
2. **中期(4-8周)**: 扩展SQL语法支持(CASE、复杂聚合、INTERSECT等)
3. **长期(8周+)**: 实现高级SQL特性(通用子查询、PIVOT等)

### 推荐方案

**优先推荐**: **按优先级逐步修复SQL语法限制**

**理由**:
- ✅ 渐进式改进,风险可控
- ✅ 每个问题都有明确的改进方案
- ✅ 预期收益明显,用户体验提升显著
- ✅ 实施周期短,快速见效

---

**文档版本**: v4.1 (限制2、3已修复版)
**最后更新**: 2026-03-24
**作者**: NL2MQL2SQL Team
