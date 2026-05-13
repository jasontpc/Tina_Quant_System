# -*- coding: utf-8 -*-
import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\tw_history.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

symbols = ['2330', '2454', '2303', '2317', '3034', '2382', '3665', '2376', '2354']

print('=== Nana 候選股 RSI 狀態 ===')
print(f'{"代號":<6} {"RSI":>6} {"日期":<12} {"區間":<10}')
print('-' * 40)

for sym in symbols:
    cur.execute('SELECT date, rsi_value, zone FROM rsi_signals WHERE symbol=? ORDER BY date DESC LIMIT 1', (sym,))
    row = cur.fetchone()
    if row:
        print(f'{sym:<6} {row[1]:>6.1f} {str(row[0]):<12} {str(row[2]):<10}')
    else:
        print(f'{sym:<6} No data')

conn.close()