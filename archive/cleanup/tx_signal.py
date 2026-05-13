# -*- coding: utf-8 -*-
import sys, requests, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

# Try TWSE directly
try:
    # Get TWII from TWSE
    r = requests.get('https://www.twse.com.tw/indices/MI_5MINS_HIST?response=json&date=20260428', timeout=10)
    print('TWSE status:', r.status_code)
    if r.status_code == 200:
        print('TWSE data:', r.text[:300])
except Exception as e:
    print('TWSE error:', e)

# Check what we have from vogel indicators
db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\vogel_indicators.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Get the latest data
cur.execute('SELECT date, close, bb_upper, bb_middle, bb_lower, rsi_14, atr_14, zone FROM daily ORDER BY date DESC LIMIT 1')
row = cur.fetchone()
if row:
    print(f'\n=== TX Latest ===')
    print(f'Date: {row[0]}')
    print(f'Close: {row[1]}')
    print(f'BB Upper: {row[2]:.0f}')
    print(f'BB Middle: {row[3]:.0f}')
    print(f'BB Lower: {row[4]:.0f}')
    print(f'RSI(14): {row[5]:.1f}')
    print(f'ATR(14): {row[6]}')
    print(f'Zone: {row[7]}')
    
    close = row[1]
    bb_u = row[2]
    bb_m = row[3]
    bb_l = row[4]
    rsi = row[5]
    atr = row[6]
    
    # Check signals
    print(f'\n=== Signal Check ===')
    print(f'Close vs BB Upper: {close} vs {bb_u:.0f} -> diff: {bb_u - close:.0f}pts')
    print(f'Close vs BB Middle: {close} vs {bb_m:.0f} -> diff: {close - bb_m:.0f}pts')
    
    # SHORT signal
    if close >= bb_u:
        print('SHORT: BB Upper突破！')
    elif close <= bb_l:
        print('LONG: BB Lower觸碰！')
    else:
        print(f'NO_SIGNAL: BB區間內，等待突破')
        print(f'  SHORT需: close >= {bb_u:.0f}（差{bb_u - close:.0f}pts）')
        print(f'  LONG需: close <= {bb_l:.0f}（差{close - bb_l:.0f}pts）')

conn.close()