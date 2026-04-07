# ⚠️ 关键：必须在所有其他导入之前加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 配置日志系统（必须在其他导入之前）
from app.core.logging_config import setup_logging
setup_logging()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import socket
import os

# 创建 logger
logger = logging.getLogger(__name__)

from app.config import settings
from app.database import engine, Base
from app.api.v1 import query, semantic, settings as settings_api, air, can, big, views, dictionaries, data_format, agent, skills


def get_local_ip():
    """获取本机局域网 IP 地址"""
    try:
        # 创建一个 UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 尝试连接到一个外部地址（不会实际发送数据）
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 备用方案：获取主机名并解析
        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception:
            return None


def get_cors_origins():
    """获取 CORS 允许的源地址列表（动态添加当前内网 IP）"""
    origins = settings.CORS_ORIGINS.copy()
    
    # 动态添加当前内网 IP
    local_ip = get_local_ip()
    if local_ip and local_ip not in origins:
        origins.append(f"http://{local_ip}:5173")
        logger.info(f"动态添加内网 IP: http://{local_ip}:5173")
    
    return origins


app = FastAPI(
    title="NL2MQL2SQL API",
    description="智能问数系统 - 自然语言转MQL转SQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"全局异常: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


@app.on_event("startup")
async def startup_event():
    # ⚠️ 关键：uvicorn 启动后覆盖了日志配置，必须在此重新应用
    setup_logging()

    logger.info("=" * 60)
    logger.info("Application startup initiated")
    logger.info("=" * 60)
    
    # 显示 CORS 配置
    cors_origins = get_cors_origins()
    logger.info("CORS 允许的源地址：")
    for origin in cors_origins:
        logger.info(f"  - {origin}")
    
    # 自动创建数据库（如果不存在）
    from urllib.parse import urlparse, urlunparse
    from sqlalchemy import create_engine, text
    
    try:
        logger.info("Checking database existence...")
        # 解析数据库 URL
        parsed_url = urlparse(settings.DATABASE_URL)
        db_name = parsed_url.path.lstrip('/')
        
        # 构建连接到 MySQL 服务器的 URL（不指定数据库）
        server_url = urlunparse(parsed_url._replace(path=''))
        
        # 连接到 MySQL 服务器并创建数据库
        engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            # 检查数据库是否存在
            result = conn.execute(text(f"SHOW DATABASES LIKE '{db_name}'"))
            if result.fetchone() is None:
                logger.info(f"Creating database '{db_name}'...")
                conn.execute(text(f"CREATE DATABASE {db_name} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.info(f"Database '{db_name}' already exists")
        engine.dispose()
    except Exception as e:
        logger.exception(f"Database creation check failed: {e}")
        # 即使创建失败也继续，可能数据库已存在
    
    # 数据库迁移
    from alembic.config import Config
    from alembic import command
    
    try:
        logger.info("Starting database migration...")
        # 设置alembic配置
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
        
        # 处理 Alembic 的 % 转义：将 % 替换为 %%
        db_url_for_alembic = settings.DATABASE_URL.replace('%', '%%')
        alembic_cfg.set_main_option("sqlalchemy.url", db_url_for_alembic)
        
        # 运行迁移至最新版本
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migration completed successfully")
    except Exception as e:
        logger.exception(f"Database migration failed: {e}")
        # 即使迁移失败也不影响应用启动
        pass

    # ⚠️ 关键：Alembic 的 command.upgrade() 会读取 alembic.ini 中的
    # [logger_root] level=WARN，通过 logging.config.fileConfig() 覆盖
    # root logger 的级别。必须在此重新应用我们的日志配置。
    setup_logging()
    
    logger.info("=" * 60)
    logger.info("Application startup completed - ready to serve requests")
    logger.info("=" * 60)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),  # 动态获取允许的源地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query.router, prefix="/api/v1/query", tags=["智能问数"])
app.include_router(semantic.router, prefix="/api/v1/semantic", tags=["语义层管理"])
app.include_router(views.router, prefix="/api/v1/views", tags=["视图管理"])
app.include_router(dictionaries.router, prefix="/api/v1/dictionaries", tags=["字典管理"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["系统设置"])
app.include_router(air.router, prefix="/api/v1", tags=["AIR模块"])
app.include_router(can.router, prefix="/api/v1", tags=["CAN模块"])
app.include_router(big.router, prefix="/api/v1", tags=["BIG模块"])
app.include_router(data_format.router, prefix="/api/v1/data-format", tags=["数据格式配置"])
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent智能体"])
app.include_router(skills.router, tags=["Skills管理"])


@app.get("/")
async def root():
    return {"message": "NL2MQL2SQL API is running", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
