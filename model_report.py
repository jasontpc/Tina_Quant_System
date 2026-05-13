import sqlite3, os, subprocess
from datetime import datetime

AGENT_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = os.path.join(AGENT_DIR, "ray_wisdom.db")

print("=" * 60)
print("  Ray 系統 4B/7B 模型訓練報告")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print(f"\nDB Tables: {tables}")

# backtest count
c.execute("SELECT COUNT(*) as cnt, MAX(timestamp) as last FROM backtest_reports")
r = c.fetchone()
print(f"\nbacktest_reports: {r[0]} 筆, 最新: {r[1]}")

# wisdom_corrections - check schema first
c.execute("PRAGMA table_info(wisdom_corrections)")
cols = [r[1] for r in c.fetchall()]
print(f"wisdom_corrections columns: {cols}")

if 'created_at' in cols:
    c.execute("SELECT COUNT(*) as cnt, MAX(created_at) as last FROM wisdom_corrections")
elif 'ts' in cols:
    c.execute("SELECT COUNT(*) as cnt, MAX(ts) as last FROM wisdom_corrections")
else:
    c.execute("SELECT COUNT(*) as cnt FROM wisdom_corrections")
r = c.fetchone()
print(f"wisdom_corrections: {r[0]} 筆", end="")
if r[1]:
    print(f", 最新: {r[1]}")

# signals log
if 'ts' in cols:
    c.execute("SELECT COUNT(*) as cnt, MAX(ts) as last FROM signals_log")
    r = c.fetchone()
    print(f"signals_log: {r[0]} 筆, 最新: {r[1]}")

conn.close()

print("\n--- Ollama Models ---")
result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
print(result.stdout)

# Check Modelfile
MODELS_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "models", "qwen35-4b-iq4xs")
modelfile = os.path.join(MODELS_DIR, "Ray-v3.5.Modelfile")
if os.path.exists(modelfile):
    mtime = os.path.getmtime(modelfile)
    dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
    print(f"Ray-v3.5.Modelfile: last modified {dt}")

# Check long_term files
LONG_TERM = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
files = os.listdir(LONG_TERM) if os.path.exists(LONG_TERM) else []
print(f"\nstores/long_term/: {files}")

print("\n--- Cron Job Schedule ---")
print("05:00  ray_distiller_auto.py (固化)  → qwen3.5-4b-iq4xs -> ray-v3.5")
print("14:00  ray_knowledge_distiller.py    → qwen2.5:7b -> axioms_v3.5.json")
print("14:05  ray_logic_distiller.py        → ray-deep-v1 -> ray_forbidden_rules.json")
print("17:00  ray_web_collector.py          → qwen2.5:7b -> wisdom_corrections.web_auto")