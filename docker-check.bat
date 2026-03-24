@echo off
chcp 65001 >nul
echo ========================================
echo   Docker 环境检查工具
echo ========================================
echo.

REM 检查 Docker
echo [1/4] 检查 Docker...
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker 已安装
    docker --version
) else (
    echo ❌ Docker 未安装
    echo    安装指南: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)
echo.

REM 检查 Docker Compose
echo [2/4] 检查 Docker Compose...
docker-compose --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker Compose 已安装
    docker-compose --version
) else (
    echo ❌ Docker Compose 未安装
    echo    安装指南: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)
echo.

REM 检查 Docker 服务状态
echo [3/4] 检查 Docker 服务状态...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker 服务正在运行
) else (
    echo ❌ Docker 服务未运行
    echo    请启动 Docker Desktop
    pause
    exit /b 1
)
echo.

REM 检查网络连接
echo [4/4] 检查 Docker 网络连接...
docker network ls | findstr "nl2mql2sql-network" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker 网络已存在
) else (
    echo ℹ️  Docker 网络不存在，首次启动时会自动创建
)
echo.

echo ========================================
echo ✅ 环境检查完成
echo ========================================
echo.
echo Docker 信息：
docker info | findstr "Server Version Operating System"
echo.
echo Docker 网络列表：
docker network ls
echo.
echo Docker 镜像列表：
docker images | findstr "REPOSITORY nl2mql2sql"
echo.

pause
