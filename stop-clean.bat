@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"

rem 关闭由 start.bat 打开的窗口及其子进程
taskkill /FI "WINDOWTITLE eq NL2MQL2SQL Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq NL2MQL2SQL Frontend*" /T /F >nul 2>&1

rem 按端口强制清理，覆盖 uvicorn --reload 派生进程和残留监听
for %%P in (8011 5173) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
        echo 停止端口 %%P 进程 PID=%%A
        taskkill /PID %%A /F /T >nul 2>&1
    )
)

rem 按项目命令行兜底清理 backend/frontend 启动链路
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root = [IO.Path]::GetFullPath('%ROOT%');" ^
  "Get-CimInstance Win32_Process | Where-Object {" ^
  "  if (-not $_.CommandLine) { $false } else {" ^
  "    $cmd = $_.CommandLine;" ^
  "    $isBackend = $_.Name -in @('cmd.exe','python.exe','uvicorn.exe') -and $cmd -match 'app\.main:app';" ^
  "    $isFrontend = $_.Name -in @('cmd.exe','node.exe') -and (($cmd -match 'npm install && npm run dev') -or ($cmd -match 'vite' -and $cmd -like ('*' + $root + 'frontend*')));" ^
  "    $isBackend -or $isFrontend" ^
  "  }" ^
  "} | ForEach-Object {" ^
  "  Write-Host ('停止残留进程 PID={0} {1}' -f $_.ProcessId, $_.Name);" ^
  "  taskkill.exe /PID $_.ProcessId /F /T | Out-Null;" ^
  "}"
