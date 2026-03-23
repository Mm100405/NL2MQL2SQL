"""
增强版 Deep Agents 管理器

集成 SkillRegistry，支持动态加载/卸载外部 Skills
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from langgraph.checkpoint.memory import MemorySaver

from app.agents.deep_agents.manager import DeepAgentsManager
from app.agents.deep_agents.skill_registry import SkillRegistry, get_skill_registry


logger = logging.getLogger(__name__)


class EnhancedDeepAgentsManager:
    """增强版 Deep Agents 管理器
    
    集成 SkillRegistry，支持：
    1. 动态加载/卸载外部 Skills
    2. 查询已加载的 Skills
    3. 创建带 Skills 的 Agent
    4. 与问数流程集成
    """
    
    def __init__(
        self,
        db_session: Optional[Session] = None,
        skill_registry: Optional[SkillRegistry] = None
    ):
        """初始化增强版管理器
        
        Args:
            db_session: 数据库会话（可选）
            skill_registry: Skill 注册表（可选，默认使用全局实例）
        """
        self.db_session = db_session
        self.skill_registry = skill_registry or get_skill_registry()
        
        # 基础管理器
        self.base_manager = DeepAgentsManager(
            db_session=db_session
        )
        
        logger.info("[EnhancedDeepAgentsManager] 增强版管理器初始化完成")
    
    # ==================== Skill 管理方法 ====================
    
    async def load_skill_from_url(
        self,
        skill_id: str,
        url: str,
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """从 URL 加载 Skill
        
        Args:
            skill_id: Skill 唯一标识符
            url: Skill 文件 URL
            force_reload: 是否强制重新加载
        
        Returns:
            加载结果
        """
        return await self.skill_registry.load_skill_from_url(
            skill_id=skill_id,
            url=url,
            force_reload=force_reload
        )
    
    async def load_skill_from_local(
        self,
        skill_id: str,
        local_path: str,
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """从本地文件加载 Skill
        
        Args:
            skill_id: Skill 唯一标识符
            local_path: 本地 SKILL.md 文件路径
            force_reload: 是否强制重新加载
        
        Returns:
            加载结果
        """
        return await self.skill_registry.load_skill_from_local(
            skill_id=skill_id,
            local_path=local_path,
            force_reload=force_reload
        )
    
    async def load_skills_from_directory(
        self,
        directory: str,
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """从目录批量加载 Skills
        
        Args:
            directory: Skills 目录
            force_reload: 是否强制重新加载
        
        Returns:
            加载结果
        """
        return await self.skill_registry.load_skills_from_directory(
            directory=directory,
            force_reload=force_reload
        )
    
    async def unload_skill(self, skill_id: str) -> Dict[str, Any]:
        """卸载 Skill
        
        Args:
            skill_id: Skill 唯一标识符
        
        Returns:
            卸载结果
        """
        return await self.skill_registry.unload_skill(skill_id)
    
    async def unload_all_skills(self) -> Dict[str, Any]:
        """卸载所有 Skills
        
        Returns:
            卸载结果
        """
        return await self.skill_registry.unload_all_skills()
    
    # ==================== Skill 查询方法 ====================
    
    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取 Skill 信息"""
        return self.skill_registry.get_skill_info(skill_id)
    
    def list_skills(self) -> list:
        """列出所有已加载的 Skills"""
        return self.skill_registry.list_skills()
    
    def count_skills(self) -> int:
        """获取已加载 Skills 数量"""
        return self.skill_registry.count_skills()
    
    def skill_exists(self, skill_id: str) -> bool:
        """检查 Skill 是否存在"""
        return self.skill_registry.skill_exists(skill_id)
    
    def get_skill_stats(self) -> Dict[str, Any]:
        """获取 Skill 统计信息"""
        return self.skill_registry.get_stats()
    
    # ==================== Agent 创建与执行 ====================
    
    def create_agent_with_skills(self, checkpointer=None):
        """创建带 Skills 的 Agent
        
        Args:
            checkpointer: Checkpointer（可选）
        
        Returns:
            Deep Agent 实例
        """
        return self.skill_registry.create_agent(checkpointer=checkpointer)
    
    async def execute_with_skills(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        use_skills: bool = True,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """执行查询（使用已加载的 Skills）
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: 最大重试次数
            use_skills: 是否使用已加载的 Skills
            thread_id: 会话 ID（可选）
        
        Returns:
            查询结果
        """
        try:
            # 检查是否使用 Skills
            if use_skills and self.skill_registry.count_skills() > 0:
                logger.info(f"[EnhancedDeepAgentsManager] 使用 Skills 执行查询")
                
                # 创建带 Skills 的 Agent
                agent = self.create_agent_with_skills()
                
                # 执行查询
                config = {}
                if thread_id:
                    config["configurable"] = {"thread_id": thread_id}
                
                result = await agent.ainvoke(
                    {
                        "messages": [{"role": "user", "content": natural_language}],
                        "natural_language": natural_language,
                        "context": context or {}
                    },
                    config=config
                )
                
                return {
                    "success": True,
                    "result": result,
                    "used_skills": True,
                    "skills_count": self.skill_registry.count_skills(),
                    "skills": self.list_skills()
                }
            else:
                # 使用基础管理器执行
                logger.info(f"[EnhancedDeepAgentsManager] 使用基础工具执行查询")
                return await self.base_manager.execute(
                    natural_language=natural_language,
                    context=context,
                    max_retries=max_retries
                )
        
        except Exception as e:
            logger.error(f"[EnhancedDeepAgentsManager] 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "used_skills": False
            }
    
    async def execute_stream_with_skills(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        use_skills: bool = True,
        step_callback: Optional[callable] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """流式执行查询（使用已加载的 Skills，带步骤回调）
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: 最大重试次数
            use_skills: 是否使用已加载的 Skills
            step_callback: 步骤回调函数（可选）
            thread_id: 会话 ID（可选）
        
        Returns:
            查询结果
        """
        try:
            # 检查是否使用 Skills
            if use_skills and self.skill_registry.count_skills() > 0:
                logger.info(f"[EnhancedDeepAgentsManager] 使用 Skills 流式执行查询")
                
                # 创建带 Skills 的 Agent
                agent = self.create_agent_with_skills()
                
                # 执行查询（流式）
                config = {}
                if thread_id:
                    config["configurable"] = {"thread_id": thread_id}
                
                result = await agent.ainvoke(
                    {
                        "messages": [{"role": "user", "content": natural_language}],
                        "natural_language": natural_language,
                        "context": context or {}
                    },
                    config=config
                )
                
                return {
                    "success": True,
                    "result": result,
                    "used_skills": True,
                    "skills_count": self.skill_registry.count_skills(),
                    "skills": self.list_skills()
                }
            else:
                # 使用基础管理器流式执行
                logger.info(f"[EnhancedDeepAgentsManager] 使用基础工具流式执行查询")
                return await self.base_manager.execute_stream(
                    natural_language=natural_language,
                    context=context,
                    max_retries=max_retries,
                    step_callback=step_callback
                )
        
        except Exception as e:
            logger.error(f"[EnhancedDeepAgentsManager] 流式执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "used_skills": False
            }
        """执行查询（使用已加载的 Skills）
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: 最大重试次数
            use_skills: 是否使用已加载的 Skills
            thread_id: 会话 ID（可选）
        
        Returns:
            查询结果
        """
        try:
            # 检查是否使用 Skills
            if use_skills and self.skill_registry.count_skills() > 0:
                logger.info(f"[EnhancedDeepAgentsManager] 使用 Skills 执行查询")
                
                # 创建带 Skills 的 Agent
                agent = self.create_agent_with_skills()
                
                # 执行查询
                config = {}
                if thread_id:
                    config["configurable"] = {"thread_id": thread_id}
                
                result = await agent.ainvoke(
                    {
                        "messages": [{"role": "user", "content": natural_language}],
                        "natural_language": natural_language,
                        "context": context or {}
                    },
                    config=config
                )
                
                return {
                    "success": True,
                    "result": result,
                    "used_skills": True,
                    "skills_count": self.skill_registry.count_skills(),
                    "skills": self.list_skills()
                }
            else:
                # 使用基础管理器执行
                logger.info(f"[EnhancedDeepAgentsManager] 使用基础工具执行查询")
                return await self.base_manager.execute(
                    natural_language=natural_language,
                    context=context,
                    max_retries=max_retries
                )
        
        except Exception as e:
            logger.error(f"[EnhancedDeepAgentsManager] 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "used_skills": False
            }
    
    async def execute_stream_with_skills(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        use_skills: bool = True,
        step_callback: Optional[callable] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """流式执行查询（使用已加载的 Skills）
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: 最大重试次数
            use_skills: 是否使用已加载的 Skills
            step_callback: 步骤回调函数（可选）
            thread_id: 会话 ID（可选）
        
        Returns:
            查询结果
        """
        # 如果使用 Skills，使用带 Skills 的 Agent
        if use_skills and self.skill_registry.count_skills() > 0:
            logger.info(f"[EnhancedDeepAgentsManager] 使用 Skills 流式执行")
            
            agent = self.create_agent_with_skills()
            
            # 执行流式查询
            config = {}
            if thread_id:
                config["configurable"] = {"thread_id": thread_id}
            
            result = await agent.ainvoke(
                {
                    "messages": [{"role": "user", "content": natural_language}],
                    "natural_language": natural_language,
                    "context": context or {}
                },
                config=config
            )
            
            return {
                "success": True,
                "result": result,
                "used_skills": True,
                "skills_count": self.skill_registry.count_skills()
            }
        else:
            # 使用基础管理器
            logger.info(f"[EnhancedDeepAgentsManager] 使用基础工具流式执行")
            return await self.base_manager.execute_stream(
                natural_language=natural_language,
                context=context,
                max_retries=max_retries,
                step_callback=step_callback
            )
    
    # ==================== 信息获取 ====================
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取 Agent 信息（包含 Skill 信息）"""
        base_info = self.base_manager.get_agent_info()
        
        base_info.update({
            "skills_enabled": self.skill_registry.count_skills() > 0,
            "skills_count": self.skill_registry.count_skills(),
            "skills_list": self.list_skills(),
            "skills_stats": self.get_skill_stats()
        })
        
        return base_info


# ============== 全局管理器实例 ==============

_global_enhanced_manager: Optional[EnhancedDeepAgentsManager] = None


def get_enhanced_deep_agents_manager(
    db_session: Optional[Session] = None,
    skill_registry: Optional[SkillRegistry] = None
) -> EnhancedDeepAgentsManager:
    """获取全局增强版 Deep Agents 管理器实例
    
    Args:
        db_session: 数据库会话（可选）
        skill_registry: Skill 注册表（可选）
    
    Returns:
        增强版 Deep Agents 管理器实例
    """
    global _global_enhanced_manager
    
    if _global_enhanced_manager is None or db_session or skill_registry:
        _global_enhanced_manager = EnhancedDeepAgentsManager(
            db_session=db_session,
            skill_registry=skill_registry
        )
    
    return _global_enhanced_manager
