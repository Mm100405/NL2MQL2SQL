from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "NL2MQL2SQL"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8011
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/nlqdb"
    
    # CORS
    # 注意：应用启动时会自动添加当前内网 IP 到允许列表
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "*"]
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "your-encryption-key-32bytes-long!"
    
    # LLM Default Settings
    DEFAULT_LLM_TEMPERATURE: float = 0.7
    DEFAULT_LLM_MAX_TOKENS: int = 4096
    
    # Query Settings
    QUERY_TIMEOUT: int = 30  # seconds
    MAX_RESULT_ROWS: int = 10000
    
    # MQL Engine V2
    MQL_ENGINE_V2: bool = True  # True=sqlglot AST引擎, False=旧字符串拼接引擎
    MQL_CACHE_ENABLED: bool = True
    MQL_CACHE_MAX_SIZE: int = 256
    MQL_CACHE_TTL: int = 300  # seconds
    MQL_OPTIMIZER_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # 允许 .env 文件中有额外字段，提高部署兼容性


settings = Settings()
