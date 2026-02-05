from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "NL2MQL2SQL"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:123456@localhost:3306/nlqdb"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://192.168.42.208:5173", "http://0.0.0.0:5173", "*"]
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ENCRYPTION_KEY: str = "your-encryption-key-32bytes-long!"
    
    # LLM Default Settings
    DEFAULT_LLM_TEMPERATURE: float = 0.7
    DEFAULT_LLM_MAX_TOKENS: int = 4096
    
    # Query Settings
    QUERY_TIMEOUT: int = 30  # seconds
    MAX_RESULT_ROWS: int = 10000
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
