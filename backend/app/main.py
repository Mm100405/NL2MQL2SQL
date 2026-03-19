from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.database import engine, Base
from app.api.v1 import query, semantic, settings as settings_api, air, can, big, views, dictionaries, data_format, agent

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
    print("Application startup initiated")
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
    
    print("Application startup completed - ready to serve requests")


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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


@app.get("/")
async def root():
    return {"message": "NL2MQL2SQL API is running", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
