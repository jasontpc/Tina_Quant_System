# -*- coding: utf-8 -*-
import sys, yfinance, sqlite3
sys.path.insert(0, r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts')
from finmind_safe import get_stock_price, get_stock_info

sys.stdout.reconfigure(encoding='utf-8')

# Nana candidates (TW)
symbols_tw = ['2330.TW', '2454.TW', '2303.TW', '2317.TW', '3034.TW', '2382.TW', '3665.TW', '2376.TW', '2354.TW']

names = {'2330.TW':'台積電','2454.TW':'聯發科','2303.TW':'聯電','2317.TW':'鴻海',
         '3034.TW':'緯穎','2382.TW':'廣達','3665.TW':'穎崴','2376.TW':'技嘉','2354.TW':'華天'}

print('=== Nana 候選個股即時報價（yfinance）===')
print('代碼     名稱              價格      漲跌%     RSI14')
print('-' * 50)

for sym in symbols_tw:
    try:
        ticker = yfinance.Ticker(sym)
        info = ticker.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        
        # RSI
        h = ticker.history(period='3mo')
        c = h['Close']
        delta = c.diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1] if len(c) > 14 else 50
        
        print(f'{sym.replace(".TW",""):<6} {names.get(sym,""):<10} {price:>10.2f} {chg:>+7.1f}% {rsi:>7.1f}')
    except Exception as e:
        print(f'{sym.replace(".TW",""):<6} {names.get(sym,""):<10} error: {e}')

print()

# Check market with finmind_safe
try:
    d = get_stock_price('2330', '2026-04-29', '2026-04-30')
    if d.get('data'):
        latest = d['data'][-1]
        date_str = latest.get('date', '')
        close_str = str(latest.get('close', ''))
        print('TWII check (via finmind_safe): ' + date_str + ' close=' + close_str)
except Exception as e:
    print('finmind_safe check: ' + str(e))

print()
print('[Done]')