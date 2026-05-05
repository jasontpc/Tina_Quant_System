# -*- coding: utf-8 -*-
"""
Tina 大腦健康監控 - 每小時執行
檢查：cron jobs / DB freshness / 腳本完整性 / 系統異常
"""
import sys, sqlite3, os, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
SCRIPTS_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts'
LOG_FILE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\reports\brain_monitor_log.md'

token = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
chat = '1616824689'

lines = [f"## 🧠 Tina Brain Monitor | {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

# 1. Cron Job 健康檢查
idle_count = 0
ok_count = 0
total_match = 0
try:
    import subprocess
    result = subprocess.run(['openclaw', 'cron', 'list'], capture_output=True, text=True, timeout=15)
    cron_text = result.stdout
    idle_count = cron_text.count('idle')
    ok_count = cron_text.count('ok')
    total_match = cron_text.count('cron ')
except:
    pass
lines.append(f"**Cron Jobs**: {total_match} total | ✅ OK: {ok_count} | ⚠️ Idle: {idle_count}")
if idle_count > 3:
    lines.append(f"⚠️ 警告：Idle jobs 過多（{idle_count}個），需要修復")

# 2. DB Freshness 檢查
dbs = [
    ('yfinance.db', 'yfinance', 1),
    ('tina_master.db', 'tina_master', 7),
    ('tw_history.db', 'tw_history', 2),
    ('etf.db', 'etf', 1),
]
for db_file, db_name, max_age_days in dbs:
    db_path = os.path.join(DATA_DIR, db_file)
    if not os.path.exists(db_path):
        lines.append(f"❌ {db_name}: 檔案不存在")
        continue
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        latest_date = None
        for t in tables:
            for col in ['date', 'Date', 'updated_at', 'created_at']:
                try:
                    r = c.execute(f'SELECT MAX({col}) FROM "{t}"').fetchone()[0]
                    if r and (not latest_date or str(r) > str(latest_date)):
                        latest_date = r
                except:
                    pass
        if latest_date:
            from datetime import date as dateclass
            if isinstance(latest_date, str):
                try:
                    ld = datetime.strptime(str(latest_date)[:10], '%Y-%m-%d')
                    days_old = (datetime.now() - ld).days
                    if days_old > max_age_days:
                        lines.append(f"🔴 {db_name}: 資料停在 {latest_date}（落後 {days_old} 天）")
                    else:
                        lines.append(f"✅ {db_name}: 最新 {latest_date}")
                except:
                    lines.append(f"? {db_name}: {latest_date}")
        else:
            lines.append(f"? {db_name}: 無法判斷日期")
        conn.close()
    except Exception as e:
        lines.append(f"❌ {db_name}: {e}")

# 3. 腳本數量檢查
try:
    scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py') and not f.startswith('_')]
    trash = [f for f in os.listdir(os.path.join(SCRIPTS_DIR, '_TRASH_')) if f.endswith('.py')] if os.path.exists(os.path.join(SCRIPTS_DIR, '_TRASH_')) else []
    lines.append(f"**腳本**: {len(scripts)} active | {len(trash)} in _TRASH_")
    if len(scripts) > 150:
        lines.append(f"⚠️ 腳本過多（{len(scripts)}），建議 Phase 3 清理")
except Exception as e:
    lines.append(f"❌ 腳本檢查失敗: {e}")

# 4. 系統異常標記
errors = []
if 'idle_count' in dir() and idle_count > 3:
    errors.append(f"Idle cron jobs: {idle_count}")
lines.append(f"**系統異常**: {'無 ✅' if not errors else ', '.join(errors)}")

# Send to Telegram
msg = '\n'.join(lines)
url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({'chat_id': chat, 'text': msg, 'parse_mode': 'Markdown'}).encode()
try:
    req = __import__('urllib.request').Request(url, data=data, headers={'Content-Type': 'application/json'})
    with __import__('urllib.request').urlopen(req, timeout=10):
        pass
except:
    pass

# Write log
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
with open(LOG_FILE, 'a', encoding='utf-8') as f:
    f.write(msg + '\n')

print(msg)