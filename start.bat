@echo off
chcp 65001 >nul
echo ========================================
echo NL2MQL2SQL 本地启动脚本（Windows）
echo ========================================
echo.

echo [1/3] 检查后端环境...
cd /d "%~dp0backend"
if not exist ".env" (
    echo ⚠️  未找到 .env 文件，正在复制 .env.example...
    copy .env.example .env
    echo ✅ 已创建 .env 文件，请根据需要修改配置
)
echo ✅ 后端环境检查完成
echo.

echo [2/3] 启动后端服务...
echo 正在启动 FastAPI 后端（端口 8011）...
start "NL2MQL2SQL Backend" cmd /k "pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload"
echo ✅ 后端服务启动中...
echo.

echo [3/3] 启动前端服务...
cd /d "%~dp0frontend"
if not exist ".env" (
    echo ⚠️  未找到 .env 文件，正在复制 .env.example...
    copy .env.example .env
    echo ✅ 已创建 .env 文件
)
echo 正在启动 Vue 3 前端（端口 5173）...
start "NL2MQL2SQL Frontend" cmd /k "npm install && npm run dev"
echo ✅ 前端服务启动中...
echo.

echo ========================================
echo 启动完成！
echo ========================================
echo 访问地址：
echo   - 本地访问：http://localhost:5173
echo   - 内网访问：http://192.168.42.208:5173（请替换为你的实际 IP）
echo.
echo 后端 API 文档：http://localhost:8011/docs
echo 内网访问文档：http://192.168.42.208:8011/docs
echo.
echo 按任意键关闭此窗口（不会关闭前后端服务）...
pause >nul
