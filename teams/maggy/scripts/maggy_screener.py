# -*- coding: utf-8 -*-
"""Maggy 美股篩選器 - v1.0"""
import sys, yfinance, sqlite3
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

# 目標股票池
WATCHLIST = {
    # ETFs
    'SPY': 'S&P 500 ETF',
    'QQQ': 'NASDAQ ETF',
    'SSO': 'S&P 500 2x槓桿',
    'QLD': 'NASDAQ 2x槓桿',
    'TQQQ': 'NASDAQ 3x槓桿',
    'SPXL': 'S&P 500 3x槓桿',
    'FANG': 'FANG+ ETF',
    'ARKK': 'ARK Innovation',
    # Mega Tech
    'NVDA': 'Nvidia',
    'AAPL': 'Apple',
    'MSFT': 'Microsoft',
    'GOOGL': 'Google',
    'AMZN': 'Amazon',
    'META': 'Meta',
    'TSLA': 'Tesla',
    # Others
    'AMD': 'AMD',
    'NFLX': 'Netflix',
    'COIN': 'Coinbase',
}

def analyze_stock(sym, name):
    try:
        t = yfinance.Ticker(sym)
        info = t.fast_info
        price = info.get('lastPrice') or info.get('regularMarketPrice')
        prev = info.get('previousClose') or info.get('regularMarketPreviousClose')
        chg = ((price - prev) / prev * 100) if price and prev else 0
        
        hist = t.history(period='3mo')
        if len(hist) < 14:
            return None
        
        closes = hist['Close'].tolist()
        highs = hist['High'].tolist()
        lows = hist['Low'].tolist()
        
        # RSI(14)
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(abs(diff) if diff < 0 else 0)
        
        avg_gain = sum(gains[-14:]) / 14
        avg_loss = sum(losses[-14:]) / 14
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        # SMA
        sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0
        sma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else 0
        ma20_dev = ((price - sma20) / sma20 * 100) if sma20 else 0
        
        # ATR(14)
        trs = []
        for i in range(1, 15):
            idx = -i
            tr = max(closes[idx] - lows[idx], highs[idx] - closes[idx-1])
            trs.append(tr)
        atr = sum(trs) / 14
        
        # 52w
        high_52w = max(hist['High'].tolist()[-252:]) if len(hist) >= 252 else max(highs)
        from_high = ((price - high_52w) / high_52w * 100) if high_52w else 0
        
        # Signals
        if rsi > 75:
            signal = 'OVERBOUGHT'
        elif rsi < 30:
            signal = 'OVERSOLD'
        elif price > sma20 and rsi < 65:
            signal = 'BULL_MA20'
        elif price < sma20:
            signal = 'BEAR_MA20'
        else:
            signal = 'NEUTRAL'
        
        return {
            'symbol': sym,
            'name': name,
            'price': price,
            'change': chg,
            'rsi': rsi,
            'sma20': sma20,
            'ma20_dev': ma20_dev,
            'atr': atr,
            'high_52w': high_52w,
            'from_high': from_high,
            'signal': signal,
        }
    except Exception as e:
        return None

def main():
    print('=== Maggy 美股波段篩選（15:36）===\n')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    results = []
    for sym, name in WATCHLIST.items():
        result = analyze_stock(sym, name)
        if result:
            results.append(result)
    
    # Sort by signal priority
    priority = {'OVERSOLD': 0, 'BULL_MA20': 1, 'NEUTRAL': 2, 'BEAR_MA20': 3, 'OVERBOUGHT': 4}
    results.sort(key=lambda x: (priority.get(x['signal'], 5), x['rsi']))
    
    print(f'{"代號":<6} {"名稱":<16} {"價格":>10} {"漲跌":>8} {"RSI":>6} {"MA20偏離":>8} {"訊號":<12}')
    print('-' * 75)
    
    for r in results:
        sig = '+' if r['change'] >= 0 else ''
        print(f"{r['symbol']:<6} {r['name']:<16} {r['price']:>10.2f} {sig}{r['change']:>6.1f}% {r['rsi']:>6.1f} {r['ma20_dev']:>+7.1f}%  {r['signal']}")

    # Summary
    oversold = [r for r in results if r['signal'] == 'OVERSOLD']
    bull = [r for r in results if r['signal'] == 'BULL_MA20']
    overbought = [r for r in results if r['signal'] == 'OVERBOUGHT']
    
    print(f'\n=== 信號概況 ===')
    print(f'🟢 超賣（觀察）: {len(oversold)} 檔')
    for r in oversold:
        print(f'  {r["symbol"]} RSI={r["rsi"]:.1f}')
    
    print(f'\n✅ 多頭MA20: {len(bull)} 檔')
    for r in bull[:5]:
        print(f'  {r["symbol"]} RSI={r["rsi"]:.1f} MA偏離={r["ma20_dev"]:.1f}%')
    
    print(f'\n🔴 過熱: {len(overbought)} 檔')
    for r in overbought[:5]:
        print(f'  {r["symbol"]} RSI={r["rsi"]:.1f}')

    print(f'\n共 {len(results)} 檔分析完成')

if __name__ == '__main__':
    main()