#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$SCRIPT_DIR/.pids"

echo "========================================"
echo "停止 NL2MQL2SQL 服务"
echo "========================================"
echo ""

# 停止后端服务
if [ -f "$PID_DIR/backend.pid" ]; then
    BACKEND_PID=$(cat "$PID_DIR/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo "正在停止后端服务 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        sleep 2
        # 如果进程还在运行，强制停止
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo "强制停止后端服务..."
            kill -9 $BACKEND_PID
        fi
        echo "✅ 后端服务已停止"
    else
        echo "⚠️  后端服务未运行"
    fi
    rm -f "$PID_DIR/backend.pid"
else
    echo "⚠️  未找到后端 PID 文件"
    # 尝试通过进程名停止
    pkill -f "uvicorn app.main:app" && echo "✅ 后端服务已停止" || echo "⚠️  未找到运行中的后端服务"
fi

echo ""

# 停止前端服务
if [ -f "$PID_DIR/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo "正在停止前端服务 (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        sleep 2
        # 如果进程还在运行，强制停止
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo "强制停止前端服务..."
            kill -9 $FRONTEND_PID
        fi
        echo "✅ 前端服务已停止"
    else
        echo "⚠️  前端服务未运行"
    fi
    rm -f "$PID_DIR/frontend.pid"
else
    echo "⚠️  未找到前端 PID 文件"
    # 尝试通过进程名停止
    pkill -f "vite" && echo "✅ 前端服务已停止" || echo "⚠️  未找到运行中的前端服务"
fi

echo ""
echo "========================================"
echo "所有服务已停止"
echo "========================================"
