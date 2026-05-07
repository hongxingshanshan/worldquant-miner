@echo off
echo ========================================
echo WorldQuant Miner 单次运行模式
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

echo [启动] 正在生成 Alpha...
echo [配置] 使用 glm-5.1-r1:1.5b 模型（适合 8GB VRAM）
echo [配置] 批量: 3 个 Alpha
echo.

python alpha_generator_ollama.py --credentials ./credential.txt --batch-size 3 --sleep-time 30 --ollama-model deepseek-r1:1.5b --max-concurrent 2

echo.
echo [完成] Alpha 生成完成
echo [结果] 查看 hopeful_alphas.json 和 results/ 目录
echo.

pause