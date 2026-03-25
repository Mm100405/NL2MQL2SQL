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

            # 初始化步骤存储
            _query_steps_store[query_id] = []

            # 用于存储当前状态，在不同节点间共享
            current_state = {}

            # 创建同步版本的步骤回调（同步调用推送到队列）
            def streaming_step_callback(step: dict):
                """流式步骤回调 - 推送中间结果到步骤存储"""
                node = step.get('node', '')

                # 更新当前状态（content是字符串，直接从step读取字段）
                if node == 'preparation':
                    current_state.update({
                        'preparation': step,
                        'intent': step.get('metadata', {}).get('intent'),
                        'intent_type': step.get('metadata', {}).get('intent_type'),
                        'complexity': step.get('metadata', {}).get('complexity'),
                        'suggested_metrics': step.get('suggested_metrics', []),
                        'suggested_dimensions': step.get('suggested_dimensions', []),
                    })
                elif node == 'generation':
                    current_state.update({
                        'generation': step,
                        'mql': step.get('mql'),
                        'mql_attempts': step.get('mql_attempts', 1),
                        'mql_errors': step.get('mql_errors', []),
                    })
                elif node == 'execution':
                    current_state.update({
                        'execution': step,
                        'sql': step.get('sql'),
                        'sql_datasources': step.get('sql_datasources', []),
                        'query_result': step.get('result'),
                        'query_id': step.get('query_id'),
                    })
                elif node == 'interpretation':
                    current_state.update({
                        'interpretation': step,
                        'insights': step.get('insights', []),
                        'visualization': step.get('visualization'),
                    })

                # 推送中间结果
                if query_id not in _query_steps_store:
                    _query_steps_store[query_id] = []

                _query_steps_store[query_id].append({
                    "type": "step",
                    "node": node,
                    "title": step.get('title', ''),
                    "status": step.get('status', ''),
                    "content": step.get('content', {}),
                    "intermediate_data": {
                        "stage": node,
                        "intent": current_state.get('intent'),
                        "intent_type": current_state.get('intent_type'),
                        "complexity": current_state.get('complexity'),
                        "suggested_metrics": current_state.get('suggested_metrics', []),
                        "suggested_dimensions": current_state.get('suggested_dimensions', []),
                        "mql": current_state.get('mql'),
                        "mql_attempts": current_state.get('mql_attempts', 1),
                        "mql_errors": current_state.get('mql_errors', []),
                        "sql": current_state.get('sql'),
                        "sql_datasources": current_state.get('sql_datasources', []),
                        "query_result": current_state.get('query_result'),
                        "query_id": current_state.get('query_id'),
                        "insights": current_state.get('insights', []),
                        "visualization": current_state.get('visualization'),
                    }
                })

            # 启动查询任务（使用 Skills）
            task = asyncio.create_task(
                manager.execute_stream_with_skills(
                    natural_language=request.natural_language,
                    context=request.context or {},
                    max_retries=3,
                    step_callback=streaming_step_callback,
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
                    "execution_time": execution_time,
                    # 新增：意图识别相关
                    "intent": current_state.get('intent'),
                    "intent_type": current_state.get('intent_type'),
                    "complexity": current_state.get('complexity'),
                    # 新增：建议的指标和维度
                    "suggested_metrics": current_state.get('suggested_metrics', []),
                    "suggested_dimensions": current_state.get('suggested_dimensions', []),
                    # 新增：SQL相关信息
                    "sql_datasources": current_state.get('sql_datasources', []),
                    # 新增：MQL验证信息
                    "mql_errors": current_state.get('mql_errors', []),
                    "mql_attempts": current_state.get('mql_attempts', 1),
                    "confidence": result.get('confidence'),
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


# ============ Time Range Parser ============
class TimeRangeRequest(BaseModel):
    """时间范围解析请求"""
    filters: Optional[dict] = None  # MQL filters 对象
    mql: Optional[dict] = None  # 完整的 MQL 对象（优先使用此获取 filters）


class TimeRangeResponse(BaseModel):
    """时间范围解析响应"""
    success: bool
    message: str
    time_ranges: Optional[dict] = None  # {field_name: {start: "2023-01-01 00:00:00", end: "2026-01-01 00:00:00"}}


@router.post("/parse-time-ranges", response_model=TimeRangeResponse)
async def parse_time_ranges(request: TimeRangeRequest, db: Session = Depends(get_db)):
    """
    解析 MQL 中的时间过滤条件，返回实际的时间范围

    支持 MQL 时间函数：
    - LAST_N_DAYS(n), LAST_N_MONTHS(n), LAST_N_YEARS(n)
    - NEXT_N_DAYS(n), NEXT_N_MONTHS(n)
    - TODAY(), YESTERDAY(), TOMORROW()
    - THIS_WEEK(), THIS_MONTH(), THIS_YEAR()
    """
    try:
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta

        # 提取 filters
        filters = request.filters
        if request.mql and request.filters is None:
            filters = request.mql.get('filters')

        if not filters:
            return TimeRangeResponse(
                success=True,
                message="No filters to parse",
                time_ranges={}
            )

        # 平铺 filters
        def flatten_filters(filter_obj):
            """平铺嵌套的 filter 结构"""
            conditions = []

            if isinstance(filter_obj, list):
                for item in filter_obj:
                    conditions.extend(flatten_filters(item))
            elif isinstance(filter_obj, dict):
                if 'conditions' in filter_obj:
                    # 这是一个分组
                    for cond in filter_obj['conditions']:
                        conditions.extend(flatten_filters(cond))
                elif 'field' in filter_obj and 'op' in filter_obj:
                    # 这是一个条件
                    conditions.append(filter_obj)

            return conditions

        conditions = flatten_filters(filters)

        # 查询维度元数据，识别时间字段
        from app.models.dimension import Dimension

        # 获取所有维度（用于识别时间字段）
        dimensions = db.query(Dimension).all()
        time_fields = set()
        time_field_types = {}  # 存储时间字段的数据类型

        for dim in dimensions:
            is_time_dim = (
                str(dim.dimension_type).lower() == "time" or
                str(dim.data_type).lower() in ["date", "datetime", "timestamp"]
            )
            if is_time_dim:
                # 同时添加 name 和 physical_column，因为 filters 中的 field 可能是任一个
                time_fields.add(dim.name)
                time_fields.add(dim.physical_column)
                time_field_types[dim.name] = dim.data_type
                time_field_types[dim.physical_column] = dim.data_type

        # 收集时间字段的条件
        time_conditions = {}
        for cond in conditions:
            field = cond.get('field')
            if field in time_fields:
                if field not in time_conditions:
                    time_conditions[field] = []
                time_conditions[field].append(cond)

        # 计算实际时间范围
        result = {}

        def resolve_time_function(func_str):
            """
            解析时间函数并返回实际 datetime
            支持: LAST_N_DAYS(n), LAST_N_MONTHS(n), LAST_N_YEARS(n) 等
            """
            import re

            if not isinstance(func_str, str):
                try:
                    # 尝试直接解析为日期
                    return datetime.strptime(str(func_str), '%Y-%m-%d')
                except:
                    return None

            func_str = func_str.strip()

            # TODAY() -> 今天 00:00:00
            if func_str.upper() == "TODAY()":
                return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # YESTERDAY() -> 昨天 00:00:00
            if func_str.upper() == "YESTERDAY()":
                return (datetime.now() - timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            # TOMORROW() -> 明天 00:00:00
            if func_str.upper() == "TOMORROW()":
                return (datetime.now() + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            # LAST_N_DAYS(n)
            match = re.match(r'LAST_N_DAYS\s*\(\s*(\d+)\s*\)', func_str, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                return (datetime.now() - timedelta(days=n)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            # LAST_N_MONTHS(n)
            match = re.match(r'LAST_N_MONTHS\s*\(\s*(\d+)\s*\)', func_str, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                result_dt = datetime.now() - relativedelta(months=n)
                return result_dt.replace(hour=0, minute=0, second=0, microsecond=0)

            # LAST_N_YEARS(n)
            match = re.match(r'LAST_N_YEARS\s*\(\s*(\d+)\s*\)', func_str, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                result_dt = datetime.now() - relativedelta(years=n)
                return result_dt.replace(hour=0, minute=0, second=0, microsecond=0)

            # NEXT_N_DAYS(n)
            match = re.match(r'NEXT_N_DAYS\s*\(\s*(\d+)\s*\)', func_str, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                return (datetime.now() + timedelta(days=n)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            # NEXT_N_MONTHS(n)
            match = re.match(r'NEXT_N_MONTHS\s*\(\s*(\d+)\s*\)', func_str, re.IGNORECASE)
            if match:
                n = int(match.group(1))
                result_dt = datetime.now() + relativedelta(months=n)
                return result_dt.replace(hour=0, minute=0, second=0, microsecond=0)

            # THIS_WEEK()
            if func_str.upper() == "THIS_WEEK()":
                # 本周一
                today = datetime.now()
                days_since_monday = today.weekday()
                return (today - timedelta(days=days_since_monday)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )

            # THIS_MONTH()
            if func_str.upper() == "THIS_MONTH()":
                return datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            # THIS_YEAR()
            if func_str.upper() == "THIS_YEAR()":
                return datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

            # 尝试解析为日期字符串
            try:
                return datetime.strptime(func_str, '%Y-%m-%d')
            except:
                try:
                    return datetime.strptime(func_str, '%Y-%m-%d %H:%M:%S')
                except:
                    pass

            return None

        for field, conds in time_conditions.items():
            start_time = None
            end_time = None
            data_type = time_field_types.get(field, 'datetime')

            for cond in conds:
                op = cond.get('op')
                value = cond.get('value')

                if value is None:
                    continue

                parsed_time = resolve_time_function(value)

                if parsed_time:
                    if op == '>=' or op == '>':
                        if start_time is None or parsed_time > start_time:
                            start_time = parsed_time
                    elif op == '<=' or op == '<':
                        if end_time is None or parsed_time < end_time:
                            end_time = parsed_time
                    elif op == '=':
                        start_time = parsed_time
                        end_time = parsed_time

            # 根据数据类型调整时间范围
            if start_time:
                if data_type == 'date':
                    # date 类型只显示年月日
                    start_time_str = start_time.strftime('%Y-%m-%d')
                else:
                    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                start_time_str = None

            if end_time:
                if data_type == 'date':
                    end_time_str = end_time.strftime('%Y-%m-%d')
                else:
                    end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                # 默认使用当前时间作为结束时间
                if data_type == 'date':
                    end_time_str = datetime.now().strftime('%Y-%m-%d')
                else:
                    end_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if start_time_str or end_time_str:
                result[field] = {
                    'start': start_time_str,
                    'end': end_time_str,
                    'data_type': data_type
                }

        return TimeRangeResponse(
            success=True,
            message=f"Parsed {len(result)} time range(s)",
            time_ranges=result
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return TimeRangeResponse(
            success=False,
            message=f"Failed to parse time ranges: {str(e)}",
            time_ranges=None
        )






