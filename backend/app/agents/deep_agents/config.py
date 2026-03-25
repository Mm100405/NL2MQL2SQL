# backend/app/agents/deep_agents/config.py

"""
Deep Agents 配置模块

基于 LangChain Deep Agents 规范的配置管理
参考：https://docs.langchain.com/oss/python/deepagents/overview
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# 加载 Deep Agents 配置文件
load_dotenv('.env.deep_agents')


class DeepAgentsConfig(BaseSettings):
    """Deep Agents 配置
    
    基于 Deep Agents 文档的标准配置项
    
    Attributes:
        enabled: 是否启用 Deep Agents
        model: 使用的模型（格式：provider:model，如 openai:gpt-4）
        system_prompt: 系统提示词
        enable_planning: 是否启用任务规划
        enable_file_system: 是否启用文件系统
        file_system_root: 文件系统根目录
        max_tokens: 最大 Token 限制
        temperature: 生成温度
        auto_fallback: 是否自动回退
        enable_memory: 是否启用记忆
        memory_type: 记忆类型（buffer、summary、vector）
    """
    
    # 基础配置
    enabled: bool = Field(
        default=False,
        description="是否启用 Deep Agents（默认 false，测试完成后改为 true）"
    )
    
    # 模型配置
    model: str = Field(
        default="openai:gpt-4",
        description="使用的模型（支持 openai:gpt-4, anthropic:claude-3-opus, deepseek:deepseek-chat 等）"
    )
    
    # 系统提示词
    system_prompt: str = Field(
        default="你是一位专业的数据分析专家，擅长将自然语言转换为 MQL（Metrics Query Language）并执行查询。你能够理解业务指标和维度，生成准确的查询，并提供深入的数据洞察。",
        description="系统提示词"
    )
    
    # 任务规划配置
    enable_planning: bool = Field(
        default=True,
        description="是否启用任务规划（Deep Agents 的核心能力）"
    )
    
    # 文件系统配置
    enable_file_system: bool = Field(
        default=False,
        description="是否启用文件系统（支持读写 Markdown 文件）"
    )
    
    file_system_root: str = Field(
        default="./data/skills",
        description="文件系统根目录"
    )
    
    # 模型参数
    max_tokens: int = Field(
        default=4000,
        description="最大 Token 限制"
    )
    
    temperature: float = Field(
        default=0.7,
        description="生成温度"
    )
    
    # 回退机制
    auto_fallback: bool = Field(
        default=True,
        description="如果 Deep Agents 失败，是否自动回退到传统引擎"
    )
    
    # 记忆配置
    enable_memory: bool = Field(
        default=True,
        description="是否启用记忆（Deep Agents 的核心能力）"
    )
    
    memory_type: str = Field(
        default="buffer",
        description="记忆类型（buffer、summary、vector）"
    )
    
    # 功能开关配置
    enable_intent_analysis: bool = Field(
        default=True,
        description="是否启用意图识别"
    )
    
    enable_insight_analysis: bool = Field(
        default=True,
        description="是否启用洞察分析"
    )
    
    # 可观测性配置
    enable_tracing: bool = Field(
        default=False,
        description="是否启用 LangSmith 追踪"
    )
    
    langsmith_api_key: Optional[str] = Field(
        default=None,
        description="LangSmith API Key"
    )
    
    class Config:
        env_file = ".env.deep_agents"
        env_prefix = "DEEP_AGENTS_"
        case_sensitive = False
    
    def get_model_provider(self) -> str:
        """获取模型提供商"""
        return self.model.split(":")[0] if ":" in self.model else "openai"
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.model.split(":")[1] if ":" in self.model else self.model
    
    def to_deep_agents_config(self) -> dict:
        """转换为 Deep Agents 配置字典
        
        参考：https://docs.langchain.com/oss/python/deepagents/quickstart
        """
        return {
            "model": self.model,
            "system_prompt": self.system_prompt,
            "enable_planning": self.enable_planning,
            "enable_file_system": self.enable_file_system,
            "file_system_root": self.file_system_root,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "enable_memory": self.enable_memory,
            "memory_type": self.memory_type,
        }


# 全局配置实例
deep_agents_config = DeepAgentsConfig()
