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
    # maggy.db is a known empty shell - data written to yfinance.db instead
    ('maggy.db', 'Maggy', 999),  # 999 = disabled check (design issue, not bug)
    ('yfinance.db', 'yfinance', 1),
    # margin_balance in macro_institutional.db is empty (FinMind v2 limitation)
    # - monitored via alternative check below
    ('macro_institutional.db', '法人數據', 3),
    ('etf.db', 'ETF', 1),
    ('tw_history.db', 'TW歷史', 2),
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
    # Known design issues - suppress false alerts
    if db_file == 'maggy.db':
        # maggy.db is intentionally empty - data written to yfinance.db
        # Only alert if yfinance.db is also stale (>5 days)
        yf_latest = get_latest_date(os.path.join(DATA_DIR, 'yfinance.db'))
        yf_age = days_old(yf_latest)
        if yf_age <= 5:
            lines.append(f"✅ {db_name}: {yf_latest}（yfinance.db, {yf_age}天）[Maggy data OK]")
            continue
        else:
            lines.append(f"🔴 {db_name}: Maggy系統落後{yf_age}天（yfinance.db）")
            alerts.append("Maggy 系統落後")
            continue
    elif db_file == 'macro_institutional.db' and age > max_age:
        # Check which table is the problem: institutional_daily vs margin_balance
        conn2 = sqlite3.connect(db_path)
        cur2 = conn2.cursor()
        inst_latest = cur2.execute("SELECT MAX(date) FROM institutional_daily").fetchone()[0]
        margin_latest = cur2.execute("SELECT MAX(date) FROM margin_balance").fetchone()[0]
        conn2.close()
        inst_age = days_old(inst_latest)
        margin_cnt = 0
        conn3 = sqlite3.connect(db_path)
        try:
            margin_cnt = conn3.execute("SELECT COUNT(*) FROM margin_balance").fetchone()[0]
        except: pass
        conn3.close()
        if inst_age > 3 and margin_cnt == 0:
            lines.append(f"🔴 {db_name}: 法人停在{inst_latest}({inst_age}天) + 融資券0筆[FinMind限制]")
            alerts.append(f"法人/融資券資料受限")
        elif inst_age > 3:
            lines.append(f"🔴 {db_name}: 停在{latest}（落後{age}天，限制{max_age}天）")
            alerts.append(f"{db_name} 落後 {age} 天")
        else:
            lines.append(f"✅ {db_name}: {latest}（{age}天）")
        continue
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