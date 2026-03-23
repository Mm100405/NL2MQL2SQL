"""
Agent API - 4节点企业级架构的Agent接口
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List, AsyncGenerator
from pydantic import BaseModel
import uuid
import asyncio
import json
from datetime import datetime
import time

from app.database import get_db
from app.models.model_config import ModelConfig
from app.models.query_history import QueryHistory
from app.agents.mql_agent import MQLAgent
from app.utils.encryption import decrypt_api_key

router = APIRouter()

# 全局存储查询步骤
_query_steps_store = {}

def print_query_steps_store():
    """打印步骤存储状态（用于调试）"""
    print(f"\n=== Query Steps Store Debug ===")
    print(f"Total queries: {len(_query_steps_store)}")
    for qid, steps in _query_steps_store.items():
        print(f"  Query {qid}: {len(steps)} steps")
        for step in steps:
            print(f"    - {step.get('title')}: {step.get('status')}")
    print(f"===============================\n")


# ============ Schemas ============
class AgentQueryRequest(BaseModel):
    """Agent查询请求（用于文档，实际使用查询参数）"""
    natural_language: str
    context: Optional[dict] = None
    user_id: Optional[str] = "anonymous"


class AgentStep(BaseModel):
    """执行步骤"""
    node: str
    skill: str
    status: str
    message: str
    timestamp: Optional[str] = None


class AgentQueryResponse(BaseModel):
    """Agent查询响应"""
    natural_language: str
    mql: Optional[dict] = None
    sql: Optional[str] = None
    result: Optional[dict] = None
    interpretation: Optional[str] = None
    insights: List[str] = []
    steps: List[AgentStep] = []
    query_id: Optional[str] = None
    execution_time: Optional[int] = None
    success: bool
    message: str


class AgentStatusResponse(BaseModel):
    """Agent状态响应"""
    model_config = {"protected_namespaces": ()}

    is_available: bool
    model_configured: bool
    model_info: Optional[dict] = None
    skills_loaded: int


class SkillInfo(BaseModel):
    """Skill信息"""
    name: str
    type: str
    description: str
    dependencies: List[str] = []
    enabled: bool = True


class SkillToggleRequest(BaseModel):
    """技能切换请求"""
    skill_name: str
    enabled: bool


class AgentSkillsResponse(BaseModel):
    """Agent Skills列表响应"""
    code_skills: List[SkillInfo] = []
    markdown_skills: List[SkillInfo] = []
    total: int


# ============ Routes ============

@router.get("/status", response_model=AgentStatusResponse)
def get_agent_status(db: Session = Depends(get_db)):
    """获取Agent状态"""
    from app.agents.skills.skill_loader import SkillLoader

    # 检查模型配置
    model_config = db.query(ModelConfig).filter(
        ModelConfig.is_default == True,
        ModelConfig.is_active == True
    ).first()

    # 检查Skills
    try:
        loader = SkillLoader()
        code_skills = loader.load_code_skills()
        markdown_skills = loader.load_markdown_skills()
        skills_loaded = len(code_skills) + len(markdown_skills)
    except Exception:
        skills_loaded = 0

    return AgentStatusResponse(
        is_available=True,
        model_configured=model_config is not None,
        model_info={
            "name": model_config.name if model_config else None,
            "provider": model_config.provider if model_config else None,
            "model_name": model_config.model_name if model_config else None
        } if model_config else None,
        skills_loaded=skills_loaded
    )


@router.get("/skills", response_model=AgentSkillsResponse)
def get_agent_skills():
    """获取Agent所有Skills"""
    from app.agents.skills.skill_loader import SkillLoader

    try:
        loader = SkillLoader()
        code_skills_dict = loader.load_code_skills()
        markdown_skills_dict = loader.load_markdown_skills()

        code_skills = []
        for skill_name, skill_instance in code_skills_dict.items():
            code_skills.append(SkillInfo(
                name=skill_name,
                type="code",
                description=skill_instance.description,
                dependencies=skill_instance.dependencies if hasattr(skill_instance, 'dependencies') else []
            ))

        markdown_skills = []
        for skill_name, skill_obj in markdown_skills_dict.items():
            markdown_skills.append(SkillInfo(
                name=skill_name,
                type="markdown",
                description=skill_obj.description,
                dependencies=[]
            ))

        return AgentSkillsResponse(
            code_skills=code_skills,
            markdown_skills=markdown_skills,
            total=len(code_skills) + len(markdown_skills)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load skills: {str(e)}")


# 全局技能状态存储
_enabled_skills: dict = {}


@router.post("/skills/toggle")
def toggle_skill(request: SkillToggleRequest):
    """切换技能启用/禁用状态"""
    _enabled_skills[request.skill_name] = request.enabled
    return {
        "success": True,
        "skill_name": request.skill_name,
        "enabled": request.enabled,
        "message": f"Skill '{request.skill_name}' has been {'enabled' if request.enabled else 'disabled'}"
    }


@router.get("/skills/enabled")
def get_enabled_skills():
    """获取所有启用的技能"""
    return {
        "enabled_skills": _enabled_skills
    }


@router.post("/query/stream")
async def agent_query_stream(
    request: AgentQueryRequest,
    db: Session = Depends(get_db)
):
    """流式Agent查询（SSE）- 使用新架构

    返回Server-Sent Events流，实时推送查询步骤和结果。
    """
    import os
    query_id = str(uuid.uuid4())

    print(f"[SSE Query] Received request: natural_language={request.natural_language}")

    async def event_stream():
        try:
            # 获取模型配置
            model_config = db.query(ModelConfig).filter(
                ModelConfig.is_default == True,
                ModelConfig.is_active == True
            ).first()

            if not model_config:
                yield format_sse_event("error", {"message": "No active model configured"})
                return

            # 设置环境变量
            if model_config.api_key:
                api_key = decrypt_api_key(model_config.api_key)
                os.environ['OPENAI_API_KEY'] = api_key
            if model_config.api_base:
                os.environ['OPENAI_API_BASE'] = model_config.api_base

            # 发送开始事件
            yield format_sse_event("start", {"query_id": query_id})

            # 使用增强版管理器（支持动态 Skills）
            from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager

            manager = get_enhanced_deep_agents_manager(db_session=db)

            # 初始化步骤存储
            _query_steps_store[query_id] = []

            # 定义步骤回调函数（直接推送到步骤存储）
            def step_callback(step_info):
                """步骤回调，推送到步骤存储"""
                print(f"[Step Callback] Node: {step_info.get('node')}, Title: {step_info.get('title')}")
                
                if query_id not in _query_steps_store:
                    _query_steps_store[query_id] = []
                
                _query_steps_store[query_id].append(step_info)

            # 启动查询任务（使用 Skills）
            task = asyncio.create_task(
                manager.execute_stream_with_skills(
                    natural_language=request.natural_language,
                    context=request.context or {},
                    max_retries=3,
                    step_callback=step_callback,
                    use_skills=True  # 启用已加载的 Skills
                )
            )

            # 监控步骤并推送
            last_step_count = 0
            start_time = time.time()

            while not task.done():
                await asyncio.sleep(0.1)

                if query_id in _query_steps_store:
                    current_steps = _query_steps_store[query_id]
                    # 推送新步骤
                    while last_step_count < len(current_steps):
                        step = current_steps[last_step_count]
                        print(f"[Pushing Step] {step.get('node')}: {step.get('title')}")
                        yield format_sse_event("step", step)
                        last_step_count += 1

            # 等待任务完成并获取结果
            result = await task
            execution_time = int((time.time() - start_time) * 1000)

            # 推送剩余的步骤（如果有）
            if query_id in _query_steps_store:
                current_steps = _query_steps_store[query_id]
                while last_step_count < len(current_steps):
                    step = current_steps[last_step_count]
                    print(f"[Pushing Remaining Step] {step.get('node')}: {step.get('title')}")
                    yield format_sse_event("step", step)
                    last_step_count += 1

            # 发送结果事件
            if result:
                yield format_sse_event("result", {
                    "natural_language": result.get('natural_language'),
                    "mql": result.get('mql'),
                    "sql": result.get('sql'),
                    "result": result.get('result'),
                    "interpretation": result.get('interpretation'),
                    "insights": result.get('insights', []),
                    "execution_time": execution_time
                })

        except Exception as e:
            print(f"[Query Stream Error] {e}")
            import traceback
            traceback.print_exc()
            yield format_sse_event("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


async def event_stream_generator(
    query_id: str,
    natural_language: str,
    context: Optional[str],
    db: Session
) -> AsyncGenerator[str, None]:
    """SSE事件生成器"""
    import os

    try:
        # 获取模型配置
        model_config = db.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()

        if not model_config:
            yield format_sse_event("error", {"message": "No active model configured"})
            return

        # 设置环境变量
        if model_config.api_key:
            api_key = decrypt_api_key(model_config.api_key)
            os.environ['OPENAI_API_KEY'] = api_key
        if model_config.api_base:
            os.environ['OPENAI_API_BASE'] = model_config.api_base

        # 发送开始事件
        yield format_sse_event("start", {"query_id": query_id})

        # 创建Agent
        agent = MQLAgent(db_session=db, query_id=query_id)

        # 解析context参数
        context_dict = {}
        if context:
            try:
                context_dict = json.loads(context)
            except:
                context_dict = {}

        # 启动查询任务
        task = asyncio.create_task(
            agent.execute_query(
                natural_language=natural_language,
                context=context_dict
            )
        )

        # 监控步骤并推送
        last_step_count = 0
        start_time = time.time()

        while not task.done():
            await asyncio.sleep(0.1)  # 每100ms检查一次

            # 检查是否有新步骤
            if query_id in _query_steps_store:
                current_steps = _query_steps_store[query_id]
                # 推送新步骤
                while last_step_count < len(current_steps):
                    yield format_sse_event("step", current_steps[last_step_count])
                    last_step_count += 1

        # 获取结果
        result = await task
        execution_time = int((time.time() - start_time) * 1000)

        # 发送结果事件
        if result:
            # 保存查询历史
            try:
                history = QueryHistory(
                    conversation_id=str(uuid.uuid4()),
                    natural_language=natural_language,
                    mql_query=result.get('mql'),
                    sql_query=result.get('sql'),
                    execution_time=execution_time,
                    result_count=result.get('result', {}).get('total_count', 0) if result.get('result') else 0,
                    status="success",
                    messages=[
                        {
                            "role": "user",
                            "content": natural_language
                        },
                        {
                            "role": "assistant",
                            "content": result.get('interpretation', '')
                        }
                    ]
                )
                db.add(history)
                db.commit()
            except Exception as e:
                print(f"Failed to save query history: {e}")

            yield format_sse_event("result", {
                "natural_language": result.get('natural_language'),
                "mql": result.get('mql'),
                "sql": result.get('sql'),
                "result": result.get('result'),
                "interpretation": result.get('interpretation'),
                "insights": result.get('insights', [])
            })

    except Exception as e:
        print(f"[Query Stream Error] {e}")
        yield format_sse_event("error", {"message": str(e)})


def format_sse_event(event_type: str, data: dict) -> str:
    """格式化SSE事件"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"




@router.get("/workflow")
def get_workflow_info():
    """获取工作流信息"""
    from app.agents.workflows.mql_query_workflow import MQLQueryWorkflow

    try:
        workflow = MQLQueryWorkflow(db_session=None)
        info = workflow.get_graph_info()

        return {
            "nodes": [
                {
                    "name": node,
                    "type": "node"
                }
                for node in info["nodes"]
            ],
            "edges": [
                {
                    "from": edge[0],
                    "to": edge[1]
                }
                for edge in info["edges"]
            ],
            "total_nodes": info["total_nodes"],
            "total_edges": info["total_edges"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow info: {str(e)}")


@router.post("/test")
async def test_agent_endpoint(
    natural_language: str,
    db: Session = Depends(get_db)
):
    """测试Agent功能（简化版本）"""
    try:
        # 检查模型配置
        model_config = db.query(ModelConfig).filter(
            ModelConfig.is_default == True,
            ModelConfig.is_active == True
        ).first()

        if not model_config:
            return {
                "success": False,
                "message": "No model configured",
                "recommendation": "Please configure an AI model in Settings > Model Config"
            }

        # 检查Skills
        from app.agents.skills.skill_loader import SkillLoader
        loader = SkillLoader()
        code_skills = loader.load_code_skills()
        markdown_skills = loader.load_markdown_skills()

        return {
            "success": True,
            "message": "Agent is ready",
            "model": {
                "name": model_config.name,
                "provider": model_config.provider,
                "model_name": model_config.model_name
            },
            "skills": {
                "code_skills_count": len(code_skills),
                "markdown_skills_count": len(markdown_skills),
                "total": len(code_skills) + len(markdown_skills)
            },
            "test_query": natural_language,
            "recommendation": f"Try querying: {natural_language}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Test failed: {str(e)}",
            "error": str(e)
        }



