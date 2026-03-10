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
| 配置数据库连接 | 已完成 | 2026-01-18 | MYSQL |
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
| 多数据库方言适配 | 已完成 | 2026-01-18 | PostgreSQL/MySQL |

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
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
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

---

## 第四阶段：功能完善

### 功能点 1：MQL Filters 生成增强（优先）

#### 背景
当前问题：自然语言中的过滤条件不能正确映射到 MQL 的 `filters` 字段。

#### 核心问题分析
1. **Prompt 不明确**：`nl_parser.py` 中对 filters 的说明过于简单
2. **时间/非时间过滤混淆**：LLM 可能将非时间条件放入 `timeConstraint`
3. **缺少字段值提示**：LLM 不知道字段的可选值
4. **MQLValidator 未验证 filters**：缺少对 filters 字段的校验

#### 方案要点

##### 1. 数据模型增强

###### 1.1 View.columns 字段结构扩展
```python
[{
    # 基础字段
    "name": "channel",
    "source_table": "t0",
    "source_column": "channel_code",
    "type": "VARCHAR(50)",
    
    # 展示信息（可编辑）
    "display_name": "销售渠道",
    "description": "订单来源渠道",
    "default_comment": "渠道编码",  # 默认值：物理表注释
    "synonyms": ["渠道", "来源"],
    
    # 值域配置
    "value_config": {
        "type": "dict",  # none | enum | range | dict | sql
        
        # enum 类型
        "enum_values": ["ONLINE", "OFFLINE"],
        
        # range 类型
        "range": {"min": 0, "max": 100, "step": 1},
        
        # dict 类型
        "dict_id": "dictionary_uuid",
        
        # sql 类型
        "sql_expression": "SELECT DISTINCT channel FROM orders",
        "value_column": "channel",
        "label_column": "channel_name"
    },
    
    # 过滤配置
    "filterable": true,
    "filter_operators": ["=", "IN", "NOT IN", "LIKE"]
}]
```

###### 1.2 FieldDictionary 字典模型（已存在，需扩展使用）
- `source_type`: manual / view_ref / auto
- `mappings`: 手动配置的值映射
- `ref_view_id`: 引用视图
- `auto_source_dataset_id`: 自动生成

##### 2. API 新增/修改

###### 2.1 字典管理 API（新增 `backend/app/api/v1/dictionary.py`）
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/dictionaries` | GET | 获取字典列表 |
| `/api/v1/dictionaries` | POST | 创建字典 |
| `/api/v1/dictionaries/{id}` | PUT | 更新字典 |
| `/api/v1/dictionaries/{id}/values` | GET | 获取字典可选值 |
| `/api/v1/dictionaries/{id}/sync` | POST | 同步自动字典 |

###### 2.2 视图字段管理 API（修改 `backend/app/api/v1/views.py`）
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/views/{id}/filterable-fields` | GET | 获取可过滤字段列表 |
| `/api/v1/views/{id}/columns` | PUT | 更新字段配置 |
| `/api/v1/views/{id}/columns/sync-from-source` | POST | 从物理表同步字段元数据 |

##### 3. NL Parser 增强

###### 3.1 Prompt 模板修改
```python
NL_TO_MQL_PROMPT = """
...
⚠️ filters 使用规则：
1. 字段名用 [中括号] 包裹，使用「展示名」或「逻辑名」
2. 字符串值用单引号 '值'
3. 从下方「可过滤字段」列表中选择字段
4. 值必须从字段的可选值中选择（如果有）

可过滤字段（视图/表的所有可过滤字段）：
{filterable_fields}

示例：
用户："线上渠道已完成的订单金额"
→ filters: ["[渠道] = '线上'", "[订单状态] = '完成'"]
"""
```

###### 3.2 新增函数
```python
def build_filterable_fields_prompt(view_id: str, db: Session) -> str:
    """构建可过滤字段的 Prompt，包含可选值"""
```

##### 4. MQLValidator 增强

###### 4.1 新增 filters 验证方法
```python
def validate_filters(self, filters: List[str], db: Session) -> Tuple[bool, str]:
    """验证 filters 字段"""
    # 1. 检查字段引用格式 [field]
    # 2. 验证字段是否存在
    # 3. 检查操作符是否合法
    # 4. 验证值是否在可选值范围内
```

##### 5. 前端适配

###### 5.1 视图字段配置组件（新增）
- 字段展示名编辑
- 字段说明编辑
- 值域配置（枚举/范围/字典/SQL）
- 过滤开关

###### 5.2 字典管理页面（新增）
- 手动配置字典
- 引用视图字典
- 自动生成字典

#### 实施计划

| 阶段 | 内容 | 文件 | 优先级 | 状态 |
|------|------|------|--------|------|
| **Phase 1** | 字典管理 API | 增强 `dictionaries.py` | P0 | ✅ 已完成 |
| **Phase 2** | 视图字段管理 API | `views.py` 增强 | P0 | ✅ 已完成 |
| **Phase 3** | NL Parser Prompt 增强 | `nl_parser.py` | P0 | ✅ 已完成 |
| **Phase 4** | MQLValidator filters 验证 | `mql_validator.py` | P1 | ✅ 已完成 |
| **Phase 5** | 前端字段配置界面 | 整合到 `ViewDesigner.vue` 的字段列表Tab | P1 | ✅ 已完成 |
| **Phase 6** | 前端字典管理界面 | 新增 `DictionaryManage.vue` | P2 | ✅ 已完成 |

#### 关键代码位置

| 功能 | 文件路径 |
|------|----------|
| NL 解析 Prompt | `backend/app/services/nl_parser.py:14-127` |
| MQL 验证器 | `backend/app/utils/mql_validator.py` |
| 视图模型 | `backend/app/models/view.py` |
| 字典模型 | `backend/app/models/field_dict.py` |
| 视图 API | `backend/app/api/v1/views.py` |
| 字典 API | `backend/app/api/v1/dictionaries.py` |

---

### 功能点 2：多视图指标处理（低优先级）

#### 背景
当用户查询涉及跨视图/跨数据源的指标时，需要自动拆分为多个独立查询。

#### 核心约束
- **维度限定**：只能选择该视图/数据集已定义的维度
- **字段限定**：只能选择该视图/数据集的可过滤字段
- **结果分离**：各视图独立返回结果，无公共维度关联

#### 分步生成流程
```
Step 1: 指标识别 → LLM 先识别用户问题中的指标
Step 2: 视图分组 → 按指标所属视图分组
Step 3: 分组生成 → 每组只提供该视图的可用维度/字段，分别生成 MQL
Step 4: 并行执行 → 多个查询并行执行
Step 5: 返回多结果 → 前端分 Tab 展示各视图结果
```

#### 新增服务（待开发）

##### 1. 指标识别服务（`backend/app/services/metric_selector.py`）
- 从自然语言中识别指标意图
- 返回指标列表 + 原始意图

##### 2. 视图分组服务（`backend/app/services/view_grouper.py`）
- 按指标所属视图/数据源分组
- 确定每个分组的可用维度和字段

#### 实施计划

| 阶段 | 内容 | 文件 | 工作量 | 状态 |
|------|------|------|--------|------|
| Phase 1 | 指标识别服务 | 新增 `metric_selector.py` | 1天 | 待开发 |
| Phase 2 | 视图分组服务 | 新增 `view_grouper.py` | 1天 | 待开发 |
| Phase 3 | NL Parser 重构 | `nl_parser.py` | 2天 | 待开发 |
| Phase 4 | 查询入口改造 | `query.py` | 1天 | 待开发 |
| Phase 5 | 前端多结果展示 | `MultiSourceResult.vue` | 1天 | 待开发 |

---

## 待办事项

- [x] **P0** 完成 MQL filters 生成的 Prompt 增强
- [x] **P0** 完成字典管理 API 开发
- [x] **P0** 完成视图字段管理 API 开发
- [x] **P1** 完成 MQLValidator filters 验证
- [x] **P1** 完成前端字段配置界面
- [x] **P2** 完成前端字典管理界面
- [ ] **低优** 多视图指标处理功能

