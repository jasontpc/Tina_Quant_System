# -*- coding: utf-8 -*-
"""Sherry ETF DCA Screener - Find Best DCA Opportunities"""
import sys, sqlite3
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
DB = f'{DATA_DIR}\\sherry_etf.db'

def screen_etf():
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Sherry ETF DCA Screener                    ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Get all ETFs with current data
    cur.execute('''SELECT symbol, name, category, focus, current_price, current_rsi, 
        current_zone, high_52w, low_52w, yield_12m, expense_ratio
        FROM etf_summary ORDER BY current_rsi ASC''')
    rows = cur.fetchall()
    
    # Categorize
    oversold = []
    neutral_low = []
    neutral = []
    overbought = []
    extreme = []
    
    for r in rows:
        sym, name, cat, focus, price, rsi, zone, high, low, yld, exp = r
        from_high = ((price - high) / high * 100) if high else 0
        from_low = ((price - low) / low * 100) if low else 0
        item = {
            'symbol': sym, 'name': name, 'category': cat, 'focus': focus,
            'price': price, 'rsi': rsi, 'zone': zone,
            'from_high': from_high, 'from_low': from_low,
            'yield': yld * 100 if yld else 0,
            'expense': exp * 100 if exp else 0
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
    print('=== 🟢 DCA 最佳進場區間（RSI < 40）===\n')
    candidates = oversold + neutral_low
    if candidates:
        print(f'{"代號":<8} {"名稱":<20} {"類別":<12} {"現價":>8} {"RSI":>6} {"距高":>8} {"殖利率":>8}')
        print('-' * 80)
        for s in candidates:
            print(f'{s["symbol"]:<8} {s["name"][:20]:<20} {s["category"][:12]:<12} ${s["price"]:>7.0f} {s["rsi"]:>6.1f} {s["from_high"]:>+7.1f}% {s["yield"]:>6.2f}%')
    
    print('\n=== ⚪ 中性區間（RSI 40-60）===\n')
    print(f'{"代號":<8} {"名稱":<20} {"類別":<12} {"現價":>8} {"RSI":>6} {"殖利率":>8}')
    print('-' * 65)
    for s in neutral[:15]:
        print(f'{s["symbol"]:<8} {s["name"][:20]:<20} {s["category"][:12]:<12} ${s["price"]:>7.0f} {s["rsi"]:>6.1f} {s["yield"]:>6.2f}%')
    
    print('\n\n=== 🔴 過熱區間（RSI > 70）===\n')
    hot = overbought + extreme
    for s in hot[:15]:
        icon = '💀' if s['zone'] == 'EXTREME' else '🔴'
        print(f'{icon} {s["symbol"]:<8} {s["name"][:20]:<20} RSI={s["rsi"]:>5.1f} {s["from_high"]:>+7.1f}%')
    
    # DCA Recommendations
    print('\n\n=== 🎯 DCA 建議 ===\n')
    
    print('**保守型（建議定期定額）:**')
    safe_etfs = [s for s in candidates if s['category'] in ('Bond', 'Index') or s['focus'] in ('Dividend', 'Defensive')]
    for s in safe_etfs[:5]:
        print(f'  {s["symbol"]}: ${s["price"]:.0f} RSI={s["rsi"]:.1f} 殖利率{s["yield"]:.2f}%')
    
    print('\n**成長型（建議定期定額 + 逢低加碼）:**')
    growth_etfs = [s for s in candidates if s['category'] in ('Sector', 'Index') and s['focus'] not in ('Bond',)]
    for s in growth_etfs[:5]:
        print(f'  {s["symbol"]}: ${s["price"]:.0f} RSI={s["rsi"]:.1f} {s["from_high"]:>+7.1f}%距高')
    
    print('\n**積極型（建議分批進場）:**')
    aggressive = extreme[:5]
    for s in aggressive:
        print(f'  {s["symbol"]}: ${s["price"]:.0f} RSI={s["rsi"]:.1f} ⚠️極度過熱')
    
    # Bond ETFs for portfolio balancing
    print('\n\n=== 📊 債券ETF（組閤平衡）===\n')
    bond_etfs = [s for s in rows if s[2] == 'Bond']
    print(f'{"代號":<8} {"名稱":<20} {"現價":>8} {"RSI":>6} {"殖利率":>8}')
    print('-' * 60)
    for s in bond_etfs:
        print(f'{s[0]:<8} {s[1][:20]:<20} ${s[4]:>7.0f} {s[5]:>6.1f} {s[9]*100:.2f}%' if s[9] else f'{s[0]:<8} {s[1][:20]:<20} ${s[4]:>7.0f} {s[5]:>6.1f} N/A')
    
    conn.close()

if __name__ == '__main__':
    screen_etf()