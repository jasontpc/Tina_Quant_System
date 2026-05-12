# -*- coding: utf-8 -*-
"""
ray_token_tracker.py — 每5小時追蹤 MiniMax Token 用量
增強版：7天平均 + 每日限額提醒
"""
import sys, json, time, sqlite3
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = "sk-cp-d1DZZxzGpsijgC4bJaTl6_mrDJp376z9iwXyRnXRq8wYZOXBKRqFL2YVSE6nVwJ0yi14yjhh6fPCwvtLT5J53KNdfLMSJgLIjfcCqTHpja08L58oTe0wztg"
DB = "ray_wisdom.db"
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ============================================================
# 寫入歷史記錄
# ============================================================
def write_history(model_name, used, total, weekly_used, weekly_total):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS token_history
        (id INTEGER PRIMARY KEY, timestamp TEXT, model TEXT, used INTEGER, total INTEGER,
         weekly_used INTEGER, weekly_total INTEGER, date TEXT)''')
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    today = time.strftime("%Y-%m-%d")
    c.execute('INSERT INTO token_history (timestamp, model, used, total, weekly_used, weekly_total, date) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (now, model_name, used, total, weekly_used, weekly_total, today))
    conn.commit()
    conn.close()

# ============================================================
# 7天平均計算
# ============================================================
def get_7day_avg(model_name):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''SELECT date, SUM(used) FROM token_history
        WHERE model=? AND date >= date('now', '-7 days')
        GROUP BY date ORDER BY date DESC''',
        (model_name,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return None, []

    daily = [(r[0], r[1]) for r in rows]
    total_used = sum(r[1] for r in daily)
    avg = total_used / len(daily) if daily else 0
    return avg, daily

# ============================================================
# 每日限額提醒
# ============================================================
def check_daily_limit(weekly_avg, weekly_total, days_left=7):
    daily_limit = weekly_total / 7 if weekly_total > 0 else 0
    projected = weekly_avg * days_left

    if projected > weekly_total * 0.8:
        return "🔴 警告：按目前用量，本週將超標！", "red"
    elif projected > weekly_total * 0.6:
        return "🟡 注意：用量高於平均，建議關注", "yellow"
    else:
        return "🟢 正常：用量在安全範圍內", "green"

# ============================================================
# 主報告
# ============================================================
def get_token_report():
    try:
        import requests
        resp = requests.get(
            "https://www.minimax.io/v1/token_plan/remains",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=15
        )
        data = resp.json()
        items = data.get("model_remains", [])

        lines = ["📊 MiniMax Token 用量（7日平均）\n"]
        alerts = []

        for item in items:
            name = item.get("model_name", "N/A")
            weekly_total = item.get("current_weekly_total_count", 0)
            weekly_used = item.get("current_weekly_usage_count", 0)

            if weekly_total == 0:
                continue

            used = item.get("current_interval_usage_count", 0)
            pct = (weekly_used / weekly_total) * 100

            # 寫入歷史
            write_history(name, used, 0, weekly_used, weekly_total)

            # 7天平均
            avg, daily = get_7day_avg(name)

            # 每日限額檢查
            days_left = 7 - time.localtime().tm_wday if time.localtime().tm_wday > 0 else 1
            status, color = check_daily_limit(avg if avg else 0, weekly_total, days_left)

            lines.append(f"┌{'─'*50}")
            lines.append(f"│ {name}")
            lines.append(f"│ 本週: {weekly_used:,} / {weekly_total:,} ({pct:.1f}%)")
            if avg is not None:
                lines.append(f"│ 7日平均: {avg:,.0f} /天")
            lines.append(f"│ 狀態: {status}")
            lines.append(f"└{'─'*50}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ Token 追蹤失敗: {str(e)}"

if __name__ == "__main__":
    print(get_token_report())