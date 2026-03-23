"""
Skills 管理 API（简化版）

提供 RESTful API 用于动态加载、卸载、查询外部标准 Skills
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/skills", tags=["Skills"])


# ============ Schemas ============

class LoadSkillFromURLRequest(BaseModel):
    """从 URL 加载 Skill 请求"""
    skill_id: str
    url: str
    force_reload: bool = False


class LoadSkillFromLocalRequest(BaseModel):
    """从本地加载 Skill 请求"""
    skill_id: str
    local_path: str
    force_reload: bool = False


class LoadSkillsFromDirectoryRequest(BaseModel):
    """从目录批量加载 Skills 请求"""
    directory: str
    force_reload: bool = False


class ExecuteWithSkillsRequest(BaseModel):
    """使用 Skills 执行查询请求"""
    query: str
    datasource_id: Optional[int] = None
    use_skills: bool = True
    thread_id: Optional[str] = None


# ============ Routes ============

@router.post("/load/url")
async def load_skill_from_url(request: LoadSkillFromURLRequest):
    """从 URL 加载 Skill"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        result = await manager.load_skill_from_url(
            skill_id=request.skill_id,
            url=request.url,
            force_reload=request.force_reload
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "skill_id": result["skill_id"],
                "loaded": result["loaded"],
                "skill_info": result.get("skill_info")
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 加载 Skill 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load/local")
async def load_skill_from_local(request: LoadSkillFromLocalRequest):
    """从本地加载 Skill"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        result = await manager.load_skill_from_local(
            skill_id=request.skill_id,
            local_path=request.local_path,
            force_reload=request.force_reload
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "skill_id": result["skill_id"],
                "loaded": result["loaded"],
                "skill_info": result.get("skill_info")
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 加载 Skill 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load/directory")
async def load_skills_from_directory(request: LoadSkillsFromDirectoryRequest):
    """从目录批量加载 Skills"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        result = await manager.load_skills_from_directory(
            directory=request.directory,
            force_reload=request.force_reload
        )
        
        return {
            "success": True,
            "message": result["message"],
            "loaded": result["loaded"],
            "failed": result["failed"],
            "skipped": result["skipped"]
        }
    
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 批量加载 Skills 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unload/{skill_id}")
async def unload_skill(skill_id: str):
    """卸载 Skill"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        result = await manager.unload_skill(skill_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "skill_id": skill_id
            }
        else:
            raise HTTPException(status_code=404, detail=result["message"])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 卸载 Skill 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/unload/all")
async def unload_all_skills():
    """卸载所有 Skills"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        result = await manager.unload_all_skills()
        
        return {
            "success": True,
            "message": result["message"],
            "unloaded": result["unloaded"],
            "failed": result["failed"]
        }
    
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 批量卸载失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{skill_id}")
async def get_skill_info(skill_id: str):
    """获取 Skill 信息"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        skill_info = manager.get_skill_info(skill_id)
        
        if skill_info:
            return {
                "success": True,
                "skill_info": skill_info
            }
        else:
            raise HTTPException(status_code=404, detail="Skill 不存在")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 获取 Skill 信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_skills():
    """列出所有已加载的 Skills"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        skills = manager.list_skills()
        
        return {
            "success": True,
            "data": skills,
            "count": len(skills)
        }
    
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 列出 Skills 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_skill_stats():
    """获取 Skill 统计信息"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        stats = manager.get_skill_stats()
        
        return {
            "success": True,
            "data": stats
        }
    
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exists/{skill_id}")
async def check_skill_exists(skill_id: str):
    """检查 Skill 是否存在"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        exists = manager.skill_exists(skill_id)
        
        return {
            "success": True,
            "exists": exists,
            "skill_id": skill_id
        }
    
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 检查 Skill 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_with_skills(request: ExecuteWithSkillsRequest):
    """使用 Skills 执行查询"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        result = await manager.execute_with_skills(
            natural_language=request.query,
            context={"datasource_id": request.datasource_id} if request.datasource_id else {},
            use_skills=request.use_skills,
            thread_id=request.thread_id
        )
        
        return result
    
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 执行查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/info")
async def get_agent_info():
    """获取 Agent 信息（包含 Skill 信息）"""
    try:
        from app.agents.deep_agents.enhanced_manager import get_enhanced_deep_agents_manager
        manager = get_enhanced_deep_agents_manager()
        
        info = manager.get_agent_info()
        
        return {
            "success": True,
            "info": info
        }
    
    except Exception as e:
        logger.error(f"[SkillsAPI] ❌ 获取 Agent 信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "success": True,
        "message": "Skills API 运行正常"
    }
