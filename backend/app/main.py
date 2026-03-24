from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import socket

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
        print(f"[CORS] 动态添加内网 IP: http://{local_ip}:5173")
    
    return origins

# 配置日志系统
import os
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler(os.path.join(log_dir, 'app.log'), encoding='utf-8')  # 输出到文件
    ]
)

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
    print(f"[GLOBAL ERROR] {type(exc).__name__}: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


@app.on_event("startup")
def startup_event():
    print("=" * 60)
    print("Application startup initiated")
    print("=" * 60)
    
    # 显示 CORS 配置
    cors_origins = get_cors_origins()
    print(f"[CORS] 允许的源地址：")
    for origin in cors_origins:
        print(f"  - {origin}")
    print()
    
    # 同步执行数据库迁移，但添加详细的进度日志
    from alembic.config import Config
    from alembic import command
    import os
    
    try:
        print("Starting database migration...")
        # 设置alembic配置
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        # 运行迁移至最新版本
        command.upgrade(alembic_cfg, "head")
        print("Database migration completed successfully")
    except Exception as e:
        print(f"Database migration failed: {e}")
        # 即使迁移失败也不影响应用启动
        pass
    
    print()
    print("=" * 60)
    print("Application startup completed - ready to serve requests")
    print("=" * 60)


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
