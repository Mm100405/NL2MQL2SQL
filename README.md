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

## 📦 项目结构

```
NL2MQL2SQL/
├── backend/                 # 后端服务 (FastAPI)
│   ├── app/
│   │   ├── agents/          # 智能体层 (LangGraph + Deep Agents)
│   │   ├── api/            # API 层
│   │   ├── models/         # 数据模型 (SQLAlchemy)
│   │   ├── services/       # 业务服务
│   │   ├── utils/          # 工具函数
│   │   ├── config.py       # 全局配置
│   │   ├── database.py     # 数据库连接
│   │   └── main.py        # FastAPI 应用入口
│   ├── Dockerfile         # 后端 Docker 镜像
│   └── requirements.txt
│
├── frontend/                # 前端应用 (Vue 3 + Vite)
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── api/            # API 封装
│   │   ├── stores/         # Pinia 状态管理
│   │   └── router/         # Vue Router 路由配置
│   ├── Dockerfile        # 前端 Docker 镜像
│   └── package.json
│
├── docker-compose.yml          # Docker Compose 编排（生产环境）
├── docker-compose.dev.yml      # Docker Compose 编排（开发环境）
├── .env.docker               # Docker 环境变量模板
│
├── start.bat                 # Windows 一键启动脚本
├── start.sh                 # Linux/Mac 一键启动脚本
├── docker-start.bat          # Windows Docker 启动脚本
├── docker-start.sh           # Linux/Mac Docker 启动脚本
│
├── DEPLOYMENT.md            # 📘 统一部署完整指南
├── ARCHITECTURE_SUMMARY.md   # 详细架构说明
└── IMPROVEMENTS.md         # 改进方向与方案
```

## 🚀 部署方式

### 📦 方案一：Docker 部署（推荐）

**特点**：一键启动、环境隔离、易于管理

**适用场景**：
- 快速体验和新手上手
- 开发环境（支持代码热重载）
- 生产环境（优化镜像、Nginx 代理）

**快速启动**：
```bash
# Windows
docker-start.bat

# Linux/Mac
chmod +x docker-start.sh && ./docker-start.sh
```

**访问地址**：
- **开发环境**：http://localhost:5173（前端）、http://localhost:8011（后端）
- **生产环境**：http://localhost（前端）、http://localhost:8011（后端）

**详细文档**：📘 **[DEPLOYMENT.md](./DEPLOYMENT.md)** - 完整部署指南

---

### 💻 方案二：本地部署

**特点**：无需 Docker、快速启动、灵活配置

**适用场景**：
- 本机开发
- 快速测试
- 无 Docker 环境

**快速启动**：
```bash
# Windows
start.bat

# Linux/Mac
chmod +x start.sh && ./start.sh
```

**访问地址**：
- 前端：http://localhost:5173
- 后端：http://localhost:8011
- API 文档：http://localhost:8011/docs

**详细文档**：📘 **[DEPLOYMENT.md](./DEPLOYMENT.md)** - 完整部署指南

---

## 🌐 内网访问

所有部署方案都支持内网其他电脑访问：

### 获取本机 IP

```bash
# Windows
get-ip.bat

# Linux/Mac
./get-ip.sh
```

### 内网访问地址

假设你的本机 IP 是 `192.168.1.100`，其他电脑可以通过以下地址访问：

| 部署方式 | 前端应用 | 后端 API | API 文档 |
|----------|----------|----------|----------|
| Docker 开发 | http://192.168.1.100:5173 | http://192.168.1.100:8011 | http://192.168.1.100:8011/docs |
| Docker 生产 | http://192.168.1.100 | http://192.168.1.100:8011 | http://192.168.1.100:8011/docs |
| 本地部署 | http://192.168.1.100:5173 | http://192.168.1.100:8011 | http://192.168.1.100:8011/docs |

**重要特性**：
- ✅ 前端使用相对路径调用 API，自动适配任何访问域名
- ✅ 后端自动添加当前内网 IP 到 CORS 允许列表
- ✅ 无需修改配置，任何内网环境都能正常工作

---

## 📚 核心文档

| 文档 | 说明 |
|------|------|
| **[DEPLOYMENT.md](./DEPLOYMENT.md)** | 📘 统一部署完整指南（Docker + 本地部署） |
| [ARCHITECTURE_SUMMARY.md](./ARCHITECTURE_SUMMARY.md) | 详细架构说明（LangChain/LangGraph/Deep Agents 使用情况） |
| [IMPROVEMENTS.md](./IMPROVEMENTS.md) | 改进方向与方案 |

---

## 🔗 外部资源

### 参考项目

| 项目 | 说明 | 链接 |
|------|------|------|
| **WrenAI** | GenBI Agent（Apache DataFusion + MDL） | https://github.com/Canner/WrenAI |
| **LangChain** | LLM 应用开发框架 | https://docs.langchain.com/ |
| **LangGraph** | 有状态智能体编排 | https://docs.langchain.com/oss/python/langgraph |
| **sqlglot** | SQL 解析器和转换器 | https://github.com/tobymao/sqlglot |

### 社区资源

- LangChain 中文社区：https://python.langchain.com/docs/get_started/introduction
- WrenAI 文档：https://docs.getwren.ai
- WrenAI Discord：https://discord.gg/5DvshJqG8Z

---

## 🤝 贡献指南

欢迎贡献代码！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证。

---

**Built with ❤️ using LangChain, LangGraph, and Deep Agents**

**文档版本**: v3.0
**最后更新**: 2026-03-24
