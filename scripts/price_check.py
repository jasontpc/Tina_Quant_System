# -*- coding: utf-8 -*-
"""
Price Verification System v2
 Checks stock prices for anomalies and alerts
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
from datetime import datetime

# Stocks to monitor
MONITOR = [
    ('2382.TW', '2382 廣達', 'portfolio'),
    ('00713.TW', '00713 高息低波', 'portfolio'),
    ('2330.TW', '2330 台積電', 'core'),
    ('2454.TW', '2454 聯發科', 'core'),
    ('2317.TW', '2317 鴻海', 'core'),
    ('NVDA', 'NVDA', 'us_core'),
    ('MSFT', 'MSFT', 'us_core'),
    ('META', 'META', 'us_core'),
    ('AAPL', 'AAPL', 'us_core'),
    ('GOOGL', 'GOOGL', 'us_core'),
    ('TSLA', 'TSLA', 'us_growth'),
    ('AMD', 'AMD', 'us_growth'),
    ('AMZN', 'AMZN', 'us_growth'),
    ('SPY', 'SPY', 'etf'),
    ('QQQ', 'QQQ', 'etf'),
]

def calc_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).iloc[-1]

def check_stock(symbol, name, category):
    """Check a single stock"""
    try:
        t = yf.Ticker(symbol)
        h = t.history(period='3mo')
        if h.empty:
            return None
        
        close = h['Close']
        
        # Calculate RSI
        rsi = calc_rsi(close)
        
        # 5D momentum
        if len(close) >= 6:
            mom5d = ((close.iloc[-1] / close.iloc[-6]) - 1) * 100
        else:
            mom5d = 0
        
        # MA20 and BIAS
        ma20 = close.rolling(20).mean().iloc[-1]
        bias20 = ((close.iloc[-1] / ma20) - 1) * 100
        
        # Zone
        if rsi > 70:
            zone = 'OVERBOUGHT'
        elif rsi < 35:
            zone = 'OVERSOLD'
        else:
            zone = 'NEUTRAL'
        
        alerts = []
        if rsi > 85:
            alerts.append('RSI EXTREME')
        elif rsi > 75:
            alerts.append('RSI HIGH')
        if mom5d > 15:
            alerts.append('5D HOT')
        elif mom5d < -10:
            alerts.append('5D COLD')
        
        return {
            'name': name,
            'price': round(close.iloc[-1], 2),
            'rsi': round(rsi, 1),
            'bias20': round(bias20, 1),
            'mom5d': round(mom5d, 1),
            'zone': zone,
            'alerts': alerts
        }
    except Exception as e:
        return {'name': name, 'error': str(e)}

def main():
    print('=' * 65)
    print('PRICE VERIFICATION SYSTEM')
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('=' * 65)
    
    results = []
    for sym, name, cat in MONITOR:
        r = check_stock(sym, name, cat)
        if r:
            results.append(r)
    
    # Group and print
    cats = ['portfolio', 'core', 'us_core', 'us_growth', 'etf']
    cat_names = {'portfolio': '【Jo 持倉】', 'core': '【台灣核心】', 
                  'us_core': '【美股核心】', 'us_growth': '【美股成長】', 'etf': '【ETF】'}
    
    for cat in cats:
        cat_results = [r for r in results if r.get('name') and 
                       any(name for s, name, c in MONITOR if c == cat and r['name'] == name)]
        # Build mapping
        name_to_cat = {name: c for sym, name, c in MONITOR}
        cat_results = [r for r in results if name_to_cat.get(r['name']) == cat]
        if not cat_results:
            continue
        
        print()
        print(cat_names[cat])
        print('-' * 65)
        
        for r in cat_results:
            if 'error' in r:
                print(f"  {r['name']}: ERROR - {r['error']}")
                continue
            
            icon = {'OVERBOUGHT': '🔴', 'OVERSOLD': '🟢', 'NEUTRAL': '➡️'}[r['zone']]
            alerts_str = ''
            if r.get('alerts'):
                alerts_str = ' ⚠️' + ','.join(r['alerts'])
            
            print(f"  {r['name']:<12} ${r['price']:>9.2f} RSI={r['rsi']:>5.1f} {icon}{r['zone']:<11} BIAS={r['bias20']:>+5.1f}% 5D={r['mom5d']:>+5.1f}%{alerts_str}")
    
    # Alert summary
    print()
    print('=' * 65)
    print('ALERT SUMMARY')
    print('=' * 65)
    
    all_alerts = []
    for r in results:
        if 'error' not in r and r.get('alerts'):
            for a in r['alerts']:
                all_alerts.append(f"{r['name']}: {a}")
    
    if all_alerts:
        for a in all_alerts:
            print(f"  ⚠️ {a}")
    else:
        print("  ✅ All prices normal - no critical alerts")
    
    print(f"\nTotal: {len(results)} stocks checked")
    print('=' * 65)
    
    return len(all_alerts)

if __name__ == '__main__':
    alert_count = main()
    sys.exit(0 if alert_count == 0 else 1)