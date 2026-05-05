# -*- coding: utf-8 -*-
"""Maggy AI/Tech Stock Screener - Focus on AI & Technology"""
import sys, sqlite3
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\maggy_ai_tech.db'

def screen_ai_tech():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Maggy AI/Tech 智能篩選                    ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    cur.execute('''SELECT symbol, name, sector, subsector, current_price, current_rsi, 
        current_zone, high_52w, low_52w FROM stock_summary ORDER BY current_rsi ASC''')
    rows = cur.fetchall()
    
    # Categorize
    oversold = []
    neutral_low = []
    neutral = []
    overbought = []
    extreme = []
    
    for r in rows:
        sym, name, sector, subsector, price, rsi, zone, high, low = r
        from_high = ((price - high) / high * 100) if high else 0
        from_low = ((price - low) / low * 100) if low else 0
        
        item = {
            'symbol': sym, 'name': name, 'sector': sector, 'subsector': subsector,
            'price': price, 'rsi': rsi, 'zone': zone,
            'from_high': from_high, 'from_low': from_low
        }
        
        if zone == 'OVERSOLD':
            oversold.append(item)
        elif zone == 'NEUTRAL_LOW':
            neutral_low.append(item)
        elif zone == 'NEUTRAL':
            neutral.append(item)
        elif zone == 'OVERBOUGHT':
            overbought.append(item)
        else:
            extreme.append(item)
    
    # Report
    print('=== 超賣進場（RSI < 30）===\n')
    if oversold:
        print('代號     名稱              子類              現價      RSI    距高')
        print('-' * 70)
        for s in oversold:
            print(f'{s["symbol"]:<8} {s["name"][:14]:<14} {s["subsector"][:14]:<14} ${s["price"]:>7.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+7.1f}%')
    
    print(f'\n=== 低檔觀察（RSI 30-40）===\n')
    if neutral_low:
        print('代號     名稱              子類              現價      RSI    距高')
        print('-' * 70)
        for s in neutral_low:
            print(f'{s["symbol"]:<8} {s["name"][:14]:<14} {s["subsector"][:14]:<14} ${s["price"]:>7.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+7.1f}%')
    
    print(f'\n=== 中性區間（RSI 40-60）===\n')
    print('代號     名稱              子類              現價      RSI')
    print('-' * 55)
    for s in neutral[:10]:
        print(f'{s["symbol"]:<8} {s["name"][:14]:<14} {s["subsector"][:14]:<14} ${s["price"]:>7.0f} {s["rsi"]:>6.1f}')
    
    print(f'\n=== 極度過熱（RSI > 80）===\n')
    for s in extreme[:10]:
        print(f'  {s["symbol"]:<8} {s["name"][:14]:<14} RSI={s["rsi"]:>5.1f}')
    
    # Entry signals
    print('\n\n=== AI/Tech 進場信號 ===\n')
    
    entry = oversold + neutral_low
    entry.sort(key=lambda x: x['rsi'])
    
    print('優先  股票     名稱            子類              RSI   建議')
    print('-' * 65)
    priorities = [
        ('緊急', '立即進場'),
        ('進場', '符合進場'),
    ]
    
    priority_idx = 0
    for s in entry:
        if priority_idx == 0 and s['zone'] == 'NEUTRAL_LOW':
            priority_idx = 1
        icon = priorities[priority_idx][0]
        action = priorities[priority_idx][1]
        print(f'{icon:<4}  {s["symbol"]:<8} {s["name"][:14]:<14} {s["subsector"][:14]:<14} {s["rsi"]:>6.1f} {action}')
    
    # AI Sector analysis
    print('\n\n=== AI/科技類別分析 ===\n')
    
    sectors = {}
    for s in rows:
        sec = s[2]
        if sec not in sectors:
            sectors[sec] = {'count': 0, 'avg_rsi': 0, 'stocks': []}
        rsi = s[5]
        sectors[sec]['count'] += 1
        sectors[sec]['avg_rsi'] += rsi
        sectors[sec]['stocks'].append({'symbol': s[0], 'rsi': rsi})
    
    print('類別                  數量    平均RSI    狀態')
    print('-' * 45)
    for sec, data in sorted(sectors.items(), key=lambda x: x[1]['avg_rsi']):
        avg_rsi = data['avg_rsi'] / data['count']
        if avg_rsi < 40:
            status = '低檔'
        elif avg_rsi < 60:
            status = '中性'
        elif avg_rsi < 70:
            status = '偏高'
        else:
            status = '過熱'
        print(f'{sec:<20} {data["count"]:>6} {avg_rsi:>10.1f}    {status}')
    
    conn.close()

if __name__ == '__main__':
    screen_ai_tech()