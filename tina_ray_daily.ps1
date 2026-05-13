# Ray Tina System Daily Automation
# 執行時間：每個交易日 08:30-18:30
# Version 1.0 | 2026-05-12

$ErrorActionPreference = "Continue"
$RAY_DIR = "C:\Users\USER\.openclaw\agents\ray"
$LOG_DIR = "$RAY_DIR\logs"

# Create log directory if not exists
if (!(Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

$LOG_FILE = "$LOG_DIR\ray_daily_$(Get-Date -Format 'yyyyMMdd').log"

function Write-Log {
    param([string]$msg, [string]$level = "INFO")
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "$ts [$level] $msg"
    Write-Host $line
    $line | Out-File -FilePath $LOG_FILE -Append
}

Write-Log "=== Ray Tina System Daily Start ==="

# Stage 1: 盤前掃描 (08:30)
Write-Log "[1/6] Stage 1: 盤前動能掃描 (ray-v1 1.5B)"
try {
    python $RAY_DIR\us_momentum.py --symbols QQQ,VTI,BND,VEA,SPY 2>&1 | Out-File -FilePath $LOG_FILE -Append
    Write-Log "Stage 1 complete"
} catch {
    Write-Log "Stage 1 failed: $_" "ERROR"
}

# Stage 2: 每日自我修正 (15:00) — 雙層 LLM
Write-Log "[2/6] Stage 2: 每日自我修正 (1.5B fast + 7B deep)"
try {
    python $RAY_DIR\ray_self_correct.py 2>&1 | Out-File -FilePath $LOG_FILE -Append
    $corrections = python -c "
import sqlite3
conn = sqlite3.connect('$RAY_DIR\ray_wisdom.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE created_at > datetime(\"now\", \"-1 day\")')
print(c.fetchone()[0])
conn.close()
"
    Write-Log "Self-corrections today: $corrections"
} catch {
    Write-Log "Stage 2 failed: $_" "ERROR"
}

# Stage 3: 蒸餾數據生成 (17:00)
Write-Log "[3/6] Stage 3: 蒸餾數據生成"
try {
    python $RAY_DIR\ray_gold_miner.py 2>&1 | Out-File -FilePath $LOG_FILE -Append
    Write-Log "Stage 3 complete"
} catch {
    Write-Log "Stage 3 failed: $_" "ERROR"
}

# Stage 4: Weight 更新 (17:30)
Write-Log "[4/6] Stage 4: 智慧權重更新 (strengthen + decay)"
try {
    python $RAY_DIR\ray_evolution.py --mode update_weights 2>&1 | Out-File -FilePath $LOG_FILE -Append
    Write-Log "Stage 4 complete"
} catch {
    Write-Log "Stage 4 failed: $_" "ERROR"
}

# Stage 5: Wisdom Decay (18:00)
Write-Log "[5/6] Stage 5: 智慧衰減"
try {
    python $RAY_DIR\ray_evolution.py --mode decay 2>&1 | Out-File -FilePath $LOG_FILE -Append
    Write-Log "Stage 5 complete"
} catch {
    Write-Log "Stage 5 failed: $_" "ERROR"
}

# Stage 6: 系統狀態報告 (18:30)
Write-Log "[6/6] Stage 6: 每日狀態報告"
try {
    python $RAY_DIR\ray_evolution.py --mode stats 2>&1 | Out-File -FilePath $LOG_FILE -Append

    # 健康檢查
    $wisdom_count = python -c "
import sqlite3
conn = sqlite3.connect('$RAY_DIR\ray_wisdom.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM wisdom_logs')
print(c.fetchone()[0])
conn.close()
"
    $corrections_count = python -c "
import sqlite3
conn = sqlite3.connect('$RAY_DIR\ray_wisdom.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
print(c.fetchone()[0])
conn.close()
"
    Write-Log "Daily Summary: wisdom_logs=$wisdom_count, corrections=$corrections_count"
} catch {
    Write-Log "Stage 6 failed: $_" "ERROR"
}

Write-Log "=== Ray Tina System Daily Complete ==="