# -*- coding: utf-8 -*-
"""
ray_token_tracker.py — 每5小時追蹤 MiniMax Token 用量
修復版：正確計算日均用量 + 每日限額提醒
"""
import sys, json, time, sqlite3
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = "sk-cp-s-RwpSrtMhHuWDdPPS1dpYW4JvXSdR3W890ibdNp6AGGxs19bAmsahQ955b6OQTe_GGRc6iieHJB163OdegORS3DZX49cR57CdVUjj8pEAvt_EVQ8A5fAvY"
DB = "ray_wisdom.db"
ENDPOINT = "https://api.minimax.io/v1/token_plan/remains"

# ============================================================
# 寫入歷史
# ============================================================
def write_history(model_name, weekly_used, weekly_total):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS token_history
        (id INTEGER PRIMARY KEY, timestamp TEXT, model TEXT, weekly_used INTEGER, weekly_total INTEGER, date TEXT)''')
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    today = time.strftime("%Y-%m-%d")
    c.execute('INSERT INTO token_history (timestamp, model, weekly_used, weekly_total, date) VALUES (?, ?, ?, ?, ?)',
        (now, model_name, weekly_used, weekly_total, today))
    conn.commit()
    conn.close()

# ============================================================
# 計算日均用量（從每小時追蹤記錄推估）
# ============================================================
def get_daily_avg(model_name):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 取得連續两天的 weekly_used 差值作為日用量
    c.execute('''SELECT date, weekly_used FROM token_history
        WHERE model=? AND date >= date('now', '-2 days')
        ORDER BY date DESC, timestamp DESC''',
        (model_name,))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 2:
        return None, 0

    # 計算日用量差值
    daily_usage = rows[0][1]  # 今天
    # 簡化：用 weekly_used / 已過天數
    now = time.localtime()
    day_of_week = now.tm_wday  # 0=Mon
    days_passed = day_of_week + 1 if day_of_week >= 0 else 1

    daily_avg = daily_usage / days_passed if days_passed > 0 else daily_usage
    return daily_avg, days_passed

# ============================================================
# 限額提醒（每日限額，固定總量7等分）
# ============================================================
def check_limit(weekly_used, weekly_total, days_passed):
    daily_quota = weekly_total / 7  # 原始每週總量 / 7 = 每日額度
    daily_usage = weekly_used / days_passed if days_passed > 0 else 0

    if daily_usage > daily_quota * 1.1:
        return "🔴 警告：用量超標，本週將耗盡！", "red", daily_usage, daily_quota
    elif daily_usage > daily_quota * 0.85:
        return "🟡 注意：用量偏高，建議關注", "yellow", daily_usage, daily_quota
    else:
        return "🟢 正常：用量在安全範圍內", "green", daily_usage, daily_quota

# ============================================================
# 計算天數（固定從週一開始）
# ============================================================
def calc_days_passed():
    now = time.localtime()
    # 週一=0, 週二=1, ..., 週日=6
    # 本週已過天數：tm_wday + 1（週一當天=1）
    return now.tm_wday + 1  # 週三返回3

# ============================================================
# 主報告
# ============================================================
def get_token_report():
    try:
        import requests
        resp = requests.get(
            ENDPOINT,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=15
        )
        data = resp.json()
        items = data.get("model_remains", [])

        lines = ["📊 MiniMax Token 用量（每日限額追蹤）\n"]
        days_passed = time.localtime().tm_wday + 1

        for item in items:
            name = item.get("model_name", "N/A")
            weekly_total = item.get("current_weekly_total_count", 0)
            weekly_used = item.get("current_weekly_usage_count", 0)

            if weekly_total == 0:
                continue

            pct = (weekly_used / weekly_total) * 100
            write_history(name, weekly_used, weekly_total)

            # 日均用量
            daily_avg, _ = get_daily_avg(name)
            daily_quota = weekly_total / 7
            days_passed = calc_days_passed()
            status, color, daily_rate, _ = check_limit(weekly_used, weekly_total, days_passed)

            lines.append(f"┌{'─'*52}")
            lines.append(f"│ {name}")
            lines.append(f"│ 本週: {weekly_used:,} / {weekly_total:,} ({pct:.1f}%)")
            lines.append(f"│ 已過: {days_passed} 天 (日均配額: {daily_quota:,.0f})")
            lines.append(f"│ 日均用量: {daily_rate:,.0f} (配額: {daily_quota:,.0f})")
            lines.append(f"│ 預測週末: {daily_rate*7:,.0f} / {weekly_total:,}")
            lines.append(f"│ 狀態: {status}")
            lines.append(f"└{'─'*52}")

        return "\n".join(lines)

    except Exception as e:
        return f"❌ 追蹤失敗: {str(e)}"

if __name__ == "__main__":
    print(get_token_report())