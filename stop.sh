#!/bin/bash

echo "正在停止所有服务..."
pkill -f "uvicorn app.main:app"
pkill -f "vite"
echo "✅ 所有服务已停止"
