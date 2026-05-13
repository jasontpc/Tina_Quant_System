# Ray Tina System Weekly Distillation
# 執行時間：每週五 22:00（非交易日，系統空閒）
# Version 1.0 | 2026-05-12

$ErrorActionPreference = "Continue"
$RAY_DIR = "C:\Users\USER\.openclaw\agents\ray"
$LOG_DIR = "$RAY_DIR\logs"

if (!(Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }

$LOG_FILE = "$LOG_DIR\ray_weekly_$(Get-Date -Format 'yyyyMMdd').log"

function Write-Log {
    param([string]$msg, [string]$level = "INFO")
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "$ts [$level] $msg"
    Write-Host $line
    $line | Out-File -FilePath $LOG_FILE -Append
}

Write-Log "=== Ray Tina Weekly Distillation Start ==="

# Step 0: 確保 Ollama 服務運行
Write-Log "[0/4] 檢查 Ollama 服務..."
$ollama = Get-Process -Name "ollama" -EA SilentlyContinue
if (!$ollama) {
    Write-Log "Ollama not running, starting..." "WARNING"
    Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# Step 1: 預熱 7B 模型（避免冷啟動延遲）
Write-Log "[1/4] 預熱 ray-deep-v1 (7B)..."
try {
    python -c "
import requests, time
t0 = time.time()
resp = requests.post('http://localhost:11434/api/chat', json={
    'model': 'ray-deep-v1',
    'messages': [{'role': 'user', 'content': 'Pre-warm for distillation.'}],
    'stream': False,
    'options': {'num_predict': 5}
}, timeout=120)
elapsed = time.time() - t0
print(f'7B warmup: {elapsed:.1f}s, response: {resp.json()[\"message\"][\"content\"][:50]}')
" 2>&1 | Out-File -FilePath $LOG_FILE -Append
    Write-Log "7B warmup complete"
} catch {
    Write-Log "7B warmup failed: $_" "WARNING"
}

# Step 2: 蒸餾數據生成
Write-Log "[2/4] 生成蒸餾數據..."
try {
    python $RAY_DIR\ray_gold_miner.py 2>&1 | Out-File -FilePath $LOG_FILE -Append

    # Check gold samples count
    $gold_count = python -c "
import sqlite3
conn = sqlite3.connect('$RAY_DIR\ray_wisdom.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM wisdom_logs WHERE weight > 1.5 AND passed = 1')
print(c.fetchone()[0])
conn.close()
"
    Write-Log "Gold samples (weight > 1.5): $gold_count"
} catch {
    Write-Log "Gold miner failed: $_" "ERROR"
}

# Step 3: 執行 Unsloth 微調（如果數據充足）
Write-Log "[3/4] 執行 Unsloth 微調..."
if ($gold_count -gt 30) {
    Write-Log "Proceeding with distillation (gold_count=$gold_count > 30)..."

    # Check if Unsloth is installed
    $unsloth_ok = python -c "import unsloth; print('OK')" 2>&1

    if ($unsloth_ok -eq "OK") {
        python $RAY_DIR\ray_train_tina.py --mode causal_sft --epochs 3 2>&1 | Out-File -FilePath $LOG_FILE -Append
        Write-Log "Distillation complete"

        # Reload Ollama model
        Write-Log "Reloading ray-v1 model..."
        & "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" create ray-v1 -f "$RAY_DIR\ray-v1.Modelfile" 2>$null
        Write-Log "Model reloaded"
    } else {
        Write-Log "Unsloth not installed — skipping training" "WARNING"
        Write-Log "Install: pip install unsloth" "INFO"
    }
} else {
    Write-Log "Insufficient gold samples ($gold_count <= 30) — skipping distillation" "INFO"
    Write-Log "Accumulating more samples for next week"
}

# Step 4: 每週統計
Write-Log "[4/4] 每週統計"
python $RAY_DIR\ray_evolution.py --mode stats 2>&1 | Out-File -FilePath $LOG_FILE -Append

# Final summary
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

Write-Log "=== Weekly Summary ==="
Write-Log "wisdom_logs: $wisdom_count"
Write-Log "wisdom_corrections: $corrections_count"
Write-Log "Gold samples (weight > 1.5): $gold_count"
Write-Log "=== Ray Tina Weekly Complete ==="