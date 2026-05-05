# -*- coding: utf-8 -*-
import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

# Check all important DB and log files
print('=== 全系統模擬交易及歷史資料庫狀態 ===\n')

# 1. Vogel TX indicators DB
db_vogel = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel_indicators.db'
if os.path.exists(db_vogel):
    import sqlite3
    conn = sqlite3.connect(db_vogel)
    cur = conn.cursor()
    cur.execute('SELECT MAX(date), COUNT(*) FROM daily')
    row = cur.fetchone()
    print(f'Vogel TX Indicators: {row[1]}筆, 最新 {row[0]}')
    conn.close()
else:
    print('Vogel TX DB: NOT FOUND')

# 2. Fugle quotes DB
db_fugle = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\fugle.db'
if os.path.exists(db_fugle):
    conn = sqlite3.connect(db_fugle)
    cur = conn.cursor()
    cur.execute('SELECT MAX(updated_at), COUNT(*) FROM quote_latest')
    row = cur.fetchone()
    print(f'Fugle 即時報價: {row[1]}筆, 更新 {row[0]}')
    conn.close()
else:
    print('Fugle DB: NOT FOUND')

# 3. TW history DB
db_tw = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_history.db'
if os.path.exists(db_tw):
    conn = sqlite3.connect(db_tw)
    cur = conn.cursor()
    cur.execute('SELECT MAX(date), COUNT(*) FROM daily_ohlcv')
    row = cur.fetchone()
    print(f'TW 歷史日K: {row[1]}筆, 最新 {row[0]}')
    conn.close()
else:
    print('TW History DB: NOT FOUND')

# 4. Trade logs
print()
logs = {
    'Nana Sim Trades': ('teams/nana/nana_sim_trades.json', 'trades'),
    'Nana Auto Trades': ('teams/nana/autonomous_trades.json', 'trades'),
    'Vogel v8 Trade Log': ('teams/vogel/vogel_trade_log_v8.json', None),
}

for name, (path, key) in logs.items():
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            print(f'{name}: {len(data)}筆')
        elif isinstance(data, dict):
            trades = data.get('trades', [])
            stats = data.get('stats', {})
            print(f'{name}: {len(trades)}筆交易, WR={stats.get("win_rate",0)*100:.0f}%, 報酬={stats.get("avg_return",0)*100:.1f}%')
            print(f'  Last updated: {data.get("last_updated", stats.get("last_updated", "unknown"))}')

# 5. Check last signal times
print()
print('=== 最後訊號時間 ===')
# Vogel current state
try:
    import sqlite3
    conn = sqlite3.connect(db_vogel)
    cur = conn.cursor()
    cur.execute('SELECT date, close, zone, rsi_14 FROM daily ORDER BY date DESC LIMIT 1')
    r = cur.fetchone()
    if r:
        print(f'TX: {r[0]} close={r[1]:.0f} zone={r[2]} RSI={r[3]:.1f}')
    conn.close()
except Exception as e:
    print(f'TX: error {e}')

print()
print('=== 今日更新完成 ===')