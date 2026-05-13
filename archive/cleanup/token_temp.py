# -*- coding: utf-8 -*-
import sys, time, requests, sqlite3
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

API_KEY = 'sk-cp-s-RwpSrtMhHuWDdPPS1dpYW4JvXSdR3W890ibdNp6AGGxs19bAmsahQ955b6OQTe_GGRc6iieHJB163OdegORS3DZX49cR57CdVUjj8pEAvt_EVQ8A5fAvY'
DB = 'ray_wisdom.db'

resp = requests.get('https://api.minimax.io/v1/token_plan/remains',
    headers={'Authorization': 'Bearer ' + API_KEY}, timeout=15)
data = resp.json()
items = data.get('model_remains', [])

days_passed = time.localtime().tm_wday + 1
now_str = time.strftime('%Y-%m-%d %H:%M:%S')
today = time.strftime('%Y-%m-%d')

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS token_history
    (id INTEGER PRIMARY KEY, timestamp TEXT, model TEXT, weekly_used INTEGER, weekly_total INTEGER, date TEXT)''')
for item in items:
    name = item.get('model_name', 'N/A')
    weekly_total = item.get('current_weekly_total_count', 0)
    weekly_used = item.get('current_weekly_usage_count', 0)
    if weekly_total == 0:
        continue
    c.execute('INSERT INTO token_history (timestamp, model, weekly_used, weekly_total, date) VALUES (?, ?, ?, ?, ?)',
        (now_str, name, weekly_used, weekly_total, today))
conn.commit()
conn.close()

print('')
print('='*56)
print('  MiniMax Token Tracker (5h interval)')
print('='*56)
print('Time: ' + now_str + ' (Asia/Taipei)')
print('Week: Day ' + str(days_passed) + ' of 7')
print('')

for item in items:
    name = item.get('model_name', 'N/A')
    weekly_total = item.get('current_weekly_total_count', 0)
    weekly_used = item.get('current_weekly_usage_count', 0)
    if weekly_total == 0:
        continue
    pct = (weekly_used / weekly_total) * 100
    daily_quota = weekly_total / 7.0
    daily_usage = weekly_used / days_passed if days_passed > 0 else 0
    remains = weekly_total - weekly_used
    if daily_usage > daily_quota * 1.1:
        status = '[RED] WARNING: Overspend'
    elif daily_usage > daily_quota * 0.85:
        status = '[YELLOW] CAUTION: High usage'
    else:
        status = '[GREEN] OK'
    sep = '-' * 54
    print('+' + sep)
    print('| ' + name)
    print('| Week: ' + str(weekly_used) + ' / ' + str(weekly_total) + ' (' + '%.1f' % pct + '%)')
    print('| Left: ' + str(remains))
    print('| Daily avg: ' + '%.0f' % daily_usage + ' (quota: ' + '%.0f' % daily_quota + ')')
    print('| Status: ' + status)
    print('+' + sep)
    print('')