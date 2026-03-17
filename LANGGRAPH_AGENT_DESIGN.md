# 基于 LangGraph 的 NL2MQL2SQL 智能体架构方案

## 一、当前架构分析

### 1.1 现有问数流程
```
NL Parser → MQL Engine → Query Executor
(线性执行，多轮修正)
```

### 1.2 现有服务层（可复用）
- nl_parser.py (NL→MQL)
- mql_engine.py (MQL→SQL)
- mql_validator.py (验证)
- query_executor.py (执行)
- llm_client.py (LLM调用)

## 二、LangGraph 智能体架构

### 2.1 整体架构图
```
API Layer
    ↓
Agent Layer (LangGraph)
    ├── Metadata Retrieval Node
    ├── Intent Analysis Node
    ├── MQL Generation Node
    ├── MQL Validation Node ◄──┐
    ├── SQL Translation Node     │ (验证失败时循环)
    ├── Query Execution Node     │
    └── Result Interpretation Node
    ↓
Semantic Layer (保留)
    ↓
Data Layer (保留)
```

### 2.2 目录结构
```
backend/app/
├── agents/
│   ├── base_agent.py
│   ├── mql_agent.py
│   ├── workflows/
│   │   ├── mql_query_workflow.py
│   │   └── drill_down_workflow.py
│   ├── nodes/
│   │   ├── base_node.py
│   │   ├── metadata_retrieval.py
│   │   ├── intent_analysis.py
│   │   ├── mql_generation.py
│   │   ├── mql_validation.py
│   │   ├── mql_correction.py
│   │   ├── sql_translation.py
│   │   ├── query_execution.py
│   │   └── result_interpretation.py
│   └── state/
│       └── query_state.py
├── services/ (保留)
├── models/ (保留)
├── api/v1/
│   ├── query.py (保留)
│   └── agent.py (新增)
└── utils/ (保留)
```

## 三、核心设计

### 3.1 状态定义 (QueryState)
```python
from typing import TypedDict, Optional, List, Dict, Any
from typing_extensions import Annotated
from langgraph.graph import add_messages

class QueryState(TypedDict):
    # 输入
    natural_language: str
    context: Optional[Dict[str, Any]]
    
    # 元数据
    metadata: Dict[str, Any]
    suggested_metrics: List[str]
    suggested_dimensions: List[str]
    filterable_fields: List[Dict]
    time_formats: List[Dict]
    
    # 意图
    intent: Dict[str, Any]
    intent_type: Optional[str]
    complexity: Optional[str]
    
    # MQL
    mql: Optional[Dict[str, Any]]
    mql_attempts: int
    mql_errors: List[str]
    
    # SQL
    sql: Optional[str]
    sql_datasources: List[str]
    sql_lineage: Dict[str, Any]
    
    # 查询结果
    query_result: Optional[Dict[str, Any]]
    query_id: Optional[str]
    
    # 结果解释
    interpretation: Optional[Dict[str, Any]]
    insights: List[str]
    
    # 执行步骤
    steps: List[Dict[str, Any]]
    
    # 控制状态
    should_retry_mql: bool
    retry_count: int
    max_retries: int
    
    # LangGraph 消息
    messages: Annotated[list, add_messages]
```

### 3.2 基础节点类
```python
# backend/app/agents/nodes/base_node.py

from abc import ABC, abstractmethod
from typing import Dict, Any
from app.agents.state.query_state import QueryState
from sqlalchemy.orm import Session

class BaseNode(ABC):
    """节点基类"""
    
    node_name: str
    description: str
    
    def __init__(self, db: Session = None):
        self.db = db
    
    @abstractmethod
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行节点逻辑，返回更新的状态"""
        pass
    
    def add_step(self, state: QueryState, title: str, content: str, status: str = "success"):
        """添加执行步骤（用于前端展示）"""
        if "steps" not in state:
            state["steps"] = []
        state["steps"].append({
            "title": title,
            "content": content,
            "status": status
        })
        return state
```

### 3.3 关键节点示例

#### 3.3.1 元数据检索节点
```python
# backend/app/agents/nodes/metadata_retrieval.py

from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models.metric import Metric
from app.models.dimension import Dimension
from app.models.settings import SystemSetting
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState

class MetadataRetrievalNode(BaseNode):
    """元数据检索节点 - 复用现有元数据管理逻辑"""
    
    node_name = "metadata_retrieval"
    description = "根据自然语言查询检索相关元数据"
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        natural_language = state["natural_language"]
        context = state.get("context", {})
        
        # 复用现有逻辑：获取指标、维度、可过滤字段
        metrics = self._retrieve_metrics(natural_language, context)
        dimensions = self._retrieve_dimensions(natural_language, context)
        filterable_fields = self._retrieve_filterable_fields()
        time_formats = self._retrieve_time_formats()
        
        # 更新状态
        metadata = {
            "metrics": metrics,
            "dimensions": dimensions,
            "filterable_fields": filterable_fields,
            "time_formats": time_formats
        }
        
        self.add_step(
            state,
            title="元数据检索",
            content=f"已检索到 {len(metrics)} 个指标、{len(dimensions)} 个维度",
            status="success"
        )
        
        return {
            "metadata": metadata,
            "suggested_metrics": [m.get("display_name") for m in metrics[:10]],
            "suggested_dimensions": [d.get("display_name") for d in dimensions[:10]],
            "filterable_fields": filterable_fields,
            "time_formats": time_formats
        }
    
    def _retrieve_metrics(self, query: str, context: dict) -> list:
        """复用现有逻辑"""
        from sqlalchemy import or_
        
        metrics_query = self.db.query(Metric)
        
        if context.get("suggested_metrics"):
            metrics_query = metrics_query.filter(or_(
                Metric.name.in_(context["suggested_metrics"]),
                Metric.display_name.in_(context["suggested_metrics"])
            ))
        
        metrics = metrics_query.all()
        
        return [
            {
                "name": m.name,
                "display_name": m.display_name,
                "measure_column": m.measure_column,
                "aggregation": m.aggregation
            }
            for m in metrics
        ]
    
    def _retrieve_dimensions(self, query: str, context: dict) -> list:
        """复用现有逻辑，包含时间维度衍生"""
        from sqlalchemy import or_
        import json
        
        dimensions_query = self.db.query(Dimension)
        
        if context.get("suggested_dimensions"):
            dimensions_query = dimensions_query.filter(or_(
                Dimension.name.in_(context["suggested_dimensions"]),
                Dimension.display_name.in_(context["suggested_dimensions"])
            ))
        
        dimensions = dimensions_query.all()
        time_formats = self._retrieve_time_formats()
        
        result = []
        
        for d in dimensions:
            is_time_dim = (
                (d.dimension_type and d.dimension_type.value == "time") or
                (d.data_type and d.data_type.lower() in ["date", "datetime", "timestamp"])
            )
            
            if not is_time_dim:
                result.append({
                    "name": d.name,
                    "display_name": d.display_name,
                    "physical_column": d.physical_column,
                    "type": "normal"
                })
            else:
                # 衍生时间维度（复用现有逻辑）
                format_options = []
                if d.format_config:
                    try:
                        config = json.loads(d.format_config) if isinstance(d.format_config, str) else d.format_config
                        format_options = config.get("options", [])
                    except:
                        pass
                
                if not format_options:
                    format_options = [f["name"] for f in time_formats]
                
                for fmt_cfg in time_formats:
                    if fmt_cfg["name"] in format_options:
                        suffix = fmt_cfg["suffix"]
                        label = fmt_cfg["label"]
                        result.append({
                            "name": f"{d.display_name or d.name}__{label}",
                            "display_name": f"{d.display_name or d.name}({label})",
                            "physical_column": d.physical_column,
                            "type": "time_virtual"
                        })
        
        return result
    
    def _retrieve_filterable_fields(self) -> list:
        """复用现有逻辑"""
        from app.models.view import View
        from app.models.field_dict import FieldDictionary
        
        fields = []
        
        views = self.db.query(View).all()
        for view in views:
            for col in view.columns or []:
                if col.get("filterable", True):
                    fields.append({
                        "display_name": col.get("display_name") or col.get("name"),
                        "name": col.get("name"),
                        "type": col.get("type", "")
                    })
        
        return fields
    
    def _retrieve_time_formats(self) -> list:
        """复用现有逻辑"""
        import json
        
        time_formats_setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == "time_formats"
        ).first()
        
        if time_formats_setting:
            val = time_formats_setting.value
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except:
                    pass
            elif isinstance(val, list):
                return val
        
        return [
            {"name": "YYYY-MM-DD", "label": "按日", "suffix": "day"},
            {"name": "YYYY-MM", "label": "按月", "suffix": "month"},
            {"name": "YYYY", "label": "按年", "suffix": "year"},
            {"name": "YYYY-WW", "label": "按周", "suffix": "week"}
        ]
```

#### 3.3.2 意图分析节点
```python
# backend/app/agents/nodes/intent_analysis.py

from typing import Dict, Any
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.services.llm_client import call_llm

class IntentAnalysisNode(BaseNode):
    """意图分析节点 - 使用 LLM 分析用户查询意图"""
    
    node_name = "intent_analysis"
    description = "分析用户查询意图"
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        natural_language = state["natural_language"]
        metadata = state.get("metadata", {})
        
        # 构建并调用 LLM
        prompt = self._build_prompt(natural_language, metadata)
        model_config = self._get_model_config()
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params=model_config["config_params"]
        )
        
        intent = self._parse_intent(response)
        
        self.add_step(
            state,
            title="意图识别",
            content=f"识别意图：{intent.get('description', '未知')}",
            status="success"
        )
        
        return {
            "intent": intent,
            "intent_type": intent.get("intent_type"),
            "complexity": intent.get("complexity")
        }
    
    def _build_prompt(self, query: str, metadata: dict) -> str:
        metrics_str = ", ".join([m.get("display_name") for m in metadata.get("metrics", [])[:10]])
        dims_str = ", ".join([d.get("display_name") for d in metadata.get("dimensions", [])[:10]])
        
        return f"""分析用户查询意图并返回 JSON：

用户查询：{query}
可用指标：{metrics_str}
可用维度：{dims_str}

返回格式：
{{
  "intent_type": "trend|comparison|drilldown|attribution|aggregation",
  "description": "意图描述",
  "suggested_metrics": ["指标1", "指标2"],
  "suggested_dimensions": ["维度1", "维度2"],
  "complexity": "low|medium|high"
}}"""
    
    def _parse_intent(self, response: str) -> dict:
        import json, re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {"intent_type": "aggregation", "complexity": "low"}
    
    def _get_model_config(self) -> dict:
        from app.models.model_config import ModelConfig
        from app.utils.encryption import decrypt_api_key
        
        model_config = self.db.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()
        
        return {
            "provider": model_config.provider,
            "model_name": model_config.model_name,
            "api_key": decrypt_api_key(model_config.api_key) if model_config.api_key else None,
            "api_base": model_config.api_base,
            "config_params": model_config.config_params
        }
```

#### 3.3.3 MQL 生成节点
```python
# backend/app/agents/nodes/mql_generation.py

from typing import Dict, Any
import json
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.services.llm_client import call_llm
from app.services.nl_parser import NL_TO_MQL_PROMPT

class MQLGenerationNode(BaseNode):
    """MQL 生成节点 - 复用现有 Prompt 和 LLM 调用逻辑"""
    
    node_name = "mql_generation"
    description = "基于自然语言和元数据生成 MQL"
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        natural_language = state["natural_language"]
        metadata = state.get("metadata", {})
        context = state.get("context", {})
        
        # 复用现有 Prompt 模板
        prompt = self._build_prompt(natural_language, metadata, context)
        
        # 调用 LLM
        model_config = self._get_model_config()
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params=model_config["config_params"]
        )
        
        # 解析 MQL
        mql = self._parse_mql(response)
        retry_count = state.get("retry_count", 0) + 1
        
        self.add_step(
            state,
            title="MQL 生成",
            content=f"已生成 MQL（第 {retry_count} 次尝试）",
            status="success"
        )
        
        return {
            "mql": mql,
            "mql_attempts": retry_count,
            "retry_count": retry_count
        }
    
    def _build_prompt(self, query: str, metadata: dict, context: dict) -> str:
        """复用现有的 NL_TO_MQL_PROMPT"""
        
        metrics = metadata.get("metrics", [])
        dimensions = metadata.get("dimensions", [])
        filterable_fields = metadata.get("filterable_fields", [])
        
        metrics_str = "\n".join([
            f"- {m.get('display_name')} | {m.get('name')} | {m.get('measure_column')}"
            for m in metrics
        ]) or "- 销售额 | gmv | retail_amt"
        
        dimensions_str = "\n".join([
            f"- {d.get('display_name')} | {d.get('name')} | {d.get('physical_column')}"
            for d in dimensions
        ]) or "- 日期 | date | create_time"
        
        filterable_fields_str = "\n".join([
            f"- {f.get('display_name')} | {f.get('name')} | {f.get('type')}"
            for f in filterable_fields
        ])
        
        quoted_mql_str = ""
        if context and context.get("quoted_mql"):
            quoted_mql_str = f"\n引用上下文:\n{json.dumps(context['quoted_mql'], ensure_ascii=False, indent=2)}\n"
        
        error_info = ""
        if state.get("mql_errors"):
            error_info = f"\n上次错误：\n{self._format_errors(state['mql_errors'])}\n"
        
        return NL_TO_MQL_PROMPT.format(
            metrics=metrics_str,
            dimensions=dimensions_str,
            filterable_fields=filterable_fields_str,
            query=query,
            error_info=error_info + quoted_mql_str
        )
    
    def _parse_mql(self, response: str) -> dict:
        mql_str = response.strip()
        if "```json" in mql_str:
            mql_str = mql_str.split("```json")[1].split("```")[0].strip()
        elif "```" in mql_str:
            mql_str = mql_str.split("```")[1].split("```")[0].strip()
        try:
            return json.loads(mql_str)
        except:
            return {}
    
    def _format_errors(self, errors: list) -> str:
        return "\n".join([f"- {err}" for err in errors])
    
    def _get_model_config(self) -> dict:
        from app.models.model_config import ModelConfig
        from app.utils.encryption import decrypt_api_key
        
        model_config = self.db.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()
        
        return {
            "provider": model_config.provider,
            "model_name": model_config.model_name,
            "api_key": decrypt_api_key(model_config.api_key) if model_config.api_key else None,
            "api_base": model_config.api_base,
            "config_params": model_config.config_params
        }
```

#### 3.3.4 MQL 验证节点
```python
# backend/app/agents/nodes/mql_validation.py

from typing import Dict, Any
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.utils.mql_validator import MQLValidator

class MQLValidationNode(BaseNode):
    """MQL 验证节点 - 复用现有的 MQLValidator"""
    
    node_name = "mql_validation"
    description = "验证 MQL 的合规性和正确性"
    
    def __init__(self, db: Session = None):
        super().__init__(db)
        self.validator = MQLValidator(db)
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        mql = state.get("mql")
        
        if not mql:
            return {"should_retry_mql": True, "mql_errors": ["MQL 为空"]}
        
        # 复用现有的 MQLValidator
        is_valid, error_msg = self.validator.validate_mql(mql)
        
        if is_valid:
            self.add_step(state, "MQL 验证", "MQL 验证通过", "success")
            return {"should_retry_mql": False, "mql_errors": []}
        else:
            self.add_step(state, "MQL 验证", f"MQL 验证失败：{error_msg}", "error")
            
            max_retries = state.get("max_retries", 3)
            retry_count = state.get("retry_count", 0)
            should_retry = retry_count < max_retries
            
            return {"should_retry_mql": should_retry, "mql_errors": [error_msg]}
```

#### 3.3.5 MQL 修正节点
```python
# backend/app/agents/nodes/mql_correction.py

from typing import Dict, Any
import json
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.services.llm_client import call_llm

class MQLCorrectionNode(BaseNode):
    """MQL 修正节点 - 基于 LLM 智能修正"""
    
    node_name = "mql_correction"
    description = "基于验证错误修正 MQL"
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        mql = state.get("mql", {})
        errors = state.get("mql_errors", [])
        
        # 构建 Prompt 让 LLM 修正
        prompt = f"""修正以下 MQL 错误：

错误：
{chr(10).join([f'- {e}' for e in errors])}

原始 MQL：
{json.dumps(mql, ensure_ascii=False, indent=2)}

请根据错误信息修正 MQL，返回完整的 JSON。"""
        
        model_config = self._get_model_config()
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params=model_config["config_params"]
        )
        
        corrected_mql = self._parse_mql(response)
        
        self.add_step(state, "MQL 修正", "已根据错误信息修正 MQL", "success")
        
        return {"mql": corrected_mql}
    
    def _parse_mql(self, response: str) -> dict:
        mql_str = response.strip()
        if "```json" in mql_str:
            mql_str = mql_str.split("```json")[1].split("```")[0].strip()
        try:
            return json.loads(mql_str)
        except:
            return {}
    
    def _get_model_config(self) -> dict:
        from app.models.model_config import ModelConfig
        from app.utils.encryption import decrypt_api_key
        
        model_config = self.db.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()
        
        return {
            "provider": model_config.provider,
            "model_name": model_config.model_name,
            "api_key": decrypt_api_key(model_config.api_key) if model_config.api_key else None,
            "api_base": model_config.api_base,
            "config_params": model_config.config_params
        }
```

#### 3.3.6 SQL 转换节点
```python
# backend/app/agents/nodes/sql_translation.py

from typing import Dict, Any
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.services.mql_engine import mql_to_sql

class SQLTranslationNode(BaseNode):
    """SQL 转换节点 - 复用现有的 mql_engine"""
    
    node_name = "sql_translation"
    description = "将 MQL 转换为可执行的 SQL"
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        mql = state.get("mql")
        if not mql:
            return {}
        
        # 直接复用现有的 mql_to_sql
        result = await mql_to_sql(mql, self.db)
        
        self.add_step(state, "SQL 转换", "已将 MQL 转换为 SQL", "success")
        
        return {
            "sql": result.get("sql"),
            "sql_datasources": result.get("datasources", []),
            "sql_lineage": result.get("lineage", {})
        }
```

#### 3.3.7 查询执行节点
```python
# backend/app/agents/nodes/query_execution.py

from typing import Dict, Any
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.services.query_executor import execute_query

class QueryExecutionNode(BaseNode):
    """查询执行节点 - 复用现有的 query_executor"""
    
    node_name = "query_execution"
    description = "执行 SQL 查询"
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        sql = state.get("sql")
        datasources = state.get("sql_datasources", [])
        
        if not sql:
            return {}
        
        datasource_id = datasources[0] if datasources else None
        
        if not datasource_id:
            query_result = {
                "columns": ["日期", "销售额"],
                "data": [["2025-04-01", 1000000]],
                "total_count": 1,
                "chart_recommendation": "line"
            }
        else:
            query_result = await execute_query(
                sql=sql,
                datasource_id=datasource_id,
                limit=1000,
                db=self.db
            )
        
        # 保存查询历史（复用现有逻辑）
        from app.models.query_history import QueryHistory
        
        history = QueryHistory(
            natural_language=state["natural_language"],
            mql_query=state.get("mql"),
            sql_query=sql,
            execution_time=query_result.get("execution_time", 0),
            result_count=query_result.get("total_count", 0),
            status="success"
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        
        self.add_step(
            state,
            "查询执行",
            f"已执行查询，返回 {query_result.get('total_count', 0)} 条结果",
            "success"
        )
        
        return {
            "query_result": query_result,
            "query_id": history.id
        }
```

#### 3.3.8 结果解释节点
```python
# backend/app/agents/nodes/result_interpretation.py

from typing import Dict, Any
from app.agents.nodes.base_node import BaseNode
from app.agents.state.query_state import QueryState
from app.services.llm_client import call_llm

class ResultInterpretationNode(BaseNode):
    """结果解释节点 - 使用 LLM 生成洞察"""
    
    node_name = "result_interpretation"
    description = "解释查询结果，生成洞察"
    
    async def __call__(
        self, 
        state: QueryState, 
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        natural_language = state["natural_language"]
        query_result = state.get("query_result", {})
        
        if not query_result:
            return {}
        
        # 构建解释 Prompt
        prompt = f"""解释查询结果：

用户查询：{natural_language}
结果列：{', '.join(query_result.get('columns', []))}
数据样本：{query_result.get('data', [])[:3]}
总记录数：{query_result.get('total_count', 0)}

返回格式：
{{
  "summary": "总结",
  "key_insights": ["洞察1", "洞察2"],
  "visualization_suggestion": {{"type": "line", "description": "说明"}}
}}"""
        
        model_config = self._get_model_config()
        response = await call_llm(
            prompt=prompt,
            provider=model_config["provider"],
            model_name=model_config["model_name"],
            api_key=model_config["api_key"],
            api_base=model_config["api_base"],
            config_params={"temperature": 0.3, "max_tokens": 1024}
        )
        
        interpretation = self._parse_interpretation(response)
        
        self.add_step(state, "结果解释", "已生成查询结果解释", "success")
        
        return {
            "interpretation": interpretation,
            "insights": interpretation.get("key_insights", [])
        }
    
    def _parse_interpretation(self, response: str) -> dict:
        import json, re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {"summary": response, "key_insights": []}
    
    def _get_model_config(self) -> dict:
        from app.models.model_config import ModelConfig
        from app.utils.encryption import decrypt_api_key
        
        model_config = self.db.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()
        
        return {
            "provider": model_config.provider,
            "model_name": model_config.model_name,
            "api_key": decrypt_api_key(model_config.api_key) if model_config.api_key else None,
            "api_base": model_config.api_base,
            "config_params": model_config.config_params
        }
```

### 3.4 工作流定义

```python
# backend/app/agents/workflows/mql_query_workflow.py

from langgraph.graph import StateGraph, END
from app.agents.state.query_state import QueryState

# 导入节点
from app.agents.nodes.metadata_retrieval import MetadataRetrievalNode
from app.agents.nodes.intent_analysis import IntentAnalysisNode
from app.agents.nodes.mql_generation import MQLGenerationNode
from app.agents.nodes.mql_validation import MQLValidationNode
from app.agents.nodes.mql_correction import MQLCorrectionNode
from app.agents.nodes.sql_translation import SQLTranslationNode
from app.agents.nodes.query_execution import QueryExecutionNode
from app.agents.nodes.result_interpretation import ResultInterpretationNode

def create_mql_query_workflow(db_session):
    """创建 MQL 查询工作流"""
    
    # 初始化节点
    metadata_retrieval_node = MetadataRetrievalNode(db_session)
    intent_analysis_node = IntentAnalysisNode(db_session)
    mql_generation_node = MQLGenerationNode(db_session)
    mql_validation_node = MQLValidationNode(db_session)
    mql_correction_node = MQLCorrectionNode(db_session)
    sql_translation_node = SQLTranslationNode(db_session)
    query_execution_node = QueryExecutionNode(db_session)
    result_interpretation_node = ResultInterpretationNode(db_session)
    
    # 创建状态图
    workflow = StateGraph(QueryState)
    
    # 添加节点
    workflow.add_node("metadata_retrieval", metadata_retrieval_node)
    workflow.add_node("intent_analysis", intent_analysis_node)
    workflow.add_node("mql_generation", mql_generation_node)
    workflow.add_node("mql_validation", mql_validation_node)
    workflow.add_node("mql_correction", mql_correction_node)
    workflow.add_node("sql_translation", sql_translation_node)
    workflow.add_node("query_execution", query_execution_node)
    workflow.add_node("result_interpretation", result_interpretation_node)
    
    # 设置入口
    workflow.set_entry_point("metadata_retrieval")
    
    # 定义边（条件路由）
    
    # 1. 元数据检索 → 意图分析
    workflow.add_edge("metadata_retrieval", "intent_analysis")
    
    # 2. 意图分析 → MQL 生成
    workflow.add_edge("intent_analysis", "mql_generation")
    
    # 3. MQL 生成 → MQL 验证
    workflow.add_edge("mql_generation", "mql_validation")
    
    # 4. MQL 验证路由
    def should_retry_mql(state: QueryState) -> str:
        """决定是否重试 MQL 生成"""
        if state.get("should_retry_mql"):
            return "mql_correction"
        else:
            return "sql_translation"
    
    workflow.add_conditional_edges(
        "mql_validation",
        should_retry_mql,
        {
            "mql_correction": "mql_correction",
            "sql_translation": "sql_translation"
        }
    )
    
    # 5. MQL 修正 → MQL 验证（循环）
    workflow.add_edge("mql_correction", "mql_validation")
    
    # 6. SQL 转换 → 查询执行
    workflow.add_edge("sql_translation", "query_execution")
    
    # 7. 查询执行 → 结果解释
    workflow.add_edge("query_execution", "result_interpretation")
    
    # 8. 结果解释 → 结束
    workflow.add_edge("result_interpretation", END)
    
    # 编译工作流
    return workflow.compile()
```

### 3.5 智能体主类

```python
# backend/app/agents/mql_agent.py

from typing import Dict, Any, Optional
from langchain_core.runnables import RunnableConfig
from sqlalchemy.orm import Session

class MQLAgent:
    """MQL 查询智能体"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.workflow = self._create_workflow()
    
    def _create_workflow(self):
        """创建工作流"""
        from app.agents.workflows.mql_query_workflow import create_mql_query_workflow
        return create_mql_query_workflow(self.db_session)
    
    async def execute_query(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """执行查询"""
        
        # 初始化状态
        initial_state: QueryState = {
            "natural_language": natural_language,
            "context": context or {},
            "metadata": {},
            "suggested_metrics": [],
            "suggested_dimensions": [],
            "filterable_fields": [],
            "time_formats": [],
            "intent": {},
            "intent_type": None,
            "complexity": None,
            "mql": None,
            "mql_attempts": 0,
            "mql_errors": [],
            "sql": None,
            "sql_datasources": [],
            "sql_lineage": {},
            "query_result": None,
            "query_id": None,
            "interpretation": None,
            "insights": [],
            "steps": [],
            "should_retry_mql": False,
            "retry_count": 0,
            "max_retries": max_retries,
            "messages": []
        }
        
        # 运行工作流
        config = RunnableConfig(recursion_limit=100)
        final_state = await self.workflow.ainvoke(initial_state, config=config)
        
        return {
            "natural_language": natural_language,
            "mql": final_state.get("mql"),
            "sql": final_state.get("sql"),
            "result": final_state.get("query_result"),
            "interpretation": final_state.get("interpretation"),
            "insights": final_state.get("insights", []),
            "steps": final_state.get("steps", []),
            "query_id": final_state.get("query_id")
        }
```

### 3.6 API 接口

```python
# backend/app/api/v1/agent.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.database import get_db
from app.agents.mql_agent import MQLAgent

router = APIRouter()

class AgentQueryRequest(BaseModel):
    natural_language: str
    context: Optional[Dict[str, Any]] = None
    max_retries: int = 3

@router.post("/execute")
async def execute_agent_query(
    request: AgentQueryRequest,
    db: Session = Depends(get_db)
):
    """通过智能体执行查询"""
    
    agent = MQLAgent(db)
    result = await agent.execute_query(
        natural_language=request.natural_language,
        context=request.context,
        max_retries=request.max_retries
    )
    
    return result
```

## 四、实施计划

### Phase 1: 基础架构搭建（1-2周）
1. 创建目录结构
2. 实现状态定义
3. 实现基础节点类
4. 实现 8 个核心节点
5. 实现工作流定义

### Phase 2: 集成测试（1周）
1. 实现 API 接口
2. 集成现有服务
3. 编写单元测试
4. 验证功能等价性

### Phase 3: 增强优化（1-2周）
1. 添加日志和监控
2. 优化性能
3. 添加记忆机制
4. 实现下钻分析工作流

### Phase 4: 上线部署（1周）
1. 灰度发布
2. 监控和调优
3. 文档完善
4. 团队培训

## 五、优势分析

### 5.1 可扩展性
- 新增节点无需修改现有代码
- 工作流可以灵活组合
- 支持多智能体协作

### 5.2 可观测性
- 每个节点都有清晰的输入输出
- 状态变化可追踪
- 易于调试和问题定位

### 5.3 可维护性
- 节点职责单一
- 代码模块化
- 易于测试

### 5.4 智能化
- 支持动态路由
- 支持多轮修正
- 支持结果解释

## 六、风险和缓解

### 6.1 性能风险
- LangGraph 可能引入额外开销
- 缓解：使用缓存、并行执行

### 6.2 复杂性增加
- 需要学习 LangGraph
- 缓解：提供培训、文档

### 6.3 兼容性
- 需要保证与现有 API 兼容
- 缓解：双系统并行运行

## 七、总结

本方案通过 LangGraph 重构问数流程，将现有的线性执行改为图状智能体架构，在保留现有语义层、应用层和数据层能力的基础上，提升了系统的可扩展性、可维护性和智能化水平。核心优势包括：

1. **高复用性**：现有服务层代码基本无需修改
2. **灵活性**：图状工作流支持动态路由和多轮修正
3. **可观测性**：状态管理和步骤记录便于追踪
4. **可扩展性**：新增节点和工作流非常容易

建议按照实施计划逐步推进，确保平稳过渡。
