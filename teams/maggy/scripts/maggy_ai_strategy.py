# -*- coding: utf-8 -*-
"""Maggy AI/Tech Core Strategy - US Stock Swing Trading System"""
import sys, sqlite3, json, yfinance
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
AI_DB = f'{DATA_DIR}\\maggy_ai_tech.db'
CONFIG = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\maggy_config.json'

def analyze_and_recommend():
    print('╔══════════════════════════════════════════════════════════════╗')
    print('║     Maggy AI/Tech 波段交易分析 & 建議              ║')
    print('╚══════════════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # Load AI/Tech database
    conn = sqlite3.connect(AI_DB)
    cur = conn.cursor()
    
    # Get all stocks
    cur.execute('''SELECT symbol, name, sector, subsector, current_price, current_rsi, 
        current_zone, high_52w, low_52w FROM stock_summary ORDER BY current_rsi ASC''')
    rows = cur.fetchall()
    
    # Categorize
    oversold = []
    neutral_low = []
    neutral = []
    hot = []
    
    for r in rows:
        sym, name, sector, subsector, price, rsi, zone, high, low = r
        from_high = ((price - high) / high * 100) if high else 0
        from_low = ((price - low) / low * 100) if low else 0
        
        item = {
            'symbol': sym, 'name': name, 'sector': sector, 'subsector': subsector,
            'price': price, 'rsi': rsi, 'zone': zone,
            'from_high': from_high, 'from_low': from_low,
            'distance': from_high  # higher = more upside potential
        }
        
        if zone == 'OVERSOLD':
            oversold.append(item)
        elif zone == 'NEUTRAL_LOW':
            neutral_low.append(item)
        elif zone in ('OVERBOUGHT', 'EXTREME'):
            hot.append(item)
        else:
            neutral.append(item)
    
    # Get live prices for key stocks
    def get_live_data(sym, price, rsi):
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='5d')
            if len(hist) > 0:
                return price, rsi
        except:
            pass
        return price, rsi
    
    # Analyze and rank entry candidates
    print('=== 🎯 進場評估分析 ===\n')
    
    entry_candidates = oversold + neutral_low
    entry_candidates.sort(key=lambda x: (x['rsi'], x['distance']), reverse=True)
    
    print(f'{'優先':<4} {'股票':<8} {'名稱':<14} {'RSI':>6} {'現價':>8} {'空間':>8} {'評估'}')
    print('-' * 75)
    
    priority_labels = [
        ('🔥 緊急', '嚴重超賣，，立即進場'),
        ('✅ 進場', '符合進場條件'),
        ('🔶 觀望', '接近進場，可觀察'),
    ]
    
    idx = 0
    for i, s in enumerate(entry_candidates):
        if i == 0 and s['zone'] == 'NEUTRAL_LOW':
            idx = 1
        if i == 0:
            idx = 0
        elif i > 0 and idx == 0:
            idx = 1 if s['zone'] == 'NEUTRAL_LOW' else 0
        
        icon, action = priority_labels[idx]
        
        # Upside calculation: how much to RSI 65
        # This is approximate
        upside = s['from_low']
        
        print(f'{icon:<4} {s["symbol"]:<8} {s["name"][:14]:<14} {s["rsi"]:>6.1f} ${s["price"]:>7.0f} {upside:>+7.1f}%  {action}')
    
    # Strategy recommendations
    print('\n\n=== 📊 策略評估 ===\n')
    
    # Top picks
    print('**首選進場（RSI < 35）：**\n')
    for s in oversold[:3]:
        print(f'  {s["symbol"]} {s["name"]}: RSI={s["rsi"]:.1f} 空間={s["from_low"]:+.1f}%')
    
    print('\n**次選觀察（RSI 35-40）：**\n')
    for s in neutral_low[:3]:
        print(f'  {s["symbol"]} {s["name"]}: RSI={s["rsi"]:.1f} 空間={s["from_low"]:+.1f}%')
    
    # Category analysis
    print('\n\n=== 📈 AI/科技類別評估 ===\n')
    
    sectors = {}
    for r in rows:
        sym, name, sector, subsector, price, rsi, zone, high, low = r
        if sector not in sectors:
            sectors[sector] = []
        sectors[sector].append({'name': name, 'rsi': rsi, 'zone': zone})
    
    for sec, stocks in sorted(sectors.items(), key=lambda x: sum(s['rsi'] for s in x[1]) / len(x[1])):
        avg_rsi = sum(s['rsi'] for s in stocks) / len(stocks)
        min_rsi = min(s['rsi'] for s in stocks)
        max_rsi = max(s['rsi'] for s in stocks)
        
        # Score
        if avg_rsi < 35:
            score = '🟢 極佳'
        elif avg_rsi < 45:
            score = '✅ 良好'
        elif avg_rsi < 55:
            score = '⚪ 中性'
        elif avg_rsi < 70:
            score = '🔶 偏高'
        else:
            score = '🔴 過熱'
        
        best = min(stocks, key=lambda x: x['rsi'])
        
        print(f'{sec}: {score} (avg={avg_rsi:.1f}, range={min_rsi:.1f}~{max_rsi:.1f})')
        print(f'   最佳: {best["name"]} RSI={best["rsi"]:.1f}')
    
    # Recommended portfolio
    print('\n\n=== 💼 建議組合 ===\n')
    
    print('**核心倉位（RSI < 35）：**\n')
    for s in oversold[:3]:
        allocation = 20  # %
        print(f'  {s["symbol"]} {s["name"]}: 20% @ RSI={s["rsi"]:.1f}')
    
    print('\n**衛星倉位（RSI 35-45）：**\n')
    for s in neutral_low[:3]:
        allocation = 10  # %
        print(f'  {s["symbol"]} {s["name"]}: 10% @ RSI={s["rsi"]:.1f}')
    
    print('\n**觀望倉位（等待 RSI < 35）：**\n')
    hot.sort(key=lambda x: x['rsi'])
    for s in hot[:5]:
        print(f'  {s["symbol"]} {s["name"]}: RSI={s["rsi"]:.1f} ⚠️過熱')
    
    # Save analysis
    analysis = {
        'date': datetime.now().isoformat(),
        'candidates': entry_candidates[:10],
        'top_picks': [{'symbol': s['symbol'], 'name': s['name'], 'rsi': s['rsi'], 'action': action} 
                       for s, (_, action) in zip(oversold[:3], priority_labels[:1] * 3)],
        'sectors': {sec: {'avg_rsi': sum(s['rsi'] for s in stocks) / len(stocks),
                     'count': len(stocks)} for sec, stocks in sectors.items()}
    }
    
    with open(f'{DATA_DIR}\\maggy_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    conn.close()
    
    print(f'\n✅ 分析已儲存')

if __name__ == '__main__':
    analyze_and_recommend()