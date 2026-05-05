# Tina 大腦健康監控增強版 - 每小時執行
# 檢查所有 DB 更新頻率，主動發現落後問題
import sys, sqlite3, os, json, subprocess
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
SCRIPTS_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts'
token = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
chat = '1616824689'

def get_latest_date(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    latest = None
    for t in [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()][:6]:
        for col in ['date', 'Date', 'updated_at', 'created_at', 'latest_date']:
            try:
                r = c.execute(f'SELECT MAX({col}) FROM "{t}"').fetchone()[0]
                if r and (not latest or str(r) > str(latest)):
                    latest = str(r)[:10]
            except: pass
    conn.close()
    return latest

def days_old(date_str):
    if not date_str: return 999
    try:
        from datetime import date
        d = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
        return (datetime.now().date() - d).days
    except:
        return 999

lines = [f"## 🧠 Tina DB 健康監控 | {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

critical_dbs = [
    ('yfinance.db', 'yfinance', 1),
    ('macro_institutional.db', '法人數據', 3),
    ('tw_margin.db', '融資券', 3),
    ('etf.db', 'ETF', 1),
    ('tw_history.db', 'TW歷史', 2),
    ('maggy.db', 'Maggy', 5),
    ('tina_master.db', 'Tina Master', 7),
    ('reddit_sentiment.db', 'Reddit情緒', 2),
]

alerts = []
for db_file, db_name, max_age in critical_dbs:
    db_path = os.path.join(DATA_DIR, db_file)
    if not os.path.exists(db_path):
        lines.append(f"❌ {db_name}: 檔案不存在")
        alerts.append(f"缺少 {db_file}")
        continue
    latest = get_latest_date(db_path)
    age = days_old(latest)
    if age > max_age:
        lines.append(f"🔴 {db_name}: 停在 {latest}（落後 {age} 天，限制{max_age}天）")
        alerts.append(f"{db_name} 落後 {age} 天")
    else:
        lines.append(f"✅ {db_name}: {latest}（{age}天）")

lines.append(f"**異常警示**: {'無 ✅' if not alerts else ', '.join(alerts)}")

# Send Telegram
msg = '\n'.join(lines)
url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({'chat_id': chat, 'text': msg, 'parse_mode': 'Markdown'}).encode()
try:
    req = __import__('urllib.request').Request(url, data=data, headers={'Content-Type': 'application/json'})
    with __import__('urllib.request').urlopen(req, timeout=10): pass
except: pass

print(msg)