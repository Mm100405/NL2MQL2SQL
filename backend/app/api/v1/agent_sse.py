"""
[旧版本 - 已废弃] 流式Agent查询 - SSE实现示例

⚠️  此文件已废弃，功能已迁移到 agent.py
⚠️  此文件不再被任何路由引用

迁移说明:
    - 流式步骤回调逻辑已迁移到 agent.py 的 agent_query_stream 函数
    - streaming_step_callback 逻辑已合并到主端点
    - 如需修改流式查询逻辑，请修改 agent.py

保留此文件仅用于参考备份。
"""

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse  # 需要安装: pip install sse-starlette
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import json
import asyncio
from datetime import datetime

from app.database import get_db
from app.models.model_config import ModelConfig
from app.agents.mql_agent import MQLAgent
from app.utils.encryption import decrypt_api_key

router = APIRouter()


class AgentQueryRequest(BaseModel):
    """Agent查询请求"""
    natural_language: str
    context: Optional[dict] = None
    user_id: Optional[str] = "anonymous"
    conversation_id: Optional[str] = None


async def execute_query_with_stream(
    query_id: str,
    natural_language: str,
    context: dict,
    db_session: Session,
    queue: asyncio.Queue,
    conversation_id: str = None
):
    """执行查询并推送步骤到队列（流式）"""
    import os

    try:
        # 获取模型配置
        model_config = db_session.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()

        if not model_config:
            await queue.put({
                "type": "error",
                "data": {"message": "No active model configured"}
            })
            return

        # 设置环境变量
        if model_config.api_key:
            os.environ['OPENAI_API_KEY'] = decrypt_api_key(model_config.api_key)
        if model_config.api_base:
            os.environ['OPENAI_API_BASE'] = model_config.api_base

        # 创建Agent（自定义步骤回调推送到队列）
        agent = MQLAgent(db_session=db_session, query_id=query_id, conversation_id=conversation_id)

        # 创建同步版本的步骤回调（BaseNode.add_step是同步调用）
        import asyncio
        loop = asyncio.get_event_loop()
        
        # 用于存储当前状态，在不同节点间共享
        current_state = {}
        
        def streaming_step_callback(step: dict):
            """步骤回调，推送到SSE队列（同步版本）"""
            node = step.get('node', '')
            
            # 根据不同节点，推送不同的中间数据
            if node == 'preparation':
                # PreparationNode 完成后，推送意图识别结果
                asyncio.ensure_future(queue.put({
                    "type": "intermediate",
                    "data": {
                        "stage": "preparation",
                        "title": step.get('title', '准备阶段'),
                        "content": step.get('content', ''),
                        "suggested_metrics": current_state.get('suggested_metrics', []),
                        "suggested_dimensions": current_state.get('suggested_dimensions', []),
                        "intent": current_state.get('intent'),
                        "intent_type": current_state.get('intent_type'),
                        "complexity": current_state.get('complexity'),
                        "metadata": current_state.get('metadata', {})
                    }
                }), loop=loop)
            elif node == 'generation':
                # GenerationNode 完成后，推送 MQL
                asyncio.ensure_future(queue.put({
                    "type": "intermediate",
                    "data": {
                        "stage": "generation",
                        "title": step.get('title', 'MQL生成'),
                        "content": step.get('content', ''),
                        "mql": current_state.get('mql'),
                        "mql_attempts": current_state.get('mql_attempts', 1),
                        "mql_errors": current_state.get('mql_errors', [])
                    }
                }), loop=loop)
            elif node == 'execution':
                # ExecutionNode 完成后，推送 SQL 和查询结果
                asyncio.ensure_future(queue.put({
                    "type": "intermediate",
                    "data": {
                        "stage": "execution",
                        "title": step.get('title', '查询执行'),
                        "content": step.get('content', ''),
                        "sql": current_state.get('sql'),
                        "sql_datasources": current_state.get('sql_datasources', []),
                        "result": current_state.get('query_result'),
                        "query_id": current_state.get('query_id')
                    }
                }), loop=loop)
            elif node == 'interpretation':
                # InterpretationNode 完成后，推送解释和洞察
                asyncio.ensure_future(queue.put({
                    "type": "intermediate",
                    "data": {
                        "stage": "interpretation",
                        "title": step.get('title', '结果解释'),
                        "content": step.get('content', ''),
                        "interpretation": current_state.get('interpretation'),
                        "insights": current_state.get('insights', []),
                        "visualization": current_state.get('visualization'),
                        "visualization_suggestion": current_state.get('visualization_suggestion')
                    }
                }), loop=loop)
            else:
                # 其他步骤，推送普通步骤信息
                asyncio.ensure_future(queue.put({
                    "type": "step",
                    "data": step
                }), loop=loop)

        agent.step_callback = streaming_step_callback
        
        # 创建工作流包装器，在每个节点完成后更新 current_state
        from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow
        
        class StreamingWorkflow(MQLQueryWorkflow):
            """流式工作流 - 在每个节点完成后推送中间结果"""
            
            async def run(self, initial_state: QueryState, config: RunnableConfig = None):
                graph = self.get_graph()
                
                # 逐步执行每个节点
                nodes = ["preparation", "generation", "execution", "interpretation"]
                
                for node_name in nodes:
                    # 更新当前状态
                    nonlocal current_state
                    current_state = initial_state.copy()
                    
                    # 执行节点
                    result = await graph.ainvoke(initial_state, config)
                    initial_state = result
                    current_state = result
                    
                    # 节点执行完成后，current_state 已经包含该节点的输出
                
                return initial_state
        
        # 使用流式工作流
        workflow = StreamingWorkflow(db_session, step_callback=streaming_step_callback)
        workflow.build()
        
        # 替换 agent 的工作流
        agent.workflow = workflow.get_graph()

        # 执行查询 - 将 conversation_id 放入 context 中传递
        if conversation_id:
            context = context or {}
            context['conversation_id'] = conversation_id
        
        result = await agent.execute_query(
            natural_language=natural_language,
            context=context
        )

        # 推送最终结果 - 包含完整的数据字段
        await queue.put({
            "type": "result",
            "data": {
                "natural_language": result.get('natural_language'),
                "mql": result.get('mql'),
                "sql": result.get('sql'),
                "result": result.get('result'),
                "interpretation": result.get('interpretation'),
                "insights": result.get('insights', []),
                "visualization": result.get('visualization'),
                "visualization_suggestion": result.get('visualization_suggestion'),
                "steps": result.get('steps', []),
                "query_id": result.get('query_id'),
                "mql_attempts": result.get('mql_attempts', 0),
                # 新增：意图识别相关
                "intent": result.get('intent'),
                "intent_type": result.get('intent_type'),
                "complexity": result.get('complexity'),
                # 新增：建议的指标和维度
                "suggested_metrics": result.get('suggested_metrics', []),
                "suggested_dimensions": result.get('suggested_dimensions', []),
                # 新增：SQL相关信息
                "sql_datasources": result.get('sql_datasources', []),
                # 新增：MQL验证信息
                "mql_errors": result.get('mql_errors', []),
                "confidence": result.get('confidence')
            }
        })

    except Exception as e:
        await queue.put({
            "type": "error",
            "data": {"message": str(e)}
        })
    finally:
        # 发送结束信号
        await queue.put({"type": "done"})


async def event_generator(query_id: str, natural_language: str, context: dict, db: Session, conversation_id: str = None):
    """SSE事件生成器"""
    from app.database import SessionLocal

    # 创建新的数据库会话
    db = SessionLocal()

    # 创建队列用于异步通信
    queue = asyncio.Queue()

    # 启动后台任务
    task = asyncio.create_task(
        execute_query_with_stream(query_id, natural_language, context, db, queue, conversation_id)
    )

    try:
        while True:
            # 等待队列中的事件
            event = await queue.get()

            # 检查是否结束
            if event.get("type") == "done":
                break

            # 格式化为SSE事件
            data = json.dumps(event.get("data", {}))
            yield {
                "event": event["type"],
                "data": data
            }

    finally:
        # 确保后台任务完成
        if not task.done():
            task.cancel()
        db.close()


@router.post("/query/stream")
async def agent_query_stream(
    request: AgentQueryRequest,
    db: Session = Depends(get_db)
):
    """流式Agent查询（SSE）

    返回Server-Sent Events流，实时推送查询步骤和结果。

    前端使用示例：
    ```javascript
    const eventSource = new EventSource('/api/v1/agent/query/stream?natural_language=查询&user_id=test');

    eventSource.addEventListener('step', (event) => {
        const step = JSON.parse(event.data);
        console.log('Step:', step);
        // 实时显示步骤
    });

    eventSource.addEventListener('result', (event) => {
        const result = JSON.parse(event.data);
        console.log('Result:', result);
        // 显示最终结果
        eventSource.close();
    });

    eventSource.addEventListener('error', (event) => {
        const error = JSON.parse(event.data);
        console.error('Error:', error);
        eventSource.close();
    });
    ```
    """
    query_id = f"query_{datetime.now().timestamp()}"

    return EventSourceResponse(
        event_generator(query_id, request.natural_language, request.context or {}, db, request.conversation_id)
    )
