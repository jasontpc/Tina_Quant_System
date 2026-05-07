# -*- coding: utf-8 -*-
"""
Tina 全系統健檢 v2 — 缺陷尋找與優化建議
"""
import sqlite3, os, sys, subprocess, glob, json
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
SCRIPTS = WORKSPACE / "scripts"
OPENCLAW_CLI = r"C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js"

def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return r.stdout.strip()
    except: return ""

def get_latest(db, table):
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        try:
            r = cur.execute(f'SELECT MAX(date) FROM "{table}"').fetchone()[0]
            conn.close()
            return str(r)[:10] if r else None
        except:
            conn.close()
            return None
    except: return None

def days_ago(date_str):
    if not date_str: return 999
    try:
        return (datetime.now().date() - datetime.strptime(date_str, '%Y-%m-%d').date()).days
    except: return 999

# ── 1. Cron 全體狀態 ──────────────────────────────────────────
print("=" * 60)
print("  🔍 Tina 全系統健檢報告")
print(f"  時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

output = run(["node", OPENCLAW_CLI, "cron", "list"], timeout=25)
cron_lines = output.splitlines()
all_crons = {}
error_crons = []
running_crons = []

for line in cron_lines:
    if len(line) > 35 and line[0] not in (' ', ' ', '\t'):
        parts = line.split()
        if len(parts) >= 2:
            cid = parts[0]
            name = " ".join(parts[1:])
            all_crons[cid] = {'name': name, 'status': 'unknown'}

for line in cron_lines:
    for cid in all_crons:
        if cid in line:
            if "error" in line.lower(): all_crons[cid]['status'] = 'error'
            elif "ok" in line.lower(): all_crons[cid]['status'] = 'ok'
            elif "idle" in line.lower(): all_crons[cid]['status'] = 'idle'
            elif "running" in line.lower(): all_crons[cid]['status'] = 'running'

error_crons = {c: v for c, v in all_crons.items() if v['status'] == 'error'}
running_crons = {c: v for c, v in all_crons.items() if v['status'] == 'running'}
ok_crons = {c: v for c, v in all_crons.items() if v['status'] == 'ok'}
idle_crons = {c: v for c, v in all_crons.items() if v['status'] == 'idle'}

print("\n📅 [1] Cron 狀態")
print(f"   總數: {len(all_crons)} | ✅OK: {len(ok_crons)} | 🔴Error: {len(error_crons)} | 🔄Running: {len(running_crons)} | 💤Idle: {len(idle_crons)}")

# ── 2. DB 健康度 ─────────────────────────────────────────────
print("\n🗄️  [2] Database 健康度")
dbs = sorted(list(DATA.glob("*.db")))
stale_dbs = []
empty_dbs = []
for db in dbs:
    size = db.stat().st_size
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    if size == 0:
        empty_dbs.append(db.name)
        print(f"   ⚠️  {db.name}: 空檔案 (0 bytes)")
        continue
    if not tables:
        empty_dbs.append(db.name)
        print(f"   ⚠️  {db.name}: 無表格 (0 tables)")
        continue
    latest_dates = {}
    for t in tables:
        d = get_latest(db, t)
        if d: latest_dates[t] = d
    if latest_dates:
        latest = max(latest_dates.values())
        age = days_ago(latest)
        status = "🔴 STALE" if age >= 3 else ("🟡" if age >= 1 else "✅")
        print(f"   {status} {db.name}: latest={latest} ({age}天)")
        if age >= 3: stale_dbs.append((db.name, latest, age))
    else:
        print(f"   ⚠️  {db.name}: 無日期欄位")

# ── 3. 腳本完整性檢查（critical scripts 存在？） ──────────────
print("\n📜 [3] 關鍵腳本存在檢查")
critical_scripts = {
    'tw_institutional.py': 'TW 法人資料',
    'macro_institutional_fetcher.py': 'DB寫入法人',
    'fetch_margin_data.py': 'Margin 更新',
    'maggy_db_update.py': 'Maggy 更新',
    'backfill_rsi.py': 'RSI Backfill',
    'ray_etf_dca.py': 'Ray DCA',
    'tina_brain_monitor.py': '健康檢查',
    'tina_cron_optimizer.py': 'Cron 優化',
    'tina_system_sop_health.py': 'SOP 健康',
    'fix_brain_alerts.py': '警報修復',
}
missing = []
for script, label in critical_scripts.items():
    path = SCRIPTS / script
    exists = path.exists()
    status = "✅" if exists else "🔴 MISSING"
    print(f"   {status} {script} ({label})")
    if not exists: missing.append(script)

# ── 4. Cron 腳本對應缺口（cron存在但腳本不存在？） ──────────
print("\n🔗 [4] Cron vs 腳本對應檢查")
cron_output = run(["node", OPENCLAW_CLI, "cron", "list"], timeout=25)
orphan_crons = []  # cron 跑的腳本不存在
for line in cron_output.splitlines():
    for cid in all_crons:
        if cid in line:
            details = run(["node", OPENCLAW_CLI, "cron", "show", cid], timeout=20)
            for l in details.splitlines():
                if 'message' in l and 'python' in l:
                    script_path = l.split('python')[-1].strip().replace('\\\\', '\\').replace('\\', '')
                    if script_path and not os.path.exists(script_path):
                        orphan_crons.append((cid, all_crons[cid]['name'], script_path))
                        print(f"   🔴 Orphan cron: [{all_crons[cid]['name']}] → {script_path}")
            break

# ── 5. Timeout 檢查（太短的 cron） ──────────────────────────
print("\n⏱️  [5] Timeout 設定檢查")
short_timeout = []
for line in cron_output.splitlines():
    for cid in all_crons:
        if cid in line:
            details = run(["node", OPENCLAW_CLI, "cron", "show", cid], timeout=20)
            for l in details.splitlines():
                if 'timeoutSeconds' in l:
                    val = int(''.join(filter(str.isdigit, l)))
                    if val < 120:
                        short_timeout.append((cid, all_crons[cid]['name'], val))
                        print(f"   🔴 {all_crons[cid]['name']}: timeout={val}s (太短)")
            break

# ── 6. 資料缺口（重要 DB 無 cron 維護） ──────────────────────
print("\n📡 [6] 資料缺口（重要 DB 無 cron）")
# Check which important dbs are NOT being updated by any cron
db_to_cron = {}  # db -> cron that updates it
for line in cron_output.splitlines():
    for cid in all_crons:
        if cid in line:
            details = run(["node", OPENCLAW_CLI, "cron", "show", cid], timeout=20)
            for l in details.splitlines():
                if 'message' in l:
                    msg = l.lower()
                    for db_name in ['macro_institutional', 'yfinance', 'etf', 'tw_history', 'maggy', 'finmind']:
                        if db_name in msg and cid not in db_to_cron:
                            db_to_cron[db_name] = (cid, all_crons[cid]['name'])
            break

# Which dbs are stale but have no cron?
stale_no_cron = []
for db_name, _, age in stale_dbs:
    db_key = db_name.replace('.db', '').replace('_', '')
    found = any(k in db_key for k in db_to_cron)
    if not found and age >= 4:
        stale_no_cron.append(db_name)

if stale_no_cron:
    for d in stale_no_cron:
        print(f"   🔴 {d}: stale但無對應cron維護")
else:
    print("   ✅ 所有重要stale DB均有cron對應")

# ── 7. 統計缺陷 ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("  📊 缺陷統計")
print("=" * 60)
print(f"   🔴 Error cron: {len(error_crons)}")
print(f"   🔴 Timeout太短: {len(short_timeout)}")
print(f"   🔴 Orphan cron: {len(orphan_crons)}")
print(f"   🔴 Stale DB: {len(stale_dbs)} (>=3天)")
print(f"   🔴 Empty DB: {len(empty_dbs)}")
print(f"   🔴 Missing script: {len(missing)}")
print(f"   🔴 Stale無cron: {len(stale_no_cron)}")

# ── 8. 優化建議 ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("  💡 優化建議")
print("=" * 60)

if len(error_crons) >= 5:
    print(f"   [優先] {len(error_crons)} 支cron持續error → 可能是Gateway不穩定，建議等待穩定後批量修復")

if short_timeout:
    print(f"   [高] {len(short_timeout)} 支cron timeout太短 → 建議全部設為120s以上")
    for cid, name, val in short_timeout[:3]:
        print(f"       - {name}: {val}s → 應改為120s")

if orphan_crons:
    print(f"   [高] {len(orphan_crons)} 支cron指向不存在的腳本 → 應修正或刪除")
    for cid, name, path in orphan_crons[:3]:
        print(f"       - [{name}]: {path}")

if missing:
    print(f"   [中] {len(missing)} 支關鍵腳本缺失 → 需補建")
    for s in missing:
        print(f"       - {s}")

if stale_no_cron:
    print(f"   [中] {len(stale_no_cron)} 個DB落後但無cron維護 → 建議建立對應cron")
    for d in stale_no_cron:
        print(f"       - {d}")

if empty_dbs:
    print(f"   [低] {len(empty_dbs)} 個空DB → 可能是歷史遺留，應評估刪除")
    for d in empty_dbs[:3]:
        print(f"       - {d}")

# ── 9. 今日完成盤點 ─────────────────────────────────────────
print("\n" + "=" * 60)
print("  ✅ 今日已完成優化")
print("=" * 60)
completed = [
    "FinMind Token v2 更換（29支腳本）",
    "tina_brain_monitor.py 健康檢查邏輯重寫",
    "macro_institutional_fetcher.py 接管 TW 法人 cron",
    "Streamlit Auto-Send Toggle（TW+US）",
    "US ETF 納入 Ray DCA（VTI/VOO/QQQ/VEA/BND）",
    "tina_sop_prevention.md 建立",
    "5支 error cron timeout → 300s",
    "Maggy/Margin 健康檢查豁免邏輯",
    "TW 法人/Margin cron 重建並設定正確 delivery",
]
for i, item in enumerate(completed, 1):
    print(f"   {i}. ✅ {item}")

print("\n✅ 全系統健檢完成")