@echo off
chcp 65001 >nul
echo ========================================
echo   NL2MQL2SQL - Docker 部署
echo ========================================
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未安装，请先安装 Docker
    echo    安装指南: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose 未安装，请先安装 Docker Compose
    echo    安装指南: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

echo ✅ Docker 环境检查通过
echo.

echo 请选择部署模式：
echo 1) 开发环境（代码热重载）
echo 2) 生产环境（优化镜像）
set /p mode=请输入选项 [1-2]:

if "%mode%"=="1" (
    echo.
    echo 🔧 启动开发环境...
    echo.
    
    REM 启动开发环境
    docker-compose -f docker-compose.dev.yml up -d
    
    echo.
    echo ========================================
    echo ✅ 开发环境启动完成
    echo ========================================
    echo.
    echo 访问地址：
    echo   前端: http://localhost:5173
    echo   后端: http://localhost:8011
    echo   API 文档: http://localhost:8011/docs
    echo.
    echo 查看日志：
    echo   docker-compose -f docker-compose.dev.yml logs -f
    echo.
    echo 停止服务：
    echo   docker-compose -f docker-compose.dev.yml down
    echo.
) else if "%mode%"=="2" (
    echo.
    echo 🏭 启动生产环境...
    echo.
    
    REM 检查配置文件
    if not exist ".env.docker" (
        echo ❌ 未找到 .env.docker，正在创建...
        copy .env.docker .env
        echo ✅ 已创建 .env 文件
    )
    
    if not exist ".env" (
        echo ⚠️  未找到 .env 文件，请先配置环境变量
        pause
    )
    
    REM 构建并启动
    docker-compose build
    docker-compose up -d
    
    echo.
    echo ========================================
    echo ✅ 生产环境启动完成
    echo ========================================
    echo.
    echo 访问地址：
    echo   前端: http://localhost
    echo   后端: http://localhost:8011
    echo   API 文档: http://localhost:8011/docs
    echo.
    echo 查看日志：
    echo   docker-compose logs -f
    echo.
    echo 停止服务：
    echo   docker-compose down
    echo.
) else (
    echo ❌ 无效选项
    pause
    exit /b 1
)

pause
