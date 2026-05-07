# WorldQuant Miner - PowerShell 启动脚本
# 作者: hongxingshanshan
# 日期: 2026-05-07

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "WorldQuant Miner - Generation One" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置错误时停止
$ErrorActionPreference = "Stop"

try {
    # 检查 Python
    Write-Host "[检查] Python..." -ForegroundColor Yellow
    $pythonVersion = python --version
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
    Write-Host ""

    # 检查 Ollama
    Write-Host "[检查] Ollama..." -ForegroundColor Yellow
    $ollamaPath = "C:\Users\Administrator\AppData\Local\Programs\Ollama\ollama.exe"
    & $ollamaPath --version
    Write-Host "[OK] Ollama 已安装" -ForegroundColor Green
    Write-Host ""

    # 检查模型
    Write-Host "[检查] 已安装的模型:" -ForegroundColor Yellow
    & $ollamaPath list
    Write-Host ""

    # 进入项目目录
    Write-Host "[启动] 进入项目目录..." -ForegroundColor Yellow
    Set-Location generation_one\naive-ollama
    Write-Host "[OK] 当前目录: $(Get-Location)" -ForegroundColor Green
    Write-Host ""

    # 检查凭证文件
    Write-Host "[检查] 凭证文件..." -ForegroundColor Yellow
    if (Test-Path credential.txt) {
        Write-Host "[OK] credential.txt 存在" -ForegroundColor Green
    } else {
        Write-Host "[错误] credential.txt 不存在" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
    Write-Host ""

    # 显示菜单
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "请选择运行模式:" -ForegroundColor Cyan
    Write-Host "1. 单次测试 (生成 3 个 Alpha)" -ForegroundColor White
    Write-Host "2. Web Dashboard (浏览器监控)" -ForegroundColor White
    Write-Host "3. 持续挖掘 (24/7 自动运行)" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    $choice = Read-Host "请输入选择 (1-3，默认 1)"
    if ([string]::IsNullOrWhiteSpace($choice)) {
        $choice = "1"
    }

    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "[启动] 单次测试模式..." -ForegroundColor Green
            Write-Host "[提示] 将生成 3 个 Alpha 并测试" -ForegroundColor Yellow
            Write-Host "[提示] 按 Ctrl+C 停止运行" -ForegroundColor Yellow
            Write-Host ""

            python alpha_generator_ollama.py `
                --credentials ./credential.txt `
                --batch-size 3 `
                --sleep-time 10 `
                --ollama-model llama3:8b `
                --max-concurrent 2
        }

        "2" {
            Write-Host ""
            Write-Host "[启动] Web Dashboard..." -ForegroundColor Green
            Write-Host "[提示] 请在浏览器访问: http://localhost:5000" -ForegroundColor Yellow
            Write-Host "[提示] 按 Ctrl+C 停止运行" -ForegroundColor Yellow
            Write-Host ""

            python web_dashboard.py
        }

        "3" {
            Write-Host ""
            Write-Host "[启动] 持续挖掘模式..." -ForegroundColor Green
            Write-Host "[提示] 按 Ctrl+C 停止运行" -ForegroundColor Yellow
            Write-Host ""

            python alpha_orchestrator.py `
                --credentials ./credential.txt `
                --mode continuous `
                --mining-interval 6 `
                --batch-size 3 `
                --max-concurrent 2 `
                --ollama-model llama3:8b
        }

        default {
            Write-Host "[错误] 无效选择" -ForegroundColor Red
        }
    }

} catch {
    Write-Host ""
    Write-Host "[错误] 发生异常:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "运行完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Read-Host "按回车键退出"
