#!/bin/bash

echo "========================================"
echo "NL2MQL2SQL 本地启动脚本（Linux/Mac）"
echo "========================================"
echo ""

echo "[1/3] 检查后端环境..."
cd "$(dirname "$0")/backend"
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在复制 .env.example..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请根据需要修改配置"
fi
echo "✅ 后端环境检查完成"
echo ""

echo "[2/3] 启动后端服务..."
echo "正在启动 FastAPI 后端（端口 8011）..."
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
echo ""

echo "[3/3] 启动前端服务..."
cd "$(dirname "$0")/frontend"
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在复制 .env.example..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件"
fi
echo "正在启动 Vue 3 前端（端口 5173）..."
npm install
npm run dev &
FRONTEND_PID=$!
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
echo ""

echo "========================================"
echo "启动完成！"
echo "========================================"
echo "访问地址："
echo "  - 本地访问：http://localhost:5173"
echo "  - 内网访问：请替换为你的实际 IP，如 http://192.168.x.x:5173"
echo ""
echo "获取本机 IP："
echo "  - Linux: ip addr show | grep inet"
echo "  - Mac: ifconfig | grep inet"
echo "  - Windows: ipconfig"
echo ""
echo "后端 API 文档：http://localhost:8011/docs"
echo ""
echo "停止服务：按 Ctrl+C 或运行 ./stop.sh"
echo ""

# 等待用户中断
wait
