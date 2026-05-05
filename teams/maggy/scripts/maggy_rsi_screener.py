# -*- coding: utf-8 -*-
"""Maggy RSI Screener - From Local Database"""
import sys, sqlite3
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy_rsi.db'

def screen_rsi():
    print('╔════════════════════════════════════════╗')
    print('║   Maggy 美股 RSI 資料庫篩選           ║')
    print('╚════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Get all stocks with current RSI
    cur.execute('SELECT symbol, name, current_price, current_rsi, zone, high_52w, low_52w FROM rsi_summary ORDER BY current_rsi ASC')
    rows = cur.fetchall()
    
    # Categorize
    oversold = []
    neutral_low = []
    neutral_high = []
    overbought = []
    
    for r in rows:
        sym, name, price, rsi, zone, high_52w, low_52w = r
        from_high = ((price - high_52w) / high_52w * 100) if high_52w else 0
        from_low = ((price - low_52w) / low_52w * 100) if low_52w else 0
        
        item = {'symbol': sym, 'name': name, 'price': price, 'rsi': rsi, 'zone': zone, 
                'from_high': from_high, 'from_low': from_low}
        
        if zone == 'OVERSOLD':
            oversold.append(item)
        elif rsi < 40:
            neutral_low.append(item)
        elif zone == 'OVERBOUGHT':
            overbought.append(item)
        else:
            neutral_high.append(item)
    
    # Report
    print('🟢 超賣（RSI < 30）:')
    print(f'{"代號":<6} {"名稱":<14} {"現價":>8} {"RSI":>6} {"距低點":>8}')
    print('-' * 45)
    for s in oversold:
        print(f'{s["symbol"]:<6} {s["name"]:<14} {s["price"]:>8.0f} {s["rsi"]:>6.1f} {s["from_low"]:>+7.1f}%')
    
    print(f'\n🟡 低檔區（RSI 30-40）:')
    print(f'{"代號":<6} {"名稱":<14} {"現價":>8} {"RSI":>6} {"距高點":>8}')
    print('-' * 45)
    for s in neutral_low:
        print(f'{s["symbol"]:<6} {s["name"]:<14} {s["price"]:>8.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+7.1f}%')
    
    print(f'\n🔴 過熱（RSI > 70）:')
    print(f'{"代號":<6} {"名稱":<14} {"現價":>8} {"RSI":>6} {"距高點":>8}')
    print('-' * 45)
    for s in overbought[:15]:
        print(f'{s["symbol"]:<6} {s["name"]:<14} {s["price"]:>8.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+7.1f}%')
    if len(overbought) > 15:
        print(f'  ... 還有 {len(overbought)-15} 檔')
    
    # Best entry opportunities (oversold with room to run)
    print(f'\n🎯 最佳進場機會（RSI < 40 + 距高點 > -10%）:')
    candidates = [s for s in neutral_low if s['from_high'] > -10]
    candidates.sort(key=lambda x: x['rsi'])
    print(f'{"代號":<6} {"名稱":<14} {"現價":>8} {"RSI":>6} {"距高點":>8}')
    print('-' * 45)
    for s in candidates[:10]:
        print(f'{s["symbol"]:<6} {s["name"]:<14} {s["price"]:>8.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+7.1f}%')
    
    if not candidates:
        print('  無合適進場點，等待 RSI < 35')
    
    conn.close()

if __name__ == '__main__':
    screen_rsi()