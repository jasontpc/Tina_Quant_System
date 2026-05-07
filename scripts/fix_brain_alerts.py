# -*- coding: utf-8 -*-
import sqlite3, os, subprocess, sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
data_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
scripts_dir = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts'
results = []

def check_table(db_path, table):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cnt = cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{table}")').fetchall()]
        date_col = next((c for c in cols if 'date' in c.lower()), None)
        latest = 'N/A'
        if date_col and cnt > 0:
            try: latest = cur.execute(f'SELECT MAX("{date_col}") FROM "{table}"').fetchone()[0]
            except: pass
        conn.close()
        return cnt, str(latest)[:10]
    except Exception as e:
        return -1, str(e)

def try_run_script(name, script_path):
    try:
        r = subprocess.run(['python', script_path], capture_output=True, text=True, timeout=90)
        return r.returncode == 0, r.stdout[:200] if r.stdout else r.stderr[:200]
    except Exception as e:
        return False, str(e)

# 1. macro_institutional.db - institutional_daily
print("=== [1] 法人數據更新 ===")
db = os.path.join(data_dir, 'macro_institutional.db')
cnt, latest = check_table(db, 'institutional_daily')
days_old = (datetime.now().date() - datetime.strptime(latest, '%Y-%m-%d').date()).days if latest != 'N/A' and latest else 999
print(f"  institutional_daily: {cnt:,} rows | latest={latest} ({days_old}天落後)")
if days_old >= 3:
    scripts_to_try = ['tw_institutional.py', 'institutional_flow_analyzer.py', 'macro_institutional_fetcher.py']
    for s in scripts_to_try:
        sp = os.path.join(scripts_dir, s)
        if os.path.exists(sp):
            ok, msg = try_run_script(s, sp)
            if ok:
                print(f"  ✅ 已執行 {s}")
                break
            else:
                print(f"  ❌ {s}: {msg[:100]}")

# 2. macro_institutional.db - margin_balance
print("\n=== [2] 融資券更新 ===")
cnt2, latest2 = check_table(db, 'margin_balance')
days_old2 = (datetime.now().date() - datetime.strptime(latest2, '%Y-%m-%d').date()).days if latest2 != 'N/A' and latest2 else 999
print(f"  margin_balance: {cnt2:,} rows | latest={latest2} ({days_old2}天落後)")
if days_old2 >= 3 or cnt2 == 0:
    scripts2 = ['fetch_margin_data.py', 'fetch_margin_finmind.py', 'fetch_twse_margin.py']
    for s in scripts2:
        sp = os.path.join(scripts_dir, s)
        if os.path.exists(sp):
            ok, msg = try_run_script(s, sp)
            if ok:
                print(f"  ✅ 已執行 {s}")
                break
            else:
                print(f"  ❌ {s}: {msg[:100]}")

# 3. maggy.db
print("\n=== [3] Maggy DB ===")
conn3 = sqlite3.connect(os.path.join(data_dir, 'maggy.db'))
cur3 = conn3.cursor()
cur3.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables3 = [r[0] for r in cur3.fetchall()]
conn3.close()
print(f"  maggy.db tables: {tables3}")
for t in tables3:
    cnt, latest = check_table(os.path.join(data_dir, 'maggy.db'), t)
    print(f"    {t}: {cnt:,} rows | latest={latest}")

# Check which cron runs maggy update
print("\n  檢查 maggy cron...")
r = subprocess.run(['node', r'C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js', 'cron', 'list'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
for line in r.stdout.splitlines():
    if 'maggy' in line.lower() or 'Maggy' in line:
        print(f"  Found: {line[:80]}")

# 4. Check if tina_master.db / reddit_sentiment.db are actually needed
print("\n=== [4] 缺少的 DB 確認 ===")
for db_name in ['tina_master.db', 'reddit_sentiment.db']:
    path = os.path.join(data_dir, db_name)
    exists = os.path.exists(path)
    print(f"  {db_name}: {'EXISTS' if exists else 'MISSING'}")

# Check if any script references these DBs
import glob
for db_name in ['tina_master', 'reddit_sentiment']:
    refs = []
    for py in glob.glob(os.path.join(scripts_dir, '*.py')):
        try:
            content = open(py, encoding='utf-8', errors='ignore').read()
            if db_name in content:
                refs.append(os.path.basename(py))
        except:
            pass
    if refs:
        print(f"  {db_name} referenced by: {refs}")
    else:
        print(f"  {db_name}: 無腳本引用，可以移除")

# 5. Create new cron jobs for missing data
print("\n=== [5] 建立缺失的 Cron ===")
cron_cmds = []

# TW Institutional cron
r = subprocess.run(['node', r'C:\Users\USER\AppData\Roaming\npm\node_modules\openclaw\dist\index.js', 'cron', 'list'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
has_inst = any('institutional' in l.lower() and 'tw' in l.lower() for l in r.stdout.splitlines())
has_margin = any('margin' in l.lower() and 'tw' in l.lower() and 'us' not in l.lower() for l in r.stdout.splitlines())

if not has_inst:
    print("  → 新增 TW 法人資料 cron (16:30 平日)")
    cron_cmds.append(('TW 法人資料每日更新', '30 16 * * 1-5', 'python scripts/tw_institutional.py'))
else:
    print("  ✅ TW 法人 cron 已存在")

if not has_margin:
    print("  → 新增 TW Margin cron (16:30 平日)")
    cron_cmds.append(('TW Margin 每日更新', '35 16 * * 1-5', 'python scripts/fetch_margin_data.py'))
else:
    print("  ✅ TW Margin cron 已存在")

print("\n完成")