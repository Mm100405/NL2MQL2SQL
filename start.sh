#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/.pids"

# 创建日志和 PID 目录
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

echo "========================================"
echo "NL2MQL2SQL 启动脚本（Linux/Mac）"
echo "========================================"
echo ""

# 停止已有服务
if [ -f "$PID_DIR/backend.pid" ]; then
    echo "停止现有后端服务..."
    kill $(cat "$PID_DIR/backend.pid") 2>/dev/null
    rm -f "$PID_DIR/backend.pid"
fi

if [ -f "$PID_DIR/frontend.pid" ]; then
    echo "停止现有前端服务..."
    kill $(cat "$PID_DIR/frontend.pid") 2>/dev/null
    rm -f "$PID_DIR/frontend.pid"
fi

echo "[1/2] 检查后端环境..."
cd "$BACKEND_DIR"
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，正在复制 .env.example..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请根据需要修改配置"
fi

# 检查是否需要安装依赖
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "安装后端依赖..."
    pip install -r requirements.txt
fi
echo "✅ 后端环境检查完成"
echo ""

echo "[2/2] 启动后端服务..."
echo "正在启动 FastAPI 后端（端口 8011）..."

# 后台启动后端
nohup uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_DIR/backend.pid"

# 等待后端启动
sleep 2
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
else
    echo "❌ 后端服务启动失败，请查看日志：$LOG_DIR/backend.log"
    exit 1
fi
echo ""

echo "[2/2] 启动前端服务..."
cd "$FRONTEND_DIR"

# 检查是否需要安装依赖
if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."
    npm install
fi

# 后台启动前端服务（使用 Vite 开发服务器）
echo "正在启动前端服务（端口 5173）..."
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PID_DIR/frontend.pid"

# 等待前端启动
sleep 2
if ps -p $FRONTEND_PID > /dev/null; then
    echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
else
    echo "❌ 前端服务启动失败，请查看日志：$LOG_DIR/frontend.log"
    exit 1
fi
echo ""

echo "========================================"
echo "启动完成！"
echo "========================================"
echo "访问地址："
echo "  - 前端：http://localhost:5173"
echo "  - 后端 API 文档：http://localhost:8011/docs"
echo ""
echo "内网访问地址："
# 获取内网 IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
if [ -n "$LOCAL_IP" ]; then
    echo "  - 前端：http://$LOCAL_IP:5173"
    echo "  - 后端：http://$LOCAL_IP:8011/docs"
fi
echo ""
echo "日志位置："
echo "  - 后端日志：$LOG_DIR/backend.log"
echo "  - 前端日志：$LOG_DIR/frontend.log"
echo ""
echo "停止服务：运行 ./stop.sh"
echo "查看日志：tail -f $LOG_DIR/backend.log"
echo ""

# 显示后端启动日志（最后10行）
echo "后端启动日志（最后10行）："
echo "----------------------------------------"
tail -n 10 "$LOG_DIR/backend.log"
echo "----------------------------------------"
