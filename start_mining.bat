@echo off
echo ========================================
echo 启动 WorldQuant Miner 持续挖掘模式
echo ========================================
echo.

cd generation_one\naive-ollama

echo [检查] 验证凭证文件...
if not exist credential.txt (
    echo [错误] credential.txt 不存在！
    echo 请先运行 setup.bat 创建凭证文件
    pause
    exit /b 1
)

echo [启动] 正在启动持续挖掘模式...
echo [配置] 使用 glm-5.1-r1:1.5b 模型（适合 8GB VRAM）
echo [配置] 最大并发: 2, 批量: 3, 间隔: 30秒
echo.
echo [提示] 按 Ctrl+C 停止运行
echo.

python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model deepseek-r1:1.5b

pause