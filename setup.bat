@echo off
echo ========================================
echo WorldQuant Miner 快速部署脚本
echo ========================================
echo.

echo [1/5] 检查 Ollama 安装...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Ollama 未安装！
    echo 请访问 https://ollama.ai/download 下载安装
    pause
    exit /b 1
)
echo [OK] Ollama 已安装

echo.
echo [2/5] 检查 Python 依赖...
cd generation_one\naive-ollama
pip show requests >nul 2>&1
if %errorlevel% neq 0 (
    echo [安装] 正在安装 Python 依赖...
    pip install -r requirements.txt
) else (
    echo [OK] Python 依赖已安装
)

echo.
echo [3/5] 检查凭证文件...
if not exist credential.txt (
    echo [创建] 正在创建凭证文件模板...
    echo ["your.email@worldquant.com", "your_password"] > credential.txt
    echo [重要] 请编辑 credential.txt 填入你的 WorldQuant Brain 账号！
    pause
) else (
    echo [OK] 凭证文件已存在
)

echo.
echo [4/5] 下载推荐模型 (glm-5.1-r1:1.5b)...
ollama list | findstr "deepseek-r1:1.5b" >nul 2>&1
if %errorlevel% neq 0 (
    echo [下载] 正在下载 glm-5.1-r1:1.5b (约 1.1GB)...
    ollama pull deepseek-r1:1.5b
) else (
    echo [OK] glm-5.1-r1:1.5b 已存在
)

echo.
echo [5/5] 下载备用模型 (llama3:3b)...
ollama list | findstr "llama3:3b" >nul 2>&1
if %errorlevel% neq 0 (
    echo [下载] 正在下载 llama3:3b (约 2GB)...
    ollama pull llama3:3b
) else (
    echo [OK] llama3:3b 已存在
)

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 下一步:
echo 1. 编辑 generation_one\naive-ollama\credential.txt 填入你的 WorldQuant 账号
echo 2. 运行 start_mining.bat 开始挖掘
echo 3. 运行 start_dashboard.bat 启动 Web Dashboard
echo.
pause
