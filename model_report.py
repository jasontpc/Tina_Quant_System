# -*- coding: utf-8 -*-
"""
model_report.py — Ray 系統綜合狀態報告
整合：model_report + llm_daily_report + llm_status
"""
import sqlite3, time, os, subprocess
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

AGENT_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = os.path.join(AGENT_DIR, "ray_wisdom.db")

def get_db(conn, sql, params=None):
    c = conn.cursor()
    c.execute(sql, params or [])
    return c.fetchone()

print("=" * 60)
print("  Ray System Status Report")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# ── 1. 回測報告 ────────────────────────────────────────────────
print("\n📊 [1] Backtest Reports")
c = conn.cursor()
c.execute('SELECT COUNT(*), AVG(sharpe_ratio), MAX(sharpe_ratio), COUNT(DISTINCT symbol) FROM backtest_reports WHERE sharpe_ratio > 0')
bt = c.fetchone()
print(f"   總筆數: {bt[0]:,}, Avg Sharpe: {bt[1]:.2f}, Max: {bt[2]:.2f}, 獨特標的: {bt[3]}")
c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio >= 1.5')
high = c.fetchone()[0]
print(f"   高 Sharpe (>=1.5): {high} 筆")

# ── 2. 智慧修正 ────────────────────────────────────────────────
print("\n🧠 [2] Wisdom Corrections")
c.execute('SELECT COUNT(*) FROM wisdom_corrections')
wc_total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM wisdom_corrections WHERE confidence >= 0.8')
wc_high = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE meta_label='ray-deep-v1'")
ray_deep = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE meta_label='qwen2.5:7b'")
qwen_7b = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM wisdom_corrections WHERE symbol='WEB_SOURCE'")
web = c.fetchone()[0]
print(f"   總修正: {wc_total} 筆 (高信心 {wc_high} 筆)")
print(f"   ray-deep-v1 產出: {ray_deep} 筆 | qwen2.5:7b 產出: {qwen_7b} 筆")
print(f"   連網學習: {web} 筆")

# ── 3. 交易信號 ────────────────────────────────────────────────
print("\n📈 [3] Signals Log")
c.execute('SELECT COUNT(*) FROM signals_log')
sig = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM signals_log WHERE approved=1')
approved = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM signals_log WHERE approved=0')
pending = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM signals_log WHERE created_at >= date('now', '-1 day')")
today = c.fetchone()[0]
print(f"   總信號: {sig:,} 筆 (已核准 {approved:,} | 待確認 {pending:,})")
print(f"   今日: {today} 筆")

# ── 4. Token 使用 ──────────────────────────────────────────────
print("\n💰 [4] Token Usage (本週)")
c.execute("SELECT model, weekly_used, weekly_total, daily_limit FROM token_history ORDER BY weekly_used DESC LIMIT 5")
for r in c.fetchall():
    pct = (r[1] / r[2] * 100) if r[2] and r[2] > 0 else 0
    print(f"   {r[0]}: {r[1]:,} / {r[2]:,} ({pct:.1f}%) | 日均 {r[3] or 'N/A'}")

# ── 5. 每日績效 ────────────────────────────────────────────────
print("\n📉 [5] Daily Performance")
c.execute('SELECT COUNT(*) FROM daily_performance')
dp = c.fetchone()[0]
if dp > 0:
    c.execute("SELECT SUM(profit_loss) FROM daily_performance WHERE date >= date('now', '-7 days')")
    w_pl = c.fetchone()[0] or 0
    c.execute("SELECT SUM(profit_loss) FROM daily_performance WHERE date >= date('now', '-30 days')")
    m_pl = c.fetchone()[0] or 0
    print(f"   總記錄: {dp} 筆 | 週損益: {w_pl:+.2f} | 月損益: {m_pl:+.2f}")

# ── 6. Ollama 模型狀態 ─────────────────────────────────────────
print("\n🤖 [6] Ollama Models")
try:
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    lines = result.stdout.strip().split('\n')
    for line in lines[1:8]:
        if line.strip():
            print(f"   {line}")
except:
    print("   (無法取得狀態)")

# ── 7. 核心腳本狀態 ─────────────────────────────────────────────
print("\n📁 [7] Core Scripts")
scripts = [
    'ray_brain.py', 'ray_scheduler.py', 'llm_router.py',
    'ray_distiller_auto.py', 'ray_knowledge_distiller.py', 'ray_logic_distiller.py',
    'ray_web_collector.py', 'ray_token_tracker.py',
    'ray_us_strategy_analysis.py', 'ray_us_premarket_macro.py',
    'us_scan_live.py', 'us_momentum.py',
    'ray_data_center.py', 'ray_engine.py', 'ray_nl2code.py', 'ray_retriever_v2.py'
]
for s in scripts:
    path = os.path.join(AGENT_DIR, s)
    if os.path.exists(path):
        size = os.path.getsize(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%m-%d %H:%M')
        print(f"   [OK] {s} ({size:>7,} B) {mtime}")
    else:
        print(f"   [MISSING] {s}")

# ── 8. Modelfile 狀態 ─────────────────────────────────────────
print("\n🧬 [8] Modelfiles")
modelfiles = {
    'Ray-v3.5.Modelfile': os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "models", "qwen35-4b-iq4xs", "Ray-v3.5.Modelfile"),
    'ray-deep-v1.Modelfile': os.path.join(AGENT_DIR, 'ray-deep-v1.Modelfile'),
}
for name, path in modelfiles.items():
    if os.path.exists(path):
        mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
        print(f"   [OK] {name}: {mtime}")
    else:
        print(f"   [MISSING] {name}")

# ── 9. Long-term Stores ────────────────────────────────────────
print("\n📚 [9] Long-term Stores")
LONG_TERM = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
if os.path.exists(LONG_TERM):
    files = sorted(os.listdir(LONG_TERM))
    for f in files:
        size = os.path.getsize(os.path.join(LONG_TERM, f))
        print(f"   {f}: {size:,} B")
else:
    print("   (不存在)")

conn.close()
print("\n" + "=" * 60)
print("=== Report Complete ===")