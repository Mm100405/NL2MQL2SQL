# backend/app/agents/nodes/base_node.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from langchain_core.runnables import RunnableConfig
from datetime import datetime

from app.agents.state.query_state import QueryState


class BaseNode(ABC):
    """节点基类
    
    所有节点都需要继承此基类。节点负责：
    1. 状态管理
    2. 流程编排
    3. 错误处理
    4. 步骤记录
    
    节点通过调用Skill来执行具体的业务逻辑。
    """
    
    node_name: str
    description: str
    step_callback = None  # 步骤回调函数
    
    def __init__(self, db: Session = None, step_callback = None):
        """初始化节点"""
        self.db = db
        self.step_callback = step_callback

    @abstractmethod
    async def __call__(
        self,
        state: QueryState,
        config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """执行节点逻辑

        Args:
            state: 当前查询状态
            config: 配置信息
        
        Returns:
            需要更新的状态字段字典
        """
        pass
    
    def add_step(
        self,
        state: QueryState,
        title: str,
        content: str,
        status: str = "success",
        extra: Optional[Dict[str, Any]] = None
    ) -> None:
        """添加执行步骤（用于前端展示）"""
        if "steps" not in state:
            state["steps"] = []

        step = {
            "title": title,
            "content": content,
            "status": status,
            "node": self.node_name,
            "timestamp": datetime.now().isoformat()
        }

        # 添加额外信息（MQL、SQL、洞察等）
        if extra:
            step["extra"] = extra

        state["steps"].append(step)

        # 调用回调函数（用于流式输出）
        if self.step_callback:
            self.step_callback(step)
    
    def __repr__(self) -> str:
        """返回节点的字符串表示"""
        return f"<{self.__class__.__name__}(name='{self.node_name}')>"
