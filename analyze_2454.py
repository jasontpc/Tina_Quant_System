# -*- coding: utf-8 -*-
import sys, yfinance, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

sym = '2454.TW'
print(f'=== 2454 聯發科 分析 ===\n')

# Get data
t = yfinance.Ticker(sym)
info = t.fast_info
price = info.get('lastPrice') or info.get('regularMarketPrice')
prev = info.get('previousClose')
chg = ((price - prev) / prev * 100) if price and prev else 0

print(f'現在價格: {price:.0f} ({chg:+.1f}%)')

# Get historical for RSI/MA
hist = t.history(period='3mo')
if len(hist) > 14:
    closes = hist['Close'].tolist()
    highs = hist['High'].tolist()
    lows = hist['Low'].tolist()
    
    # RSI(14)
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    # SMA
    sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0
    sma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else 0
    
    # MA20偏離
    ma20_dev = ((price - sma20) / sma20 * 100) if sma20 else 0
    
    # ATR(14)
    trs = []
    for i in range(-14, 0):
        if i == -14:
            tr = highs[i] - lows[i]
        else:
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        trs.append(tr)
    atr = sum(trs) / 14
    
    # 距高點
    high_52w = max(hist['High'].tolist()[-252:]) if len(hist) >= 252 else max(hist['High'])
    from_high = ((price - high_52w) / high_52w * 100) if high_52w else 0
    
    print(f'\n技術指標:')
    print(f'  RSI(14): {rsi:.1f}')
    print(f'  SMA(20): {sma20:.0f}')
    print(f'  SMA(60): {sma60:.0f}')
    print(f'  MA20偏離: {ma20_dev:+.1f}%')
    print(f'  ATR(14): {atr:.0f}')
    print(f'  52w高點: {high_52w:.0f}')
    print(f'  距高點: {from_high:+.1f}%')
    
    # 法人動態（從 leo_institutional_flow.py 最近報告）
    print(f'\n法人動向:')
    print(f'  動能: 💹動能強 (+6.9%)')
    
    # 信號評估
    print(f'\n信號評估:')
    if rsi > 80:
        print(f'  RSI={rsi:.1f} → [!] 過熱區')
    elif rsi < 40:
        print(f'  RSI={rsi:.1f} → [?] 超賣區')
    else:
        print(f'  RSI={rsi:.1f} → [~] 中性')
    
    if price > sma20:
        print(f'  > MA20 → 偏多')
    else:
        print(f'  < MA20 → 偏空')
    
    if ma20_dev > 10:
        print(f'  MA20偏離+{ma20_dev:.1f}% → 偏離過大')
    
    if from_high > -5:
        print(f'  距高點 {from_high:+.1f}% → 接近高點')
    
    # 建議
    print(f'\n建議:')
    if rsi > 80 and chg > 5:
        print('  ⚠️ 短線過熱，追高風險高，建議觀望')
        print('  若要操作，等待拉回 RSI < 70 再考慮')
    elif rsi < 40:
        print('  RSI 超賣，可觀察是否打底')
    else:
        print('  中性，觀望為主')
    
    # 潛在虧損計算
    risk = atr * 1.5
    print(f'\n風險參考:')
    print(f'  現價: {price:.0f}')
    print(f'  1.5x ATR 止損價: {price - risk:.0f} (-{(risk/price)*100:.1f}%)')