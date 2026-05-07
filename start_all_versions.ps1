# WorldQuant Miner - 版本选择启动器 (PowerShell)
# 支持启动所有版本的 Alpha 自动化服务

$Host.UI.RawUI.WindowTitle = "WorldQuant Miner - 版本选择器"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           WorldQuant Miner - 版本选择启动器                    ║" -ForegroundColor Cyan
Write-Host "╠════════════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  当前时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "┌──────────────────────────────────────────────────────────────────┐" -ForegroundColor Yellow
Write-Host "│  Generation One - 基础版本                                      │" -ForegroundColor Yellow
Write-Host "├──────────────────────────────────────────────────────────────────┤" -ForegroundColor Yellow
Write-Host "│  1. naive-ollama          (推荐) 基础 Alpha 生成                │" -ForegroundColor White
Write-Host "│     - 简单直接，适合入门                                         │" -ForegroundColor Gray
Write-Host "│     - Web Dashboard 监控                                        │" -ForegroundColor Gray
Write-Host "│     - 自动编排器                                                │" -ForegroundColor Gray
Write-Host "├──────────────────────────────────────────────────────────────────┤" -ForegroundColor Yellow
Write-Host "│  2. consultant-naive-ollama     自适应优化版                    │" -ForegroundColor White
Write-Host "│     - 多臂老虎机算法                                            │" -ForegroundColor Gray
Write-Host "│     - 自适应参数调整                                            │" -ForegroundColor Gray
Write-Host "│     - 模型舰队管理                                              │" -ForegroundColor Gray
Write-Host "│     - VRAM 智能监控                                             │" -ForegroundColor Gray
Write-Host "├──────────────────────────────────────────────────────────────────┤" -ForegroundColor Yellow
Write-Host "│  3. consultant-multi-arm-bandit  多臂老虎机优化版               │" -ForegroundColor White
Write-Host "│     - 多臂老虎机决策                                            │" -ForegroundColor Gray
Write-Host "│     - 模型选择优化                                              │" -ForegroundColor Gray
Write-Host "│     - 集成式挖掘器                                              │" -ForegroundColor Gray
Write-Host "└──────────────────────────────────────────────────────────────────┘" -ForegroundColor Yellow
Write-Host ""

Write-Host "┌──────────────────────────────────────────────────────────────────┐" -ForegroundColor Magenta
Write-Host "│  Generation Two - 高级版本                                      │" -ForegroundColor Magenta
Write-Host "├──────────────────────────────────────────────────────────────────┤" -ForegroundColor Magenta
Write-Host "│  4. Generation Two        (进阶) 自优化系统                     │" -ForegroundColor White
Write-Host "│     - 遗传算法进化                                              │" -ForegroundColor Gray
Write-Host "│     - AST 深度验证                                              │" -ForegroundColor Gray
Write-Host "│     - Cyberpunk GUI (PyQt5)                                     │" -ForegroundColor Gray
Write-Host "│     - SQLite 数据存储                                           │" -ForegroundColor Gray
Write-Host "└──────────────────────────────────────────────────────────────────┘" -ForegroundColor Magenta
Write-Host ""

Write-Host "┌──────────────────────────────────────────────────────────────────┐" -ForegroundColor Green
Write-Host "│  辅助工具                                                       │" -ForegroundColor Green
Write-Host "├──────────────────────────────────────────────────────────────────┤" -ForegroundColor Green
Write-Host "│  5. alpha-icu             Alpha 分析监控工具                    │" -ForegroundColor White
Write-Host "│     - 分析已提交 Alpha                                          │" -ForegroundColor Gray
Write-Host "│     - 相关性检查                                                │" -ForegroundColor Gray
Write-Host "│     - 性能报告                                                  │" -ForegroundColor Gray
Write-Host "├──────────────────────────────────────────────────────────────────┤" -ForegroundColor Green
Write-Host "│  6. Web Dashboard         单独启动监控面板                      │" -ForegroundColor White
Write-Host "│     - 仅启动 naive-ollama 的 Web Dashboard                      │" -ForegroundColor Gray
Write-Host "└──────────────────────────────────────────────────────────────────┘" -ForegroundColor Green
Write-Host ""

$choice = Read-Host "请选择要启动的版本 (1-6)"

$projectRoot = $PSScriptRoot
if (-not $projectRoot) {
    $projectRoot = Get-Location
}

function Start-NaiveOllama {
    Write-Host ""
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  启动 Generation One - naive-ollama" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""

    Set-Location "$projectRoot\generation_one\naive-ollama"

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[错误] 未找到 credential.txt" -ForegroundColor Red
        Write-Host "请确保文件存在于: $(Get-Location)\credential.txt" -ForegroundColor Red
        return
    }

    Write-Host "[启动] 持续挖掘模式..." -ForegroundColor Green
    Write-Host "[提示] 按 Ctrl+C 停止运行" -ForegroundColor Yellow
    Write-Host ""

    python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model llama3:8b
}

function Start-ConsultantNaive {
    Write-Host ""
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  启动 Generation One - consultant-naive-ollama" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""

    Set-Location "$projectRoot\generation_one\consultant-naive-ollama"

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[提示] 复制凭证文件..." -ForegroundColor Yellow
        Copy-Item "$projectRoot\generation_one\naive-ollama\credential.txt" . -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[错误] 未找到 credential.txt" -ForegroundColor Red
        return
    }

    Write-Host "[启动] 自适应优化模式..." -ForegroundColor Green
    Write-Host "[提示] 按 Ctrl+C 停止运行" -ForegroundColor Yellow
    Write-Host ""

    python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model llama3:8b
}

function Start-ConsultantBandit {
    Write-Host ""
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  启动 Generation One - consultant-multi-arm-bandit-ollama" -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""

    Set-Location "$projectRoot\generation_one\consultant-multi-arm-bandit-ollama"

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[提示] 复制凭证文件..." -ForegroundColor Yellow
        Copy-Item "$projectRoot\generation_one\naive-ollama\credential.txt" . -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[错误] 未找到 credential.txt" -ForegroundColor Red
        return
    }

    Write-Host "[启动] 多臂老虎机优化模式..." -ForegroundColor Green
    Write-Host "[提示] 按 Ctrl+C 停止运行" -ForegroundColor Yellow
    Write-Host ""

    python alpha_orchestrator.py --credentials ./credential.txt --mode continuous --mining-interval 6 --batch-size 3 --max-concurrent 2 --ollama-model llama3:8b
}

function Start-GenerationTwo {
    Write-Host ""
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  启动 Generation Two - 自优化系统" -ForegroundColor Magenta
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host ""

    Set-Location "$projectRoot\generation_two"

    # 检查 PyQt5
    try {
        python -c "import PyQt5" 2>$null
    } catch {
        Write-Host "[安装] PyQt5..." -ForegroundColor Yellow
        pip install PyQt5 -q
    }

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[提示] 复制凭证文件..." -ForegroundColor Yellow
        Copy-Item "$projectRoot\generation_one\naive-ollama\credential.txt" . -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[错误] 未找到 credential.txt" -ForegroundColor Red
        return
    }

    Write-Host "[启动] Cyberpunk GUI..." -ForegroundColor Green
    Write-Host "[提示] GUI 窗口将打开" -ForegroundColor Yellow
    Write-Host ""

    python gui/run_gui.py credential.txt
}

function Start-AlphaICU {
    Write-Host ""
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  启动 Alpha ICU - 分析监控工具" -ForegroundColor Green
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""

    Set-Location "$projectRoot\generation_one\alpha-icu"

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[提示] 复制凭证文件..." -ForegroundColor Yellow
        Copy-Item "$projectRoot\generation_one\naive-ollama\credential.txt" . -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path "credential.txt")) {
        Write-Host "[错误] 未找到 credential.txt" -ForegroundColor Red
        return
    }

    Write-Host "[启动] Alpha 分析..." -ForegroundColor Green
    Write-Host ""

    python main.py --credentials ./credential.txt
}

function Start-WebDashboard {
    Write-Host ""
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  启动 Web Dashboard - 监控面板" -ForegroundColor Green
    Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""

    Set-Location "$projectRoot\generation_one\naive-ollama"

    Write-Host "[启动] Web Dashboard..." -ForegroundColor Green
    Write-Host "[提示] 访问 http://localhost:5000" -ForegroundColor Yellow
    Write-Host "[提示] 按 Ctrl+C 停止运行" -ForegroundColor Yellow
    Write-Host ""

    python web_dashboard.py
}

switch ($choice) {
    "1" { Start-NaiveOllama }
    "2" { Start-ConsultantNaive }
    "3" { Start-ConsultantBandit }
    "4" { Start-GenerationTwo }
    "5" { Start-AlphaICU }
    "6" { Start-WebDashboard }
    default {
        Write-Host "[错误] 无效选择" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  服务已停止" -ForegroundColor Cyan
Write-Host "══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
