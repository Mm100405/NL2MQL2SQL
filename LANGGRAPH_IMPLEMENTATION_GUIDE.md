# LangGraph 智能体实施指南

## 快速开始

### 1. 安装依赖

```bash
pip install langgraph langchain langchain-core
```

### 2. 创建基础目录

```bash
cd backend/app
mkdir -p agents/nodes agents/workflows agents/state
touch agents/__init__.py agents/nodes/__init__.py agents/workflows/__init__.py agents/state/__init__.py
```

### 3. 逐步实施

#### 步骤 1: 创建状态定义
```bash
# 创建 backend/app/agents/state/query_state.py
# 复制方案文档中的 QueryState 定义
```

#### 步骤 2: 创建基础节点类
```bash
# 创建 backend/app/agents/nodes/base_node.py
# 复制方案文档中的 BaseNode 定义
```

#### 步骤 3: 创建各个节点（按顺序）
1. metadata_retrieval.py
2. intent_analysis.py
3. mql_generation.py
4. mql_validation.py
5. mql_correction.py
6. sql_translation.py
7. query_execution.py
8. result_interpretation.py

#### 步骤 4: 创建工作流
```bash
# 创建 backend/app/agents/workflows/mql_query_workflow.py
# 复制方案文档中的工作流定义
```

#### 步骤 5: 创建智能体主类
```bash
# 创建 backend/app/agents/mql_agent.py
# 复制方案文档中的 MQLAgent 定义
```

#### 步骤 6: 创建 API 接口
```bash
# 创建 backend/app/api/v1/agent.py
# 复制方案文档中的 API 接口定义
```

#### 步骤 7: 注册路由
```python
# 在 backend/app/main.py 中添加
from app.api.v1 import agent

app.include_router(agent.router, prefix="/api/v1/agent", tags=["智能体查询"])
```

## 测试指南

### 1. 单元测试（节点级别）

```python
# tests/test_nodes/test_metadata_retrieval.py

import pytest
from app.agents.nodes.metadata_retrieval import MetadataRetrievalNode
from app.agents.state.query_state import QueryState
from app.database import SessionLocal

def test_metadata_retrieval_node():
    db = SessionLocal()
    node = MetadataRetrievalNode(db)
    
    initial_state: QueryState = {
        "natural_language": "查询销售额",
        "context": {},
        "messages": []
    }
    
    result = await node(initial_state, {})
    
    assert "metadata" in result
    assert "suggested_metrics" in result
    assert len(result["steps"]) > 0
```

### 2. 集成测试（工作流级别）

```python
# tests/test_workflows/test_mql_query_workflow.py

import pytest
from app.agents.mql_agent import MQLAgent
from app.database import SessionLocal

@pytest.mark.asyncio
async def test_mql_query_workflow():
    db = SessionLocal()
    agent = MQLAgent(db)
    
    result = await agent.execute_query(
        natural_language="2025年4月线上渠道的销售额"
    )
    
    assert "mql" in result
    assert "sql" in result
    assert "result" in result
    assert result["steps"][-1]["status"] == "success"
```

### 3. API 测试

```bash
curl -X POST "http://localhost:8000/api/v1/agent/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "natural_language": "2025年4月线上渠道的销售额"
  }'
```

## 验证清单

### 功能验证

- [ ] 元数据检索正确
- [ ] 意图分析合理
- [ ] MQL 生成符合规范
- [ ] MQL 验证准确
- [ ] MQL 修正有效
- [ ] SQL 转换正确
- [ ] 查询执行成功
- [ ] 结果解释有价值

### 性能验证

- [ ] 单次查询响应时间 < 5 秒
- [ ] 并发支持正常
- [ ] 内存占用合理

### 兼容性验证

- [ ] 与现有 API 并存
- [ ] 数据格式一致
- [ ] 错误处理兼容

## 常见问题

### Q1: 节点间如何传递数据？

A: 通过 `QueryState` 对象。每个节点接收完整状态，返回需要更新的字段。

```python
async def __call__(self, state: QueryState, config: Dict) -> Dict[str, Any]:
    # 读取状态
    metadata = state.get("metadata", {})
    
    # 处理逻辑...
    
    # 返回更新的状态（只需要返回变化的字段）
    return {
        "new_field": value
    }
```

### Q2: 如何实现条件路由？

A: 使用 `add_conditional_edges`：

```python
def should_retry(state: QueryState) -> str:
    if state.get("should_retry_mql"):
        return "correction_node"
    else:
        return "next_node"

workflow.add_conditional_edges(
    "validation_node",
    should_retry,
    {
        "correction_node": "correction_node",
        "next_node": "next_node"
    }
)
```

### Q3: 如何添加新的节点？

A: 1. 继承 BaseNode；2. 实现 __call__ 方法；3. 在工作流中注册。

```python
# 1. 创建节点
class MyCustomNode(BaseNode):
    node_name = "custom_node"
    
    async def __call__(self, state, config):
        # 实现逻辑
        return {"custom_field": "value"}

# 2. 注册到工作流
workflow.add_node("custom_node", my_custom_node)
workflow.add_edge("prev_node", "custom_node")
```

### Q4: 如何调试工作流？

A: 使用 LangGraph 的可视化工具：

```python
from IPython.display import Image, display

# 生成工作流图
display(Image(workflow.get_graph().draw_mermaid_png()))
```

### Q5: 如何处理 LLM 错误？

A: 在节点中添加异常处理：

```python
try:
    response = await call_llm(...)
    result = parse_response(response)
except Exception as e:
    self.add_step(state, "LLM 调用", f"LLM 调用失败: {str(e)}", "error")
    raise
```

## 性能优化建议

### 1. 缓存元数据

```python
from functools import lru_cache

class MetadataRetrievalNode(BaseNode):
    @lru_cache(maxsize=100)
    def _retrieve_metrics(self, query_hash: str, context_hash: str):
        # 缓存元数据检索结果
        pass
```

### 2. 并行执行

```python
# 可以并行执行的节点（如元数据检索 + 意图分析）
workflow.add_edge("metadata_retrieval", "sql_translation")
workflow.add_edge("intent_analysis", "sql_translation")
```

### 3. 异步优化

确保所有 I/O 操作都是异步的：

```python
# 使用异步数据库驱动
from sqlalchemy.ext.asyncio import AsyncSession

# 使用异步 HTTP 客户端
import httpx
```

## 监控和日志

### 1. 添加结构化日志

```python
import logging

logger = logging.getLogger(__name__)

class MQLGenerationNode(BaseNode):
    async def __call__(self, state, config):
        start_time = time.time()
        
        # 执行逻辑...
        
        execution_time = time.time() - start_time
        logger.info(f"MQL generation completed in {execution_time:.2f}s")
```

### 2. 添加指标收集

```python
from prometheus_client import Counter, Histogram

mql_generation_counter = Counter('mql_generation_total', 'Total MQL generations')
mql_generation_duration = Histogram('mql_generation_duration_seconds', 'MQL generation duration')

class MQLGenerationNode(BaseNode):
    async def __call__(self, state, config):
        mql_generation_counter.inc()
        
        with mql_generation_duration.time():
            # 执行逻辑...
            pass
```

## 迁移策略

### 阶段 1: 双系统并行（2周）

1. 保留原有 `/api/v1/query/nl2result` 接口
2. 新增 `/api/v1/agent/execute` 接口
3. 对比两个接口的输出
4. 收集性能数据

### 阶段 2: 灰度发布（2周）

1. 使用 A/B 测试，将 10% 流量切换到智能体接口
2. 监控错误率和性能
3. 逐步增加到 50%

### 阶段 3: 完全迁移（1周）

1. 将所有流量切换到智能体接口
2. 保留原接口作为回退
3. 观察 1-2 周后下线原接口

## 团队培训

### 培训内容

1. LangGraph 基础概念
2. 节点开发指南
3. 工作流设计模式
4. 调试和测试技巧
5. 性能优化方法

### 学习资源

- LangGraph 官方文档: https://langchain-ai.github.io/langgraph/
- LangChain 文档: https://python.langchain.com/
- 示例项目: https://github.com/langchain-ai/langgraph/tree/main/examples

## 联系支持

如有问题，请查看：
- LangGraph GitHub Issues
- 社区论坛
- 内部技术文档
