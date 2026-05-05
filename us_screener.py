# -*- coding: utf-8 -*-
"""US Stock RSI Screener - From Local Database"""
import sys, sqlite3
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\us_history.db'

def screen():
    print('╔═══════════════════════════════════════════╗')
    print('║   US Stock RSI Screener (Local DB)     ║')
    print('╚═══════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute('SELECT symbol, name, sector, current_price, current_rsi, current_zone, high_52w, low_52w FROM stock_summary ORDER BY current_rsi ASC')
    rows = cur.fetchall()
    
    # Categorize
    zones = {'OVERSOLD': [], 'NEUTRAL_LOW': [], 'NEUTRAL': [], 'NEUTRAL_HIGH': [], 'OVERBOUGHT': [], 'EXTREME': []}
    
    for r in rows:
        sym, name, sector, price, rsi, zone, high_52w, low_52w = r
        from_high = ((price - high_52w) / high_52w * 100) if high_52w else 0
        zones[zone].append({'symbol': sym, 'name': name, 'price': price, 'rsi': rsi, 'from_high': from_high, 'high_52w': high_52w})
    
    # Report
    print('🟢 OVERSOLD（RSI < 30）:')
    print(f'{"代號":<8} {"名稱":<16} {"現價":>8} {"RSI":>6} {"距高點":>9}')
    print('-' * 50)
    for s in zones['OVERSOLD']:
        print(f'{s["symbol"]:<8} {s["name"]:<16} {s["price"]:>8.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+8.1f}%')
    if not zones['OVERSOLD']:
        print('  無')
    
    print(f'\n🟡 NEUTRAL_LOW（RSI 30-40）:')
    print(f'{"代號":<8} {"名稱":<16} {"現價":>8} {"RSI":>6} {"距高點":>9}')
    print('-' * 50)
    for s in zones['NEUTRAL_LOW']:
        print(f'{s["symbol"]:<8} {s["name"]:<16} {s["price"]:>8.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+8.1f}%')
    if not zones['NEUTRAL_LOW']:
        print('  無')
    
    print(f'\n⚪ NEUTRAL（RSI 40-60）:')
    print(f'{"代號":<8} {"名稱":<16} {"現價":>8} {"RSI":>6}')
    print('-' * 40)
    for s in zones['NEUTRAL']:
        print(f'{s["symbol"]:<8} {s["name"]:<16} {s["price"]:>8.0f} {s["rsi"]:>6.1f}')
    
    print(f'\n🔶 NEUTRAL_HIGH（RSI 60-70）:')
    for s in zones['NEUTRAL_HIGH']:
        print(f'  {s["symbol"]:<8} RSI={s["rsi"]:.1f}')
    if not zones['NEUTRAL_HIGH']:
        print('  無')
    
    print(f'\n🔴 OVERBOUGHT（RSI 70-80）:')
    for s in zones['OVERBOUGHT']:
        print(f'  {s["symbol"]:<8} RSI={s["rsi"]:.1f}')
    if not zones['OVERBOUGHT']:
        print('  無')
    
    print(f'\n💀 EXTREME（RSI > 80）:')
    print(f'{"代號":<8} {"名稱":<16} {"現價":>8} {"RSI":>6}')
    print('-' * 40)
    for s in zones['EXTREME'][:15]:
        print(f'{s["symbol"]:<8} {s["name"]:<16} {s["price"]:>8.0f} {s["rsi"]:>6.1f}')
    if len(zones['EXTREME']) > 15:
        print(f'  ... 還有 {len(zones["EXTREME"])-15} 檔')
    
    # Entry candidates
    candidates = [s for s in zones['NEUTRAL_LOW'] if s['from_high'] > -20]
    candidates.sort(key=lambda x: x['rsi'])
    
    print(f'\n🎯 進場候選（RSI < 40 + 距高點 > -20%）:')
    print(f'{"代號":<8} {"名稱":<16} {"現價":>8} {"RSI":>6} {"距高點":>9}')
    print('-' * 50)
    for s in candidates[:10]:
        print(f'{s["symbol"]:<8} {s["name"]:<16} {s["price"]:>8.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+8.1f}%')
    if not candidates:
        print('  無 — 等待 RSI < 35')
    
    conn.close()

if __name__ == '__main__':
    screen()