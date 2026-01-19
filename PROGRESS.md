# NL2MQL2SQL 开发进度表

## 项目信息
- **项目名称**: NL2MQL2SQL 智能问数系统
- **开始时间**: 2026-01-18
- **技术栈**: Vue 3 + Vite + Arco Design | FastAPI + SQLAlchemy

---

## 第一阶段：核心功能

### Step 1: 项目初始化
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 创建前端项目（Vue 3 + Vite） | 已完成 | 2026-01-18 | 含Arco Design、Pinia、Vue Router |
| 创建后端项目（FastAPI） | 已完成 | 2026-01-18 | 含SQLAlchemy、Pydantic |
| 配置数据库连接 | 已完成 | 2026-01-18 | SQLite |
| 搭建主布局框架 | 已完成 | 2026-01-18 | 侧边栏导航、路由配置 |

### Step 2: 数据模型与基础CRUD
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 创建ORM模型 | 已完成 | 2026-01-18 | DataSource, Dataset, Metric, Dimension, ModelConfig等 |
| 数据库迁移 | 已完成 | 2026-01-18 | 自动创建表 |
| 实现数据源CRUD | 已完成 | 2026-01-18 | - |
| 实现数据集CRUD | 已完成 | 2026-01-18 | - |
| 实现模型配置CRUD | 已完成 | 2026-01-18 | - |

### Step 3: 模型配置管理
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 后端：模型配置API | 已完成 | 2026-01-18 | - |
| 后端：API Key加密存储 | 已完成 | 2026-01-18 | Fernet加密 |
| 后端：模型连接测试接口 | 已完成 | 2026-01-18 | 支持OpenAI/Ollama/Azure |
| 前端：模型配置页面 | 已完成 | 2026-01-18 | - |
| 前端：模型配置状态检查 | 已完成 | 2026-01-18 | Pinia store |

### Step 4: 语义层管理
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 指标管理（三种类型） | 已完成 | 2026-01-18 | 基础/派生/复合指标 |
| 维度管理 | 已完成 | 2026-01-18 | - |
| 关联关系管理 | 已完成 | 2026-01-18 | - |
| 元数据校验 | 已完成 | 2026-01-18 | 基础校验 |

### Step 5: MQL引擎
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| MQL语法解析 | 已完成 | 2026-01-18 | 正则解析 |
| MQL→SQL转换器 | 已完成 | 2026-01-18 | - |
| 多数据库方言适配 | 已完成 | 2026-01-18 | SQLite/PostgreSQL/MySQL |

### Step 6: NL理解与集成
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| LLM客户端集成 | 已完成 | 2026-01-18 | 支持OpenAI/Ollama/Azure/Custom |
| 意图识别服务 | 已完成 | 2026-01-18 | Few-shot Prompt |
| 实体消歧服务 | 已完成 | 2026-01-18 | 基础实现 |

### Step 7: 智能问数页面
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 问数主页面 | 已完成 | 2026-01-18 | - |
| 模型未配置提醒组件 | 已完成 | 2026-01-18 | - |
| 结果可视化 | 已完成 | 2026-01-18 | ECharts |
| 下钻与归因分析 | 已完成 | 2026-01-18 | 框架搭建，待完善 |

---

## 第二阶段：高级功能

### AIR模块
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 工作簿 | 已完成 | 2026-01-18 | 工作流管理界面 |
| 数据集成 | 已完成 | 2026-01-18 | ETL任务管理 |
| 数据整合 | 已完成 | 2026-01-18 | 数据合并/清洗/转换 |
| 数据加速 | 已完成 | 2026-01-18 | 物化视图/OLAP Cube/缓存 |

### CAN模块
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 指标目录 | 已完成 | 2026-01-18 | 指标分类树/搜索/筛选 |
| 指标应用 | 已完成 | 2026-01-18 | 仪表盘/报表/API服务 |
| 指标加速 | 已完成 | 2026-01-18 | 指标预计算加速 |
| 管理设置 | 已完成 | 2026-01-18 | 权限/通知/审计/集成 |

### BIG模块
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 算子级数据血缘 | 已完成 | 2026-01-18 | SQL算子级血缘可视化 |

---

## 第三阶段：前后端对接

### 后端API开发
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 创建AIR模块数据模型 | 已完成 | 2026-01-19 | Workbook/IntegrationTask/ConsolidationRule/DataAcceleration |
| 创建CAN模块数据模型 | 已完成 | 2026-01-19 | MetricCatalog/Application/Acceleration/Role/AuditLog |
| 创建BIG模块数据模型 | 已完成 | 2026-01-19 | LineageNode/LineageConnection/SQLAnalysis |
| 实现AIR模块API | 已完成 | 2026-01-19 | 15+ API端点 |
| 实现CAN模块API | 已完成 | 2026-01-19 | 12+ API端点 |
| 实现BIG模块API | 已完成 | 2026-01-19 | 8+ API端点 |
| 注册路由到主应用 | 已完成 | 2026-01-19 | - |

### 前端API调用
| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| 创建AIR模块API封装 | 已完成 | 2026-01-19 | frontend/src/api/air.ts |
| 创建CAN模块API封装 | 已完成 | 2026-01-19 | frontend/src/api/can.ts |
| 创建BIG模块API封装 | 已完成 | 2026-01-19 | frontend/src/api/big.ts |
| 前端构建验证 | 已完成 | 2026-01-19 | TypeScript编译通过 |

---

## 启动说明

### 后端启动
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 访问地址
- 前端: http://localhost:5173
- 后端API文档: http://localhost:8010/docs

---

## 变更记录

| 日期 | 变更内容 | 负责人 |
|------|----------|--------|
| 2026-01-18 | 项目启动，创建进度表 | - |
| 2026-01-18 | 完成前后端项目初始化 | - |
| 2026-01-18 | 完成语义层管理和智能问数核心功能 | - |
| 2026-01-18 | 修复导航菜单展开问题 | - |
| 2026-01-18 | 完成AIR模块前端页面（工作簿/数据集成/数据整合/数据加速） | - |
| 2026-01-18 | 完成CAN模块前端页面（指标目录/指标应用/指标加速/管理设置） | - |
| 2026-01-18 | 完成BIG模块前端页面（算子级数据血缘） | - |
| 2026-01-19 | 完成AIR/CAN/BIG模块后端数据模型和API | - |
| 2026-01-19 | 完成前端API调用封装，实现前后端完整对接 | - |

## API接口清单

### AIR模块 API (15个)
- `POST /api/v1/air/workbooks` - 创建工作簿
- `GET /api/v1/air/workbooks` - 获取工作簿列表
- `DELETE /api/v1/air/workbooks/{id}` - 删除工作簿
- `POST /api/v1/air/integration-tasks` - 创建集成任务
- `GET /api/v1/air/integration-tasks` - 获取集成任务列表
- `PUT /api/v1/air/integration-tasks/{id}/toggle` - 切换任务状态
- `POST /api/v1/air/consolidation-rules` - 创建整合规则
- `GET /api/v1/air/consolidation-rules` - 获取整合规则列表
- `POST /api/v1/air/accelerations` - 创建数据加速配置
- `GET /api/v1/air/accelerations` - 获取数据加速配置列表
- `PUT /api/v1/air/accelerations/{id}/toggle` - 切换加速状态

### CAN模块 API (13个)
- `POST /api/v1/can/catalogs` - 创建指标
- `GET /api/v1/can/catalogs` - 获取指标列表
- `PUT /api/v1/can/catalogs/{id}/publish` - 发布指标
- `PUT /api/v1/can/catalogs/{id}/deprecate` - 废弃指标
- `POST /api/v1/can/applications` - 创建指标应用
- `GET /api/v1/can/applications` - 获取指标应用列表
- `POST /api/v1/can/accelerations` - 创建指标加速配置
- `GET /api/v1/can/accelerations` - 获取指标加速配置列表
- `PUT /api/v1/can/accelerations/{id}/toggle` - 切换指标加速状态
- `POST /api/v1/can/roles` - 创建角色
- `GET /api/v1/can/roles` - 获取角色列表
- `GET /api/v1/can/audit-logs` - 获取审计日志
- `POST /api/v1/can/audit-logs` - 创建审计日志

### BIG模块 API (8个)
- `POST /api/v1/big/lineage-nodes` - 创建血缘节点
- `GET /api/v1/big/lineage-nodes` - 获取血缘节点列表
- `GET /api/v1/big/lineage-nodes/{id}` - 获取血缘节点详情
- `POST /api/v1/big/lineage-connections` - 创建血缘连接
- `GET /api/v1/big/lineage-connections` - 获取血缘连接列表
- `POST /api/v1/big/sql-analysis` - 分析SQL血缘
- `GET /api/v1/big/sql-analysis` - 获取SQL分析历史
- `GET /api/v1/big/lineage-graph/{target}` - 获取血缘图谱

