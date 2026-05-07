@echo off
echo ========================================
echo 启动 WorldQuant Miner Web Dashboard
echo ========================================
echo.

cd generation_one\naive-ollama

echo [启动] 正在启动 Web Dashboard...
echo [访问] http://localhost:5000
echo.
echo [提示] 按 Ctrl+C 停止运行
echo.

python web_dashboard.py

pause