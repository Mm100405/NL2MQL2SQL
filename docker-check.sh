#!/bin/bash
# Docker 环境检查脚本

echo "========================================"
echo "  Docker 环境检查工具"
echo "========================================"
echo ""

# 检查 Docker
echo "[1/4] 检查 Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker 已安装"
    docker --version
else
    echo "❌ Docker 未安装"
    echo "   安装指南: https://docs.docker.com/get-docker/"
    exit 1
fi
echo ""

# 检查 Docker Compose
echo "[2/4] 检查 Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "✅ Docker Compose 已安装"
    docker-compose --version
else
    echo "❌ Docker Compose 未安装"
    echo "   安装指南: https://docs.docker.com/compose/install/"
    exit 1
fi
echo ""

# 检查 Docker 服务状态
echo "[3/4] 检查 Docker 服务状态..."
if docker info &> /dev/null; then
    echo "✅ Docker 服务正在运行"
else
    echo "❌ Docker 服务未运行"
    echo "   请启动 Docker 服务："
    echo "   - Linux: sudo systemctl start docker"
    echo "   - Mac: 打开 Docker Desktop"
    echo "   - Windows: 打开 Docker Desktop"
    exit 1
fi
echo ""

# 检查网络连接
echo "[4/4] 检查 Docker 网络连接..."
if docker network ls | grep -q "nl2mql2sql-network"; then
    echo "✅ Docker 网络已存在"
else
    echo "ℹ️  Docker 网络不存在，首次启动时会自动创建"
fi
echo ""

echo "========================================"
echo "✅ 环境检查完成"
echo "========================================"
echo ""
echo "Docker 信息："
docker info | grep -E "Server Version|Operating System|Total Memory|CPUs"
echo ""
echo "Docker 网络列表："
docker network ls
echo ""
echo "Docker 镜像列表："
docker images | grep -E "REPOSITORY|nl2mql2sql"
echo ""
