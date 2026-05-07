@echo off
chcp 936 >/dev/null
title Generation Two - Alpha Mining System
color 0B

echo.
echo ========================================
echo   Generation Two - Advanced Mining
echo ========================================
echo.
echo WARNING: Generation Two is advanced system.
echo Recommend to use Generation One first.
echo.
echo Features:
echo - Genetic Algorithm Evolution Engine
echo - Self-Optimizing Parameter Tuning
echo - AST Deep Validation
echo - Quality Monitoring
echo - Cyberpunk GUI Interface
echo.

set /p confirm="Continue? (y/n): "
if /i not "%confirm%"=="y" (
    echo Cancelled
    pause
    exit /b 0
)

echo.
echo ========================================
echo Step 1: Check Python
echo ========================================
echo.

python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [OK] Python installed
echo.

echo ========================================
echo Step 2: Enter Generation Two directory
echo ========================================
echo.

cd generation_two
if %errorlevel% neq 0 (
    echo [ERROR] Cannot enter directory
    pause
    exit /b 1
)

echo [OK] Current directory: %cd%
echo.

echo ========================================
echo Step 3: Install dependencies
echo ========================================
echo.

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Installing PyQt5 (GUI dependency)...
pip install PyQt5

echo.
echo [OK] Dependencies installed
echo.

echo ========================================
echo Step 4: Configure credentials
echo ========================================
echo.

if exist credential.txt (
    echo [OK] Credential file exists
    echo Content:
    type credential.txt
    echo.
) else if exist ..\generation_one\naive-ollama\credential.txt (
    echo Copying credentials from Generation One...
    copy ..\generation_one\naive-ollama\credential.txt .
    echo [OK] Credential file copied
    echo.
) else (
    echo [WARNING] Credential file not found
    echo Please create credential.txt file
    echo Format: ["email@worldquant.com", "password"]
    echo.
    set /p create_cred="Create now? (y/n): "
    if /i "%create_cred%"=="y" (
        set /p email="Enter email: "
        set /p password="Enter password: "
        echo ["%email%", "%password%"] > credential.txt
        echo [OK] Credential file created
    )
    echo.
)

echo ========================================
echo Step 5: Check Ollama
echo ========================================
echo.

where ollama >/dev/null 2>/dev/null
if %errorlevel% equ 0 (
    echo [OK] Ollama installed
    ollama --version
    echo.
    echo Installed models:
    ollama list
    echo.
) else (
    echo [WARNING] Ollama not found
    echo Please install Ollama: https://ollama.ai/download
    echo.
    echo After installation, download recommended model:
    echo ollama pull qwen2.5-coder:1.5b
    echo.
    pause
    exit /b 1
)

echo ========================================
echo Step 6: Start GUI
echo ========================================
echo.

echo Starting Cyberpunk GUI...
echo.
echo GUI Features:
echo - Dashboard: System status monitoring
echo - Evolution: Genetic algorithm config
echo - Config: Generation parameters
echo - Monitor: Real-time performance
echo - Database: Historical data query
echo.

python gui/run_gui.py credential.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] GUI startup failed
    echo Please check:
    echo 1. PyQt5 installed correctly
    echo 2. Credential file correct
    echo 3. Ollama running
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Generation Two Started
echo ========================================
echo.

pause
