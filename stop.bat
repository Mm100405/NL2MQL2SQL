@echo off
chcp 65001 >nul
echo 正在停止 NL2MQL2SQL 本地服务...
call "%~dp0stop-clean.bat"
echo ✅ 所有服务已停止
pause
