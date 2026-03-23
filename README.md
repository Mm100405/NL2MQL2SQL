# NL2MQL2SQL - 智能问数系统

基于 LangChain、LangGraph 和 Deep Agents 的企业级自然语言查询系统。

## 🎯 核心特性

- **自然语言查询**：用日常语言提问，系统自动转换为数据库查询（Text-to-SQL）
- **多模型支持**：支持 OpenAI、Ollama、Azure、Claude、DeepSeek 等多种 LLM
- **语义层管理**：可视化配置数据源、指标、维度、视图
- **流式输出**：实时展示查询步骤和结果，提升用户体验
- **动态技能系统**：运行时加载、卸载外部技能，支持 Code Skills 和 Markdown Skills 双轨架构
- **企业级架构**：基于 LangGraph + Deep Agents 的智能体架构，7节点工作流
- **MQL 引擎 V2**：基于 sqlglot AST 的语义层查询引擎，支持 11 个 MQL 字段

## 🏗️ 技术架构

### 前端技术栈
- **Vue 3** - 渐进式 JavaScript 框架（Composition API）
- **Vite** - 下一代前端构建工具
- **Arco Design** - 企业级 UI 组件库
- **TypeScript** - 类型安全的 JavaScript
- **Pinia** - Vue 3 状态管理
- **Vue Router** - 路由管理

### 后端技术栈
- **FastAPI** - 现代化 Python Web 框架（异步支持）
- **SQLAlchemy** - Python ORM 工具
- **LangChain** - LLM 应用开发框架（LLM Client、Tools、Messages）
- **LangGraph** - 有状态智能体编排（StateGraph、astream、MemorySaver）
- **Deep Agents** - 企业级智能体系统（自定义实现，基于 LangGraph）

### MQL 引擎技术栈
- **sqlglot** - SQL 解析器和转换器（AST 构建）
- **Apache DataFusion** - 数据查询引擎（参考 WrenAI）
- **AST Builder** - MQL 到 SQL 的转换管线

### AI 智能体架构

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                    │
│  - /api/v1/query/stream  (SSE 流式查询)                  │
│  - /api/v1/skills/*      (技能管理)                     │
│  - /api/v1/agent/*        (智能体监控)                   │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│             Agent Layer (Deep Agents Manager)             │
│  - LLM Router (智能路由)                                 │
│  - Skill Loader (动态技能加载)                            │
│  - Execution Engine (流式执行 - LangGraph astream)          │
│  - Checkpointer (MemorySaver - 对话记忆)                   │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Skills Layer (双轨 Skill 系统)               │
│  ├─ Code Skills (核心技能，Python 实现)                  │
│  │  ├─ analyze_intent (意图分析)                       │
│  │  ├─ retrieve_metadata (元数据检索)                  │
│  │  ├─ generate_mql (MQL 生成)                       │
│  │  ├─ validate_mql (MQL 验证)                       │
│  │  ├─ correct_mql (MQL 修正)                       │
│  │  ├─ translate_to_sql (SQL 转换)                    │
│  │  ├─ execute_query (查询执行)                        │
│  │  └─ analyze_result (结果分析)                       │
│  └─ Markdown Skills (外部技能，Markdown 定义)           │
│     ├─ web-search (网络搜索)                             │
│     ├─ code-analyzer (代码分析)                         │
│     └─ ... (自定义技能)                                  │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Semantic Layer (语义层服务)                │
│  - nl_parser.py (NL → MQL)                              │
│  - mql_engine.py (MQL → SQL, 基于 sqlglot AST)           │
│  - mql_translator/ (MQL V2 引擎)                        │
│  │  ├─ semantic.py (语义层解析)                         │
│  │  ├─ ast_builder.py (AST 构建)                         │
│  │  ├─ optimizer.py (查询优化)                          │
│  │  └─ dialect.py (方言转换)                           │
│  - query_executor.py (执行查询)                          │
│  - llm_client.py (LLM 调用，支持流式)                   │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│               Data Layer (数据存储)                      │
│  - MySQL/PostgreSQL (业务数据)                           │
│  - Model Config (模型配置)                               │
│  - View/Dataset (语义层定义)                             │
└─────────────────────────────────────────────────────────┘
```

### 智能体架构

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                    │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│             Agent Layer (Deep Agents Manager)             │
│  - LLM Router (智能路由)                                 │
│  - Skill Loader (动态技能加载)                            │
│  - Execution Engine (流式执行)                            │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Skills Layer (双轨 Skill 系统)               │
│  ├─ Code Skills (核心技能，Python 实现)                  │
│  │  ├─ intent_analysis (意图分析)                       │
│  │  ├─ metadata_retrieval (元数据检索)                  │
│  │  ├─ mql_generation (MQL 生成)                        │
│  │  ├─ mql_validation (MQL 验证)                        │
│  │  ├─ mql_correction (MQL 修正)                        │
│  │  ├─ sql_translation (SQL 转换)                       │
│  │  ├─ query_execution (查询执行)                       │
│  │  └─ result_analysis (结果分析)                       │
│  └─ Markdown Skills (外部技能，Markdown 定义)           │
│     ├─ web-search (网络搜索)                             │
│     ├─ code-analyzer (代码分析)                         │
│     └─ ... (自定义技能)                                  │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              Semantic Layer (语义层服务)                │
│  - nl_parser.py (NL → MQL)                              │
│  - mql_engine.py (MQL → SQL)                             │
│  - query_executor.py (执行查询)                          │
│  - llm_client.py (LLM 调用)                              │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│               Data Layer (数据存储)                      │
│  - MySQL/PostgreSQL (业务数据)                           │
│  - Model Config (模型配置)                               │
│  - View/Dataset (语义层定义)                             │
└─────────────────────────────────────────────────────────┘
```

## 📦 项目结构

```
NL2MQL2SQL/
├── backend/                 # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── agents/          # 智能体层 (LangGraph + Deep Agents)
│   │   │   ├── deep_agents/    # Deep Agents 核心
│   │   │   │   ├── manager.py       # Deep Agents 管理器
│   │   │   │   ├── enhanced_manager.py  # 增强版管理器（支持 Skills）
│   │   │   │   ├── config.py        # Deep Agents 配置
│   │   │   │   ├── state.py         # 状态定义 (DeepAgentState)
│   │   │   │   ├── tools.py         # 8 个核心工具
│   │   │   │   └── workflow.py      # LangGraph 7节点工作流
│   │   │   ├── skills/          # Skills 定义
│   │   │   │   ├── code_skills/    # 代码技能（废弃，迁移到 tools.py）
│   │   │   │   └── markdown_skills/ # Markdown 技能
│   │   │   ├── external_skills/  # 外部标准 Skills
│   │   │   │   ├── web_search/    # 网络搜索技能
│   │   │   │   └── code_analyzer/ # 代码分析技能
│   │   │   └── mql_agent.py     # 传统 MQL 智能体（废弃）
│   │   ├── api/            # API 层
│   │   │   └── v1/
│   │   │       ├── query.py     # 查询 API (SSE 流式输出)
│   │   │       ├── skills.py    # 技能管理 API
│   │   │       ├── agent.py     # 智能体监控 API
│   │   │       └── ...
│   │   ├── models/         # 数据模型 (SQLAlchemy)
│   │   │   ├── metric.py        # 指标模型
│   │   │   ├── dimension.py     # 维度模型
│   │   │   ├── dataset.py       # 数据集模型
│   │   │   ├── view.py         # 视图模型
│   │   │   └── datasource.py   # 数据源模型
│   │   ├── services/       # 业务服务
│   │   │   ├── llm_client.py       # LLM 客户端（多模型支持）
│   │   │   ├── nl_parser.py        # 自然语言解析 (NL → MQL)
│   │   │   ├── mql_engine.py      # MQL 引擎 V1
│   │   │   ├── mql_translator/    # MQL 引擎 V2（基于 sqlglot）
│   │   │   │   ├── semantic.py     # 语义层解析
│   │   │   │   ├── ast_builder.py  # AST 构建
│   │   │   │   ├── optimizer.py    # 查询优化
│   │   │   │   └── dialect.py     # 方言转换
│   │   │   └── query_executor.py  # 查询执行
│   │   ├── utils/          # 工具函数
│   │   ├── config.py       # 全局配置
│   │   ├── database.py     # 数据库连接
│   │   └── main.py        # FastAPI 应用入口
│   └── requirements.txt
│
├── frontend/                # 前端应用 (Vue 3 + Vite)
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   │   ├── layout/     # 布局组件
│   │   │   ├── query/      # 智能问数页面
│   │   │   ├── semantic/   # 语义层管理
│   │   │   └── settings/   # 系统设置
│   │   ├── api/            # API 封装
│   │   ├── stores/         # Pinia 状态管理
│   │   └── router/         # Vue Router 路由配置
│   └── package.json
│
├── otherproj/              # 参考项目
│   └── WrenAI/           # WrenAI（GenBI Agent）
│       ├── wren-engine/    # 语义引擎 (Rust + Apache DataFusion)
│       ├── wren-ai-service/ # AI 服务 (Python + LangChain)
│       └── wren-mdl/      # MDL (模型定义语言) schema
│
├── README.md              # 项目主文档（总体架构和部署）
├── ARCHITECTURE_SUMMARY.md  # 详细架构说明
└── IMPROVEMENTS.md       # 改进方向与方案
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **Node.js**: 18+
- **数据库**: MySQL 8.0+ 或 PostgreSQL 12+

### 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动服务
npm run dev
```

### 访问地址

- **前端应用**: http://localhost:5173
- **后端 API 文档**: http://localhost:8011/docs
- **智能问数**: http://localhost:5173/#/query

## 🚀 部署方案

### 本地开发部署

**快速启动**（推荐）：
```bash
# 1. 启动后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload

# 2. 启动前端（新终端）
cd frontend
npm install
npm run dev
```

**访问地址**：
- 前端应用：http://localhost:5173
- 后端 API 文档：http://localhost:8011/docs
- 智能问数：http://localhost:5173/#/query

---

### Docker 部署

**单容器部署**：
```bash
# 构建镜像
docker build -t nl2mql2sql:latest .

# 运行容器
docker run -d \
  -p 8011:8011 \
  -p 5173:5173 \
  -e DATABASE_URL=mysql+pymysql://user:pass@host:3306/db \
  nl2mql2sql:latest
```

**Docker Compose 部署**：
```yaml
version: '3.8'
services:
  nl2mql2sql:
    image: nl2mql2sql:latest
    ports:
      - "8011:8011"  # 后端 API
      - "5173:5173"  # 前端 UI
    environment:
      - DATABASE_URL=mysql+pymysql://root:password@db:3306/nl2mql2sql
      - LLM_PROVIDER=openai
      - LLM_MODEL=gpt-4-turbo
      - LLM_API_KEY=sk-...
    depends_on:
      - db

  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=nl2mql2sql
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

启动：
```bash
docker-compose up -d
```

---

### K8s 部署

参考 `deployments/k8s/` 目录下的配置文件。

---

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接字符串 | - |
| `LLM_PROVIDER` | LLM 提供商 | openai |
| `LLM_MODEL` | LLM 模型名称 | gpt-4-turbo |
| `LLM_API_KEY` | LLM API Key | - |
| `LLM_API_BASE` | LLM API 端点 | https://api.openai.com/v1 |
| `LLM_TEMPERATURE` | LLM 温度参数 | 0.2 |
| `LLM_MAX_TOKENS` | LLM 最大 Token | 4096 |
| `REDIS_URL` | Redis 连接字符串（可选，用于缓存） | - |

---

## 🔍 故障排查

### 常见问题

**1. 后端启动失败**
```bash
# 检查端口占用
netstat -ano | findstr :8011

# 检查依赖安装
pip list | findstr langchain
```

**2. 前端连接失败**
```bash
# 检查后端是否启动
curl http://localhost:8011/health

# 检查 CORS 配置
```

**3. LLM 调用失败**
```bash
# 检查 API Key
echo $LLM_API_KEY

# 测试 API 连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"
```

**4. 数据库连接失败**
```bash
# 测试数据库连接
mysql -h localhost -u root -p

# 检查 DATABASE_URL 配置
echo $DATABASE_URL
```

---

## 📈 性能优化

### 后端优化

**1. 并发优化**
- 启用并行执行独立工具（预期收益 30-40%）
- 使用异步 I/O（asyncio）

**2. 缓存优化**
- Redis 缓存查询结果（预期收益 <100ms 响应）
- LLM 响应缓存（预期收益 50% 成本降低）

**3. 数据库优化**
- 添加索引（预期收益 50% 查询加速）
- 使用连接池

### 前端优化

**1. 加载优化**
- 代码分割
- 懒加载

**2. 渲染优化**
- 虚拟滚动
- 防抖节流

---

## 🔧 开发指南

### 后端开发

**添加新工具**：
```python
from langchain_core.tools import tool

@tool
async def my_tool(param: str) -> Dict[str, Any]:
    """工具描述"""
    # 实现逻辑
    return {"result": param}
```

**添加新技能**：
1. 创建 Markdown Skill
2. 使用 API 加载：
```bash
curl -X POST http://localhost:8011/api/v1/skills/load/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/skill.md"}'
```

### 前端开发

**添加新页面**：
```bash
cd frontend
npm run dev
```

**组件开发**：
- 使用 Vue 3 Composition API
- 遵循 Arco Design 规范
- 使用 Pinia 状态管理

---

## 🧪 测试

### 后端测试

```bash
cd backend
pytest tests/ -v
```

### 前端测试

```bash
cd frontend
npm run test
```

---

## 📚 核心文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE_SUMMARY.md](./ARCHITECTURE_SUMMARY.md) | 详细架构说明（LangChain/LangGraph/Deep Agents 使用情况、7节点工作流、MQL Engine V2） |
| [IMPROVEMENTS.md](./IMPROVEMENTS.md) | 改进方向与方案（自主决策机制分析、WrenAI 集成分析、对比与建议） |

---

## 🔗 外部资源

### 参考项目

| 项目 | 说明 | 链接 |
|------|------|------|
| **WrenAI** | GenBI Agent（Apache DataFusion + MDL） | https://github.com/Canner/WrenAI |
| **LangChain** | LLM 应用开发框架 | https://docs.langchain.com/ |
| **LangGraph** | 有状态智能体编排 | https://docs.langchain.com/oss/python/langgraph |
| **sqlglot** | SQL 解析器和转换器 | https://github.com/tobymao/sqlglot |
| **Apache DataFusion** | 数据查询引擎（Rust） | https://arrow.apache.org/datafusion/ |

### 社区资源

- LangChain 中文社区：https://python.langchain.com/docs/get_started/introduction
- WrenAI 文档：https://docs.getwren.ai
- WrenAI Discord：https://discord.gg/5DvshJqG8Z

---

## 🤝 贡献指南

欢迎贡献代码！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 👥 联系方式

- 项目主页：https://github.com/your-org/NL2MQL2SQL
- 问题反馈：https://github.com/your-org/NL2MQL2SQL/issues
- 邮箱：contact@nl2mql2sql.com

---

**文档版本**: v2.0
**最后更新**: 2026-03-23
**作者**: NL2MQL2SQL Team

## 🎨 功能模块

### 智能问数
- 自然语言查询转换
- 实时流式输出
- 查询步骤可视化
- 结果格式化展示

### 语义层管理
- 数据源管理
- 视图设计器
- 指标管理
- 维度管理
- 字典管理

### 技能管理
- 核心技能展示
- 外部技能加载
- 技能启用/禁用
- 技能卸载

### 系统设置
- 模型配置
- 智能体状态监控
- 用户信息管理

## 🔧 配置说明

### 模型配置

在"系统设置 → 模型配置"页面配置：

- **LLM 模型**: 选择 OpenAI、Ollama、Azure 或 Claude
- **API Key**: 输入对应平台的 API Key
- **基础 URL**: 自定义 API 端点（可选）
- **温度**: 控制生成随机性（0-1）
- **超时时间**: 单次查询超时（秒）

### 数据源配置

在"语义层管理 → 数据源管理"页面添加数据源：

- 支持 MySQL、PostgreSQL
- 配置连接信息并测试
- 数据源用于语义层视图定义

## 📖 使用示例

### 示例 1：基础查询

**用户提问**：
```
查询最近7天的销售额
```

**系统流程**：
```
1. 意图分析：识别指标为"销售额"，时间范围为"最近7天"
   ↓
2. 元数据检索：获取"销售额"指标定义和相关视图
   ↓
3. MQL 生成：生成 MQL 查询语句
   ↓
4. MQL 验证：验证 MQL 语法正确性
   ↓
5. SQL 转换：将 MQL 转换为可执行的 SQL
   ↓
6. 查询执行：执行 SQL 查询
   ↓
7. 结果分析：格式化展示查询结果
```

**生成的 MQL**：
```json
{
    "metrics": ["sales_amount"],
    "timeConstraint": {
        "operator": "BETWEEN",
        "start": "LAST_N_DAYS(7)",
        "end": "TODAY()"
    }
}
```

**生成的 SQL**：
```sql
SELECT SUM(order_amount) AS sales_amount
FROM orders
WHERE order_date BETWEEN DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND CURDATE()
```

---

### 示例 2：多维度查询

**用户提问**：
```
按地区、渠道查询2025年的订单数量
```

**系统流程**：
1. 意图分析：识别指标为"订单数量"，维度为"地区"、"渠道"，时间范围为"2025年"
2. 元数据检索：获取相关视图和字段信息
3. MQL 生成：生成分组查询的 MQL
4. 执行并返回：返回按地区、渠道分组的订单数量

**生成的 MQL**：
```json
{
    "metrics": [{"name": "order_count", "expression": "COUNT(*)"}],
    "dimensions": ["region", "channel"],
    "timeConstraint": {
        "operator": "BETWEEN",
        "start": "DATE_FORMAT('2025-01-01', '%Y-%m-%d')",
        "end": "DATE_FORMAT('2025-12-31', '%Y-%m-%d')"
    },
    "groupBy": ["region", "channel"]
}
```

---

### 示例 3：复杂过滤查询

**用户提问**：
```
查询线上渠道、订单状态为完成的订单金额
```

**系统流程**：
1. 意图分析：识别指标为"订单金额"，过滤条件为"渠道=线上"、"状态=完成"
2. 元数据检索：获取字段可选值（如"线上"、"完成"）
3. MQL 生成：生成带过滤条件的 MQL
4. 执行并返回：返回符合条件的订单金额

**生成的 MQL**：
```json
{
    "metrics": [{"name": "total_amount", "expression": "SUM(order_amount)"}],
    "filters": [
        {
            "column": "channel",
            "operator": "EQUALS",
            "value": "线上"
        },
        {
            "column": "order_status",
            "operator": "EQUALS",
            "value": "完成"
        }
    ]
}
```

---

### 示例 4：高级查询（排序、限制）

**用户提问**：
```
查询销售额最高的10个产品
```

**生成的 MQL**：
```json
{
    "metrics": [{"name": "sales", "expression": "SUM(sales_amount)"}],
    "dimensions": ["product_name"],
    "orderBy": [
        {
            "column": "sales",
            "direction": "DESC"
        }
    ],
    "limit": 10
}
```

---

### 示例 5：窗口函数查询

**用户提问**：
```
查询每月销售额及其同比增长率
```

**生成的 MQL**：
```json
{
    "metrics": [
        {"name": "monthly_sales", "expression": "SUM(order_amount)"},
        {
            "name": "yoy_growth",
            "expression": "SUM(order_amount) / LAG(SUM(order_amount), 12) - 1"
        }
    ],
    "dimensions": ["month"],
    "timeConstraint": {
        "operator": "BETWEEN",
        "start": "LAST_N_MONTHS(24)",
        "end": "TODAY()"
    },
    "windowFunctions": [
        {
            "function": "LAG",
            "column": "order_amount",
            "offset": 12,
            "partitionBy": [],
            "orderBy": ["month"]
        }
    ]
}
```

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](./LICENSE) 文件。

## 📞 联系方式

如有问题或建议，请提交 Issue 或联系维护者。

---

**Built with ❤️ using LangChain, LangGraph, and Deep Agents**
