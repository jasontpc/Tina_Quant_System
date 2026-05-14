# -*- coding: utf-8 -*-
"""
Tina System Health Check — 全面檢測腳本
檢查：Qwen 模型 / Ollama / 資料庫 / 硬體 / 排程
"""

import json, sqlite3, time, sys, os, subprocess, requests

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "http://localhost:11434/api/chat"
DB_PATH = "ray_wisdom.db"

print("=" * 60)
print("  Tina System Health Check")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# ============================================================
# 1. 硬體檢測
# ============================================================
print("\n[1] 硬體狀態")
print("-" * 40)

try:
    import torch
    print(f"  PyTorch: {torch.__version__}")
    print(f"  CUDA: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        mem_gb = torch.cuda.get_device_properties(0).total_mem / 1e9
        print(f"  VRAM: {mem_gb:.1f} GB")
    else:
        print("  GPU: No CUDA GPU detected")
except ImportError:
    print("  PyTorch: Not installed")

try:
    import psutil
    mem = psutil.virtual_memory()
    print(f"  RAM: {mem.total / 1e9:.1f} GB total | {mem.available / 1e9:.1f} GB available")
    cpu = psutil.cpu_percent(interval=1)
    print(f"  CPU: {cpu}% usage | {psutil.cpu_count()} cores")
except ImportError:
    print("  RAM/CPU: psutil not available")

# ============================================================
# 2. Ollama + Qwen 模型檢測
# ============================================================
print("\n[2] Ollama + Qwen 模型")
print("-" * 40)

try:
    resp = requests.get("http://localhost:11434/api/tags", timeout=5)
    models = resp.json().get("models", [])
    print(f"  Ollama: ✅ Running ({len(models)} models)")

    for m in models:
        size_gb = m.get("size", 0) // (1024**3)
        size_mb = m.get("size", 0) // (1024**2)
        print(f"  - {m['name']} ({size_mb:.0f} MB)")

    # 測試 1.5B 回應速度
    print("\n  Testing ray-v1 (1.5B) response time...")
    t0 = time.time()
    payload = {"model": "ray-v1", "messages": [{"role": "user", "content": "Hi"}], "stream": False}
    r = requests.post(BASE_URL, json=payload, timeout=30)
    el1b = time.time() - t0
    print(f"  ray-v1: {el1b:.2f}s ✅" if r.status_code == 200 else f"  ray-v1: ❌ ({r.status_code})")

    # 測試 7B 回應速度
    print("  Testing ray-deep-v1 (7B) response time...")
    t0 = time.time()
    payload = {"model": "ray-deep-v1", "messages": [{"role": "user", "content": "Hi"}], "stream": False}
    r = requests.post(BASE_URL, json=payload, timeout=300)
    el7b = time.time() - t0
    print(f"  ray-deep-v1: {el7b:.2f}s ✅" if r.status_code == 200 else f"  ray-deep-v1: ❌ ({r.status_code})")

except Exception as e:
    print(f"  Ollama: ❌ Not reachable ({e})")
    models = []

# ============================================================
# 3. 資料庫健檢
# ============================================================
print("\n[3] 資料庫健檢")
print("-" * 40)

if not os.path.exists(DB_PATH):
    print(f"  ❌ {DB_PATH} not found")
else:
    size_kb = os.path.getsize(DB_PATH) // 1024
    print(f"  ✅ {DB_PATH} ({size_kb} KB)")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"  Tables: {len(tables)}")

    table_counts = {}
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        table_counts[t] = c.fetchone()[0]

    key_tables = ["wisdom_logs", "wisdom_corrections", "backtest_reports", "signals_log", "positions_log", "daily_performance"]
    for t in key_tables:
        count = table_counts.get(t, 0)
        status = "✅" if count > 0 else "⚠️ (empty)"
        print(f"    {t}: {count} {status}")

    # wisdom_logs weight 分佈
    c.execute("SELECT COUNT(*) FROM wisdom_logs WHERE weight > 2.0")
    high = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM wisdom_logs WHERE weight < 1.0 AND weight IS NOT NULL")
    low = c.fetchone()[0]
    print(f"    weight high(>2): {high} | low(<1): {low}")

    # backtest quality
    c.execute("SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 0.8")
    gold08 = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 1.5")
    gold15 = c.fetchone()[0]
    print(f"    Sharpe>0.8: {gold08} | Sharpe>1.5: {gold15} ⭐")

    # wisdom_corrections quality
    c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8")
    high_conf = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM wisdom_corrections")
    total_corr = c.fetchone()[0]
    print(f"    corrections: {total_corr} (high conf: {high_conf})")

    conn.close()

# ============================================================
# 4. 磁碟空間
# ============================================================
print("\n[4] 磁碟空間")
print("-" * 40)
try:
    import shutil
    total, used, free = shutil.disk_usage("C:\\")
    print(f"  C: {free//1024**3} GB free / {total//1024**3} GB total")
except:
    print("  C: Unable to query")

# ============================================================
# 5. Windows 排程任務
# ============================================================
print("\n[5] Windows Task Scheduler")
print("-" * 40)

tasks = ["Ray Tina Daily", "Ray Tina Evening", "Ray Tina Weekly"]
found_tasks = []
try:
    result = subprocess.run(
        ["schtasks", "/query", "/fo", "list"],
        capture_output=True, text=True, timeout=10
    )
    for task in tasks:
        if task in result.stdout:
            found_tasks.append(task)
            print(f"  ✅ {task}")
        else:
            print(f"  ❌ {task} (not found)")
except Exception as e:
    print(f"  Unable to query: {e}")

# ============================================================
# 6. 腳本完整性
# ============================================================
print("\n[6] 核心腳本完整性")
print("-" * 40)

scripts = {
    "ray_brain.py":           "大腦協調層",
    "ray_engine.py":          "回測引擎",
    "ray_data_center.py":     "資料庫持久化",
    "ray_nl2code.py":         "JSON驗證",
    "ray_evolution.py":       "自主學習",
    "ray_self_correct.py":    "自我修正",
    "ray_gold_miner.py":      "黃金挖掘",
    "ray_train_tina.py":      "蒸餾訓練",
    "tina_daily_self_correct.py": "每日自動化",
    "us_momentum.py":         "動能掃描",
    "us_scan_live.py":        "即時掃描",
}

all_ok = True
for script, desc in scripts.items():
    path = f"C:\\Users\\USER\\.openclaw\\agents\\ray\\{script}"
    if os.path.exists(path):
        size_kb = os.path.getsize(path) // 1024
        print(f"  ✅ {script} ({size_kb} KB)")
    else:
        print(f"  ❌ {script} MISSING")
        all_ok = False

# ============================================================
# 7. 最近的 Ollama 日誌摘要
# ============================================================
print("\n[7] Ollama 最近日誌")
print("-" * 40)

log_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Ollama", "server.log")
if os.path.exists(log_path):
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        recent = lines[-10:] if len(lines) > 10 else lines
        for line in recent:
            line = line.strip()
            if line:
                print(f"  {line[-100:]}")
    except Exception as e:
        print(f"  Unable to read log: {e}")
else:
    print(f"  Log not found at {log_path}")

# ============================================================
# 8. Summary Score
# ============================================================
print("\n" + "=" * 60)
print("  健康總結")
print("=" * 60)

score = 0
max_score = 10

# Hardware
if torch.cuda.is_available(): score += 2
else: print("  ⚠️ No GPU - Unsloth distillation unavailable")

# Models
if len(models) >= 2: score += 2
else: print("  ⚠️ Missing models in Ollama")

# DB
conn2 = sqlite3.connect(DB_PATH)
c2 = conn2.cursor()
c2.execute("SELECT COUNT(*) FROM wisdom_logs")
wl = c2.fetchone()[0]
c2.execute("SELECT COUNT(*) FROM backtest_reports")
br = c2.fetchone()[0]
if wl > 100: score += 1
if br > 50: score += 1
if wl < 50: print(f"  ⚠️ wisdom_logs low ({wl})")
if br < 10: print(f"  ⚠️ backtest_reports low ({br})")
conn2.close()

# Scripts
if all_ok: score += 2
else: print("  ⚠️ Some scripts missing")

# Scheduler
if len(found_tasks) >= 2: score += 1
else: print("  ⚠️ Task Scheduler not fully configured")

# Gold quality
conn3 = sqlite3.connect(DB_PATH)
c3 = conn3.cursor()
c3.execute("SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio > 1.5")
gold15 = c3.fetchone()[0]
if gold15 >= 1: score += 1
else: print(f"  ⚠️ No Sharpe>1.5 strategies")
conn3.close()

print(f"\n  健康分數: {score}/{max_score}")
if score >= 8:
    print("  狀態: 🟢 健康")
elif score >= 5:
    print("  狀態: 🟡 一般")
else:
    print("  狀態: 🔴 需要修復")

print("=" * 60)