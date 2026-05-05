# -*- coding: utf-8 -*-
"""Sherry ETF DCA Daily Check"""
import sys, sqlite3, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\sherry_etf.db'

def daily_check():
    print('╔════════════════════════════════════════╗')
    print('║   Sherry ETF DCA 每日檢查          ║')
    print('╚════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Get current signals
    cur.execute('''SELECT symbol, name, category, current_price, current_rsi, 
        current_zone, high_52w, low_52w, yield_12m
        FROM etf_summary ORDER BY current_rsi ASC''')
    rows = cur.fetchall()
    
    # Categorize
    oversold = []
    neutral = []
    overbought = []
    
    for r in rows:
        sym, name, cat, price, rsi, zone, high, low, yld = r
        from_high = ((price - high) / high * 100) if high else 0
        from_low = ((price - low) / low * 100) if low else 0
        
        item = {
            'symbol': sym, 'name': name, 'category': cat,
            'price': price, 'rsi': rsi, 'zone': zone,
            'from_high': from_high, 'from_low': from_low,
            'yield': yld * 100 if yld else 0
        }
        
        if zone in ('OVERSOLD', 'NEUTRAL_LOW'):
            oversold.append(item)
        elif zone == 'OVERBOUGHT' or zone == 'EXTREME':
            overbought.append(item)
        else:
            neutral.append(item)
    
    # Summary
    print('=== 📊 市場概況 ===\n')
    print(f'  DCA最佳進場（RSI < 40）: {len(oversold)}檔')
    print(f'  中性區間（RSI 40-70）: {len(neutral)}檔')
    print(f'  過熱觀望（RSI > 70）: {len(overbought)}檔')
    
    # Recommendations
    print('\n\n=== 🎯 今日DCA建議 ===\n')
    
    print('🟢 定期定額（RSI < 40）:\n')
    for s in oversold:
        print(f'  {s["symbol"]}: ${s["price"]:.0f} RSI={s["rsi"]:.1f} {s["from_high"]:>+6.1f}%距高 {s["yield"]:.2f}%殖利')
    
    print('\n⚪ 中性區間（正常定投）:\n')
    safe = [s for s in neutral if s['category'] in ('Bond', 'Index')]
    for s in safe[:5]:
        print(f'  {s["symbol"]}: ${s["price"]:.0f} RSI={s["rsi"]:.1f}')
    
    print('\n🔴 建議觀望（RSI > 70）:\n')
    for s in overbought[:5]:
        print(f'  {s["symbol"]}: RSI={s["rsi"]:.1f} ⚠️')
    
    # Bond ETFs
    print('\n\n=== 📊 債券ETF（平衡配置）===\n')
    bonds = [s for s in neutral if s['category'] == 'Bond']
    for s in bonds:
        print(f'  {s["symbol"]}: ${s["price"]:.0f} RSI={s["rsi"]:.1f} 殖利率{s["yield"]:.2f}%')
    
    conn.close()
    
    # Save signal
    signal = {
        'date': datetime.now().isoformat(),
        'oversold_count': len(oversold),
        'neutral_count': len(neutral),
        'overbought_count': len(overbought),
        'dca_buy': [s['symbol'] for s in oversold],
        'dca_watch': [s['symbol'] for s in neutral[:10]],
    }
    
    with open(f'{DATA_DIR}\\sherry_signal.json', 'w', encoding='utf-8') as f:
        json.dump(signal, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 信號已儲存')

if __name__ == '__main__':
    daily_check()