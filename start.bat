@echo off
title WorldQuant Miner
color 0A

echo.
echo ========================================
echo   WorldQuant Miner - Generation One
echo ========================================
echo.
echo Select mode:
echo   1. Start Mining (Generate Alpha)
echo   2. Web Dashboard (Monitor)
echo   3. Continuous Mining (24/7)
echo.

set /p choice="Enter choice (1-3, default 1): "
if "%choice%"=="" set choice=1

cd generation_one\naive-ollama

if "%choice%"=="1" (
    echo.
    echo [START] Mining mode...
    echo [TIP] Press Ctrl+C to stop
    echo.
    python alpha_generator_ollama.py --credentials ./credential.txt --batch-size 3 --ollama-model llama3:8b --max-concurrent 2
) else if "%choice%"=="2" (
    echo.
    echo [START] Web Dashboard...
    echo [TIP] Visit http://localhost:5000
    echo [TIP] Press Ctrl+C to stop
    echo.
    python web_dashboard.py
) else if "%choice%"=="3" (
    echo.
    echo [START] Continuous mining...
    echo [TIP] Press Ctrl+C to stop
    echo.
    python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model llama3:8b
) else (
    echo [ERROR] Invalid choice
)

echo.
pause
