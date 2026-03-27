from sqlalchemy import Column, String, Text, JSON, DateTime, Boolean
from datetime import datetime
import uuid

from app.database import Base


class ModelConfig(Base):
    __tablename__ = "model_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)  # openai, anthropic, azure, deepseek, qwen, zhipu, moonshot, ollama, mistral, gemini, custom 等（通过 LiteLLM 统一调用）
    model_name = Column(String(255), nullable=False)  # gpt-4, gpt-3.5-turbo, llama3, etc.
    api_key = Column(Text, nullable=True)  # Encrypted API key
    api_base = Column(String(500), nullable=True)  # Custom API endpoint
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    config_params = Column(JSON, nullable=True)  # {temperature, max_tokens, ...}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self, include_key: bool = False):
        result = {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "model_name": self.model_name,
            "api_base": self.api_base,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "config_params": self.config_params or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_key and self.api_key:
            result["api_key"] = "***"  # Mask the key
        return result
