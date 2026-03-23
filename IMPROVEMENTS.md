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

---

**文档版本**: v3.0 (增强版)
**最后更新**: 2026-03-23
**作者**: NL2MQL2SQL Team
