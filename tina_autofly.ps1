# Tina 24/7 Autofly - Ray Evolution Core Runner
# Run daily at 03:00 via Windows Task Scheduler
# Usage: powershell -File tina_autofly.ps1

Write-Host "[*] Tina Digital Resilience Evolution..." -ForegroundColor Cyan

$ErrorActionPreference = "Continue"

# 1. Daily self-correction (i9 load)
Write-Host "[1/4] Self-correction..." -ForegroundColor Yellow
python ray_evolution.py --mode self_correct

# 2. Wisdom decay + weight update (SQLite operations)
Write-Host "[2/4] Weight update..." -ForegroundColor Yellow
python ray_evolution.py --mode update_weights

# 3. Check distillation threshold (gold samples > 50)
Write-Host "[3/4] Checking distillation threshold..." -ForegroundColor Yellow
$gold_count = python -c "
import sqlite3
conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()
c.execute(\"SELECT count(*) FROM wisdom_logs WHERE weight > 1.5 AND passed = 1\")
print(conn.fetchone()[0])
conn.close()
"

if ($gold_count -gt 50) {
    Write-Host "[!] Distillation threshold met ($gold_count > 50) - Launch Unsloth fine-tuning (4050 load)..." -ForegroundColor Yellow
    python ray_train_tina.py --mode causal_sft --epochs 3

    # 4. Hot-reload Ollama model
    Write-Host "[4/4] Reloading Ollama model..." -ForegroundColor Cyan
    & ollama create ray-tina-v2 -f ray_v1_modelfile 2>$null
    Write-Host "[OK] 1.5B model upgraded with distilled wisdom." -ForegroundColor Green
} else {
    Write-Host "[-] Insufficient samples, continuing accumulation (current: $gold_count / 50)" -ForegroundColor Gray
}

Write-Host "[*] Evolution task complete. Awaiting market open..." -ForegroundColor Cyan