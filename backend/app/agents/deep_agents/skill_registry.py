"""
外部 Skill 注册表

基于 StoreBackend 的动态 Skill 管理系统
支持运行时加载、卸载、查询大量外部标准 Skills
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from urllib.request import urlopen

from langgraph.store.memory import InMemoryStore

# PostgresStore 是可选依赖，仅在需要时导入
try:
    from langgraph.store.postgres import PostgresStore
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

from deepagents.backends import StoreBackend
from deepagents.backends.utils import create_file_data


logger = logging.getLogger(__name__)


class SkillInfo:
    """Skill 信息对象"""
    
    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str,
        source: str,
        loaded_at: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.source = source  # "local" 或 "url"
        self.loaded_at = loaded_at
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "loaded_at": self.loaded_at.isoformat(),
            "metadata": self.metadata
        }


class SkillRegistry:
    """Skill 注册表
    
    负责管理外部标准 Skills 的生命周期：
    1. 加载 Skills（从本地文件或 URL）
    2. 卸载 Skills
    3. 查询 Skills
    4. 创建带 Skills 的 Agent
    """
    
    def __init__(
        self,
        store: Optional[Any] = None,
        backend_factory: Optional[callable] = None
    ):
        """初始化 Skill 注册表
        
        Args:
            store: LangGraph Store（默认使用 InMemoryStore）
            backend_factory: Backend 工厂函数（默认使用 StoreBackend）
        """
        # 初始化 Store
        self.store = store or InMemoryStore()
        
        # Backend 工厂
        self.backend_factory = backend_factory or (lambda rt: StoreBackend(rt))
        
        # Skill 信息缓存（内存）
        self._skills_info: Dict[str, SkillInfo] = {}
        
        # 加载的 Skill 路径集合
        self._loaded_skill_paths: Set[str] = set()
        
        logger.info("[SkillRegistry] Skill 注册表初始化完成")
    
    # ==================== 核心方法：加载/卸载 ====================
    
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
        try:
            # 检查是否已加载
            if skill_id in self._skills_info and not force_reload:
                logger.warning(f"[SkillRegistry] Skill 已存在: {skill_id}")
                return {
                    "success": True,
                    "message": "Skill 已存在",
                    "skill_id": skill_id,
                    "loaded": False
                }
            
            # 从 URL 下载 Skill 内容
            logger.info(f"[SkillRegistry] 从 URL 加载 Skill: {skill_id}")
            with urlopen(url) as response:
                skill_content = response.read().decode('utf-8')
            
            # 验证 Skill 内容
            skill_info = self._parse_skill_md(skill_content)
            
            # 存储到 Store
            skill_key = f"/skills/{skill_id}/SKILL.md"
            self.store.put(
                namespace=("filesystem",),
                key=skill_key,
                value=create_file_data(skill_content)
            )
            
            # 缓存 Skill 信息
            self._skills_info[skill_id] = SkillInfo(
                skill_id=skill_id,
                name=skill_info["name"],
                description=skill_info["description"],
                source="url",
                loaded_at=datetime.now(),
                metadata=skill_info.get("metadata", {})
            )
            
            # 添加到已加载路径集合
            self._loaded_skill_paths.add(f"/skills/{skill_id}/")
            
            logger.info(f"[SkillRegistry] ✅ Skill 加载成功: {skill_id}")
            
            return {
                "success": True,
                "message": "Skill 加载成功",
                "skill_id": skill_id,
                "loaded": True,
                "skill_info": skill_info
            }
            
        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ Skill 加载失败 ({skill_id}): {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Skill 加载失败: {str(e)}",
                "skill_id": skill_id,
                "loaded": False
            }
    
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
        try:
            # 检查是否已加载
            if skill_id in self._skills_info and not force_reload:
                logger.warning(f"[SkillRegistry] Skill 已存在: {skill_id}")
                return {
                    "success": True,
                    "message": "Skill 已存在",
                    "skill_id": skill_id,
                    "loaded": False
                }
            
            # 检查文件是否存在
            if not os.path.exists(local_path):
                logger.error(f"[SkillRegistry] 文件不存在: {local_path}")
                return {
                    "success": False,
                    "message": f"文件不存在: {local_path}",
                    "skill_id": skill_id,
                    "loaded": False
                }
            
            # 读取 Skill 内容
            logger.info(f"[SkillRegistry] 从本地加载 Skill: {skill_id}")
            with open(local_path, 'r', encoding='utf-8') as f:
                skill_content = f.read()
            
            # 验证 Skill 内容
            skill_info = self._parse_skill_md(skill_content)
            
            # 存储到 Store
            skill_key = f"/skills/{skill_id}/SKILL.md"
            self.store.put(
                namespace=("filesystem",),
                key=skill_key,
                value=create_file_data(skill_content)
            )
            
            # 缓存 Skill 信息
            self._skills_info[skill_id] = SkillInfo(
                skill_id=skill_id,
                name=skill_info["name"],
                description=skill_info["description"],
                source="local",
                loaded_at=datetime.now(),
                metadata=skill_info.get("metadata", {})
            )
            
            # 添加到已加载路径集合
            self._loaded_skill_paths.add(f"/skills/{skill_id}/")
            
            logger.info(f"[SkillRegistry] ✅ Skill 加载成功: {skill_id}")
            
            return {
                "success": True,
                "message": "Skill 加载成功",
                "skill_id": skill_id,
                "loaded": True,
                "skill_info": skill_info
            }
            
        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ Skill 加载失败 ({skill_id}): {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Skill 加载失败: {str(e)}",
                "skill_id": skill_id,
                "loaded": False
            }
    
    async def load_skills_from_directory(
        self,
        directory: str,
        force_reload: bool = False
    ) -> Dict[str, Any]:
        """从目录批量加载 Skills
        
        Args:
            directory: Skills 目录（包含多个 Skill 子目录）
            force_reload: 是否强制重新加载
        
        Returns:
            加载结果
        """
        try:
            results = {
                "success": True,
                "message": "",
                "loaded": [],
                "failed": [],
                "skipped": []
            }
            
            # 遍历目录
            for skill_name in os.listdir(directory):
                skill_path = os.path.join(directory, skill_name)
                
                # 只处理目录
                if not os.path.isdir(skill_path):
                    continue
                
                # 检查 SKILL.md
                skill_md = os.path.join(skill_path, "SKILL.md")
                if not os.path.exists(skill_md):
                    logger.warning(f"[SkillRegistry] SKILL.md 不存在: {skill_name}")
                    continue
                
                # 加载 Skill
                result = await self.load_skill_from_local(
                    skill_id=skill_name,
                    local_path=skill_md,
                    force_reload=force_reload
                )
                
                if result["success"] and result["loaded"]:
                    results["loaded"].append(skill_name)
                elif result["success"] and not result["loaded"]:
                    results["skipped"].append(skill_name)
                else:
                    results["failed"].append(skill_name)
            
            results["message"] = (
                f"加载完成: {len(results['loaded'])} 成功, "
                f"{len(results['skipped'])} 跳过, "
                f"{len(results['failed'])} 失败"
            )
            
            logger.info(f"[SkillRegistry] {results['message']}")
            
            return results
            
        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 批量加载失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"批量加载失败: {str(e)}",
                "loaded": [],
                "failed": [],
                "skipped": []
            }
    
    async def unload_skill(self, skill_id: str) -> Dict[str, Any]:
        """卸载 Skill
        
        Args:
            skill_id: Skill 唯一标识符
        
        Returns:
            卸载结果
        """
        try:
            # 检查是否存在
            if skill_id not in self._skills_info:
                logger.warning(f"[SkillRegistry] Skill 不存在: {skill_id}")
                return {
                    "success": False,
                    "message": "Skill 不存在",
                    "skill_id": skill_id
                }
            
            # 从 Store 删除
            skill_key = f"/skills/{skill_id}/SKILL.md"
            self.store.delete(
                namespace=("filesystem",),
                key=skill_key
            )
            
            # 从缓存删除
            del self._skills_info[skill_id]
            self._loaded_skill_paths.discard(f"/skills/{skill_id}/")
            
            logger.info(f"[SkillRegistry] ✅ Skill 卸载成功: {skill_id}")
            
            return {
                "success": True,
                "message": "Skill 卸载成功",
                "skill_id": skill_id
            }
            
        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ Skill 卸载失败 ({skill_id}): {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Skill 卸载失败: {str(e)}",
                "skill_id": skill_id
            }
    
    async def unload_all_skills(self) -> Dict[str, Any]:
        """卸载所有 Skills
        
        Returns:
            卸载结果
        """
        try:
            skill_ids = list(self._skills_info.keys())
            results = {
                "success": True,
                "message": "",
                "unloaded": [],
                "failed": []
            }
            
            for skill_id in skill_ids:
                result = await self.unload_skill(skill_id)
                if result["success"]:
                    results["unloaded"].append(skill_id)
                else:
                    results["failed"].append(skill_id)
            
            results["message"] = (
                f"卸载完成: {len(results['unloaded'])} 成功, "
                f"{len(results['failed'])} 失败"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ 批量卸载失败: {e}")
            return {
                "success": False,
                "message": f"批量卸载失败: {str(e)}",
                "unloaded": [],
                "failed": []
            }
    
    # ==================== 查询方法 ====================
    
    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取 Skill 信息
        
        Args:
            skill_id: Skill 唯一标识符
        
        Returns:
            Skill 信息（不存在返回 None）
        """
        skill_info = self._skills_info.get(skill_id)
        return skill_info.to_dict() if skill_info else None
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有已加载的 Skills
        
        Returns:
            Skill 信息列表
        """
        return [
            skill_info.to_dict()
            for skill_info in self._skills_info.values()
        ]
    
    def get_skill_paths(self) -> List[str]:
        """获取所有已加载 Skill 的路径
        
        Returns:
            Skill 路径列表（用于创建 Agent）
        """
        return list(self._loaded_skill_paths)
    
    def count_skills(self) -> int:
        """获取已加载 Skills 数量
        
        Returns:
            Skills 数量
        """
        return len(self._skills_info)
    
    def skill_exists(self, skill_id: str) -> bool:
        """检查 Skill 是否存在
        
        Args:
            skill_id: Skill 唯一标识符
        
        Returns:
            是否存在
        """
        return skill_id in self._skills_info
    
    # ==================== Agent 创建 ====================
    
    def create_agent(self, checkpointer=None):
        """创建带已加载 Skills 的 Agent
        
        Args:
            checkpointer: Checkpointer（可选）
        
        Returns:
            Deep Agent 实例
        """
        try:
            from deepagents import create_deep_agent
            
            # 获取已加载的 Skill 路径
            skill_paths = self.get_skill_paths()
            
            logger.info(f"[SkillRegistry] 创建 Agent，已加载 {len(skill_paths)} 个 Skills")
            
            # 创建 Agent
            agent = create_deep_agent(
                backend=self.backend_factory,
                store=self.store,
                skills=skill_paths,
                checkpointer=checkpointer
            )
            
            logger.info(f"[SkillRegistry] ✅ Agent 创建成功")
            
            return agent
            
        except Exception as e:
            logger.error(f"[SkillRegistry] ❌ Agent 创建失败: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    # ==================== 辅助方法 ====================
    
    def _parse_skill_md(self, content: str) -> Dict[str, Any]:
        """解析 SKILL.md 文件
        
        Args:
            content: SKILL.md 文件内容
        
        Returns:
            解析后的 Skill 信息
        """
        # 提取 YAML 头部
        lines = content.split('\n')
        yaml_lines = []
        in_yaml = False
        
        for line in lines:
            if line.strip() == '---':
                if not in_yaml:
                    in_yaml = True
                else:
                    break
            elif in_yaml:
                yaml_lines.append(line)
        
        yaml_content = '\n'.join(yaml_lines)
        metadata = yaml.safe_load(yaml_content) if yaml_content else {}
        
        return {
            "name": metadata.get("name", "unknown"),
            "description": metadata.get("description", ""),
            "license": metadata.get("license", ""),
            "compatibility": metadata.get("compatibility", ""),
            "metadata": metadata.get("metadata", {}),
            "allowed-tools": metadata.get("allowed-tools", [])
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total": len(self._skills_info),
            "local_skills": sum(
                1 for s in self._skills_info.values() if s.source == "local"
            ),
            "url_skills": sum(
                1 for s in self._skills_info.values() if s.source == "url"
            ),
            "skill_ids": list(self._skills_info.keys()),
            "loaded_at": [
                s.loaded_at.isoformat()
                for s in self._skills_info.values()
            ]
        }


# ============== 全局注册表实例 ==============

_global_registry: Optional[SkillRegistry] = None


def get_skill_registry(store: Optional[Any] = None) -> SkillRegistry:
    """获取全局 Skill 注册表实例
    
    Args:
        store: LangGraph Store（可选）
    
    Returns:
        Skill 注册表实例
    """
    global _global_registry
    
    if _global_registry is None or store is not None:
        _global_registry = SkillRegistry(store=store)
    
    return _global_registry
