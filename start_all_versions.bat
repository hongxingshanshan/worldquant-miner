@echo off
title WorldQuant Miner - Version Selector
color 0B

echo.
echo ================================================================================
echo            WorldQuant Miner - Version Launcher
echo ================================================================================
echo   Current Time: %date% %time%
echo ================================================================================
echo.

echo +--------------------------------------------------------------------------------+
echo ^|  Generation One - Basic Versions                                              ^|
echo +--------------------------------------------------------------------------------+
echo ^|  1. naive-ollama          (Recommended) Basic Alpha Generation                ^|
echo ^|     - Simple and direct, suitable for beginners                                ^|
echo ^|     - Web Dashboard monitoring                                                 ^|
echo ^|     - Automatic orchestrator                                                   ^|
echo +--------------------------------------------------------------------------------+
echo ^|  2. consultant-naive-ollama     Adaptive Optimization Version                  ^|
echo ^|     - Multi-arm bandit algorithm                                               ^|
echo ^|     - Adaptive parameter adjustment                                            ^|
echo ^|     - Model fleet management                                                   ^|
echo ^|     - VRAM intelligent monitoring                                               ^|
echo +--------------------------------------------------------------------------------+
echo ^|  3. consultant-multi-arm-bandit  Multi-arm Bandit Optimization Version         ^|
echo ^|     - Multi-arm bandit decision making                                         ^|
echo ^|     - Model selection optimization                                              ^|
echo ^|     - Integrated miner                                                         ^|
echo +--------------------------------------------------------------------------------+
echo.
echo +--------------------------------------------------------------------------------+
echo ^|  Generation Two - Advanced Version                                             ^|
echo +--------------------------------------------------------------------------------+
echo ^|  4. Generation Two        (Advanced) Self-optimizing System                    ^|
echo ^|     - Genetic algorithm evolution                                              ^|
echo ^|     - AST deep validation                                                      ^|
echo ^|     - Cyberpunk GUI (PyQt5)                                                    ^|
echo ^|     - SQLite data storage                                                      ^|
echo +--------------------------------------------------------------------------------+
echo.
echo +--------------------------------------------------------------------------------+
echo ^|  Auxiliary Tools                                                               ^|
echo +--------------------------------------------------------------------------------+
echo ^|  5. alpha-icu             Alpha Analysis Monitoring Tool                       ^|
echo ^|     - Analyze submitted Alpha                                                  ^|
echo ^|     - Correlation check                                                        ^|
echo ^|     - Performance report                                                       ^|
echo +--------------------------------------------------------------------------------+
echo ^|  6. Web Dashboard         Start Monitoring Panel Separately                    ^|
echo ^|     - Only start naive-ollama Web Dashboard                                    ^|
echo +--------------------------------------------------------------------------------+
echo ^|  7. Model Selection       Interactive LLM Model Selection                      ^|
echo ^|     - View installed models                                                    ^|
echo ^|     - Set default model                                                        ^|
echo ^|     - Pull new models                                                          ^|
echo +--------------------------------------------------------------------------------+
echo.

set /p choice="Please select version to start (1-7): "

if "%choice%"=="1" goto naive_ollama
if "%choice%"=="2" goto consultant_naive
if "%choice%"=="3" goto consultant_bandit
if "%choice%"=="4" goto generation_two
if "%choice%"=="5" goto alpha_icu
if "%choice%"=="6" goto web_dashboard
if "%choice%"=="7" goto model_selector

echo [Error] Invalid selection
pause
exit /b 1

:naive_ollama
echo.
echo ================================================================================
echo   Starting Generation One - naive-ollama
echo ================================================================================
echo.
cd generation_one\naive-ollama
if not exist credential.txt (
    echo [Error] credential.txt not found
    pause
    exit /b 1
)
echo [Starting] Using default model from config file...
echo [Starting] Web Dashboard will be available at http://localhost:5000
start "Web Dashboard - naive-ollama" python web_dashboard.py
timeout /t 2 /nobreak >nul
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --config config.json
goto end

:consultant_naive
echo.
echo ================================================================================
echo   Starting Generation One - consultant-naive-ollama
echo ================================================================================
echo.
cd generation_one\consultant-naive-ollama
if not exist credential.txt copy ..\naive-ollama\credential.txt . >nul 2>&1
if not exist credential.txt (
    echo [Error] credential.txt not found
    pause
    exit /b 1
)
echo [Starting] Using default model from config file...
echo [Starting] Web Dashboard will be available at http://localhost:5000
start "Web Dashboard - consultant-naive" python web_dashboard.py
timeout /t 2 /nobreak >nul
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --config config.json
goto end

:consultant_bandit
echo.
echo ================================================================================
echo   Starting Generation One - consultant-multi-arm-bandit-ollama
echo ================================================================================
echo.
cd generation_one\consultant-multi-arm-bandit-ollama
if not exist credential.txt copy ..\naive-ollama\credential.txt . >nul 2>&1
if not exist credential.txt (
    echo [Error] credential.txt not found
    pause
    exit /b 1
)
echo [Starting] Using default model from config file...
echo [Starting] Web Dashboard will be available at http://localhost:5000
start "Web Dashboard - multi-arm-bandit" python web_dashboard.py
timeout /t 2 /nobreak >nul
python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --config config.json
goto end

:generation_two
echo.
echo ================================================================================
echo   Starting Generation Two - Self-optimizing System
echo ================================================================================
echo.
cd generation_two
python -c "import PyQt5" 2>nul
if errorlevel 1 pip install PyQt5 -q
if not exist credential.txt copy ..\generation_one\naive-ollama\credential.txt . >nul 2>&1
if not exist credential.txt (
    echo [Error] credential.txt not found
    pause
    exit /b 1
)
echo [Starting] Cyberpunk GUI...
python gui/run_gui.py credential.txt
goto end

:alpha_icu
echo.
echo ================================================================================
echo   Starting Alpha ICU - Analysis Monitoring Tool
echo ================================================================================
echo.
cd generation_one\alpha-icu
if not exist credential.txt copy ..\naive-ollama\credential.txt . >nul 2>&1
if not exist credential.txt (
    echo [Error] credential.txt not found
    pause
    exit /b 1
)
echo [Starting] Alpha Analysis...
python main.py --credentials ./credential.txt
goto end

:web_dashboard
echo.
echo ================================================================================
echo   Starting Web Dashboard - Monitoring Panel
echo ================================================================================
echo.
cd generation_one\naive-ollama
echo [Starting] Web Dashboard...
echo [Info] Visit http://localhost:5000
python web_dashboard.py
goto end

:model_selector
echo.
echo ================================================================================
echo   Model Selection Tool
echo ================================================================================
echo.
cd generation_one\naive-ollama
python model_selector.py --config config.json
goto end

:end
echo.
echo ================================================================================
echo   Service Stopped
echo ================================================================================
pause
