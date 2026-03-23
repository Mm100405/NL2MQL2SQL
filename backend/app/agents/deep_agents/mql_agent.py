# backend/app/agents/deep_agents/mql_agent.py
"""
基于 Deep Agents 的 MQL Agent 实现
使用 create_deep_agent 替代自定义 Workflow
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

# 加载配置
load_dotenv('.env.deep_agents')

from deepagents import create_deep_agent

from app.agents.deep_agents.tools import create_mql_tools, create_mql_workflow_tool


class DeepMQLAgent:
    """
    基于 Deep Agents 的 MQL Agent
    
    使用 Deep Agents 的 create_deep_agent 创建智能体，
    支持任务规划、工具调用、文件系统等高级特性。
    """
    
    def __init__(
        self,
        db_session: Session,
        query_id: str = None,
        conversation_id: str = None,
        step_callback=None
    ):
        """初始化 Deep Agents MQL Agent
        
        Args:
            db_session: 数据库会话
            query_id: 查询 ID（用于步骤回调）
            conversation_id: 对话 ID（用于保存查询历史）
            step_callback: 步骤回调函数
        """
        self.db_session = db_session
        self.query_id = query_id
        self.conversation_id = conversation_id
        self.step_callback = step_callback
        
        # 加载配置
        self.config = self._load_config()
        
        # 创建 Deep Agent
        self.agent = self._create_agent()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            "enabled": os.getenv("DEEP_AGENTS_ENABLED", "false").lower() == "true",
            "model": os.getenv("DEEP_AGENTS_MODEL", "openai:gpt-4"),
            "system_prompt": os.getenv(
                "DEEP_AGENTS_SYSTEM_PROMPT",
                "你是一位专业的数据分析专家，擅长将自然语言转换为 MQL 并执行查询。"
            ),
            "enable_planning": os.getenv("DEEP_AGENTS_ENABLE_PLANNING", "true").lower() == "true",
            "enable_file_system": os.getenv("DEEP_AGENTS_ENABLE_FILE_SYSTEM", "false").lower() == "true",
            "file_system_root": os.getenv("DEEP_AGENTS_FILE_SYSTEM_ROOT", "./data/skills"),
            "max_tokens": int(os.getenv("DEEP_AGENTS_MAX_TOKENS", "4000")),
            "temperature": float(os.getenv("DEEP_AGENTS_TEMPERATURE", "0.7")),
            "auto_fallback": os.getenv("DEEP_AGENTS_AUTO_FALLBACK", "true").lower() == "true"
        }
    
    def _create_agent(self):
        """创建 Deep Agent"""
        # 创建工具
        tools = create_mql_tools(self.db_session, self.step_callback)
        workflow_tool = create_mql_workflow_tool(self.db_session, self.step_callback)
        
        # 所有工具
        all_tools = tools + workflow_tool
        
        # 创建 Deep Agent
        agent = create_deep_agent(
            model=self.config["model"],
            system_prompt=self.config["system_prompt"],
            tools=all_tools,
            enable_planning=self.config["enable_planning"],
            enable_file_system=self.config["enable_file_system"],
            file_system_root=self.config["file_system_root"] if self.config["enable_file_system"] else None
        )
        
        return agent
    
    async def execute_query(
        self,
        natural_language: str,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """执行查询（使用 Deep Agents）
        
        Args:
            natural_language: 自然语言查询
            context: 上下文信息（可选）
            max_retries: MQL 生成最大重试次数（Deep Agents 会自动重试）
        
        Returns:
            查询结果字典
        """
        # 构建输入消息
        input_message = {
            "role": "user",
            "content": f"""
请执行以下查询任务：

自然语言查询：{natural_language}

上下文信息：{context or {}}

请使用 execute_mql_workflow 工具完成整个查询流程。
"""
        }
        
        # 执行 Deep Agent
        try:
            result = await self.agent.ainvoke({
                "messages": [input_message]
            })
            
            # 提取结果
            messages = result.get("messages", [])
            
            # 从最后一条消息中提取结果
            if messages:
                last_message = messages[-1]
                content = last_message.get("content", "")
                
                # 尝试解析 JSON 结果
                import json
                try:
                    # 如果内容是 JSON 字符串，解析它
                    if isinstance(content, str):
                        # 查找 JSON 块
                        if "```json" in content:
                            json_start = content.find("```json") + 7
                            json_end = content.find("```", json_start)
                            json_str = content[json_start:json_end].strip()
                            parsed_result = json.loads(json_str)
                        else:
                            # 尝试直接解析
                            parsed_result = json.loads(content)
                        
                        return {
                            "natural_language": natural_language,
                            "mql": parsed_result.get("mql"),
                            "sql": parsed_result.get("sql"),
                            "result": parsed_result.get("query_result"),
                            "interpretation": parsed_result.get("interpretation"),
                            "insights": parsed_result.get("insights", []),
                            "visualization": parsed_result.get("visualization_suggestion"),
                            "steps": parsed_result.get("steps", []),
                            "query_id": parsed_result.get("query_id"),
                            "mql_attempts": parsed_result.get("mql_attempts", 0)
                        }
                except (json.JSONDecodeError, AttributeError):
                    pass
                
                # 如果无法解析 JSON，返回原始消息
                return {
                    "natural_language": natural_language,
                    "error": "无法解析 Deep Agents 响应",
                    "raw_response": content
                }
            
            return {
                "natural_language": natural_language,
                "error": "Deep Agents 未返回有效响应"
            }
        
        except Exception as e:
            # 如果启用自动回退，使用传统引擎
            if self.config["auto_fallback"]:
                print(f"[DeepMQLAgent] Deep Agents 失败，回退到传统引擎: {str(e)}")
                from app.agents.mql_agent import MQLAgent
                fallback_agent = MQLAgent(
                    self.db_session,
                    query_id=self.query_id,
                    conversation_id=self.conversation_id
                )
                return await fallback_agent.execute_query(natural_language, context, max_retries)
            
            # 否则抛出异常
            raise Exception(f"Deep Agents 执行失败: {str(e)}")
    
    async def explain_result(
        self,
        query_result: Dict[str, Any],
        natural_language: str
    ) -> Dict[str, Any]:
        """解释查询结果
        
        Args:
            query_result: 查询结果
            natural_language: 原始查询
        
        Returns:
            解释结果
        """
        input_message = {
            "role": "user",
            "content": f"""
请解释以下查询结果：

原始查询：{natural_language}

查询结果：
{query_result}

请使用 interpret_result 工具生成详细的解释和洞察。
"""
        }
        
        result = await self.agent.ainvoke({
            "messages": [input_message]
        })
        
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            return {
                "interpretation": last_message.get("content", ""),
                "insights": []
            }
        
        return {
            "interpretation": "无法生成解释",
            "insights": []
        }
