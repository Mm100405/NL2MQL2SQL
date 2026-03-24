@echo off
chcp 65001 >nul
echo 正在停止所有服务...
taskkill /FI "WINDOWTITLE eq NL2MQL2SQL Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq NL2MQL2SQL Frontend*" /T /F >nul 2>&1
echo ✅ 所有服务已停止
pause
