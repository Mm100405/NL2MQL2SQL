#!/bin/bash
# Docker 一键启动脚本

echo "========================================"
echo "  NL2MQL2SQL - Docker 部署"
echo "========================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    echo "   安装指南: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    echo "   安装指南: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker 环境检查通过"
echo ""

# 选择部署模式
echo "请选择部署模式："
echo "1) 开发环境（代码热重载）"
echo "2) 生产环境（优化镜像）"
read -p "请输入选项 [1-2]: " mode

case $mode in
    1)
        echo ""
        echo "🔧 启动开发环境..."
        echo ""
        
        # 检查配置文件
        if [ ! -f "docker-compose.dev.yml" ]; then
            echo "❌ 未找到 docker-compose.dev.yml"
            exit 1
        fi
        
        # 启动开发环境
        docker-compose -f docker-compose.dev.yml up -d
        
        echo ""
        echo "========================================"
        echo "✅ 开发环境启动完成"
        echo "========================================"
        echo ""
        echo "访问地址："
        echo "  前端: http://localhost:5173"
        echo "  后端: http://localhost:8011"
        echo "  API 文档: http://localhost:8011/docs"
        echo ""
        echo "查看日志："
        echo "  docker-compose -f docker-compose.dev.yml logs -f"
        echo ""
        echo "停止服务："
        echo "  docker-compose -f docker-compose.dev.yml down"
        echo ""
        ;;
    2)
        echo ""
        echo "🏭 启动生产环境..."
        echo ""
        
        # 检查配置文件
        if [ ! -f ".env.docker" ]; then
            echo "❌ 未找到 .env.docker，正在创建..."
            cp .env.docker .env
            echo "✅ 已创建 .env 文件"
        fi
        
        if [ ! -f ".env" ]; then
            echo "⚠️  未找到 .env 文件，请先配置环境变量"
            read -p "是否现在编辑 .env 文件？[y/N] " edit_env
            if [ "$edit_env" = "y" ] || [ "$edit_env" = "Y" ]; then
                ${EDITOR:-nano} .env
            fi
        fi
        
        # 构建并启动
        docker-compose build
        docker-compose up -d
        
        echo ""
        echo "========================================"
        echo "✅ 生产环境启动完成"
        echo "========================================"
        echo ""
        echo "访问地址："
        echo "  前端: http://localhost"
        echo "  后端: http://localhost:8011"
        echo "  API 文档: http://localhost:8011/docs"
        echo ""
        echo "查看日志："
        echo "  docker-compose logs -f"
        echo ""
        echo "停止服务："
        echo "  docker-compose down"
        echo ""
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac
