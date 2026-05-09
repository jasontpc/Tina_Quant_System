# -*- coding: utf-8 -*-
"""
0050 / 00631L / 00981A ETF 深度分析腳本
加入 News Trends 報告系統
"""
import yfinance as yf
import numpy as np
import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

ETF_DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\etf.db'

ETF_LIST = [
    ('0050.TW', '元大台灣50', '指數型', 0),
    ('00631L.TW', '元大台灣50正2', '槓桿型', 2),
    ('00981A.TW', '國泰5G+', '主題型', 0),
]

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

def calc_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]  # first bar, no previous close
    return np.mean(tr[-period:]) if len(tr) >= period else None

def analyze_etf(symbol, name, etype):
    """完整技術分析"""
    tk = yf.Ticker(symbol)
    h = tk.history(period='60d')
    if h is None or len(h) < 30:
        return None
    
    # 去除 NaN 價格
    h = h[h['Close'].notna()]
    if len(h) < 30:
        return None
    
    closes = h['Close'].values
    highs = h['High'].values
    lows = h['Low'].values
    volumes = h['Volume'].values
    
    # 基本價格
    price = float(closes[-1])
    prev_price = float(closes[-2]) if len(closes) > 1 else price
    chg_pct = (price - prev_price) / prev_price * 100
    
    # RSI
    rsi_14 = calc_rsi(closes, 14)
    rsi_30 = calc_rsi(closes, 30)
    
    # MA
    ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else None
    ma60 = np.mean(closes[-60:]) if len(closes) >= 60 else None
    
    # ATR
    atr = calc_atr(highs, lows, closes) if len(closes) >= 15 else None
    
    # 動量
    mom1m = (price / closes[-21] - 1) * 100 if len(closes) >= 22 else 0
    mom3m = (price / closes[-63] - 1) * 100 if len(closes) >= 64 else 0
    
    # 成交量比
    vol_ma5 = np.mean(volumes[-5:]) if len(volumes) >= 5 else np.mean(volumes)
    vol_ratio = volumes[-1] / vol_ma5 if vol_ma5 > 0 else 1
    
    # BIAS
    bias20 = (price / ma20 - 1) * 100 if ma20 else None
    
    # 區間判斷
    if rsi_14 and rsi_14 > 85:
        zone = 'OVERBOUGHT'
        signal = 'WATCH'
    elif rsi_14 and rsi_14 < 30:
        zone = 'OVERSOLD'
        signal = 'BUY'
    elif rsi_14 and rsi_14 > 70:
        zone = 'OVERBOUGHT'
        signal = 'WATCH'
    elif rsi_14 and rsi_14 < 50:
        zone = 'NEUTRAL'
        signal = 'WATCH'
    else:
        zone = 'NEUTRAL'
        signal = 'HOLD'
    
    return {
        'symbol': symbol,
        'name': name,
        'type': etype,
        'price': round(price, 2),
        'chg_pct': round(chg_pct, 2),
        'rsi_14': round(rsi_14, 1) if rsi_14 else None,
        'rsi_30': round(rsi_30, 1) if rsi_30 else None,
        'ma20': round(ma20, 2) if ma20 else None,
        'ma60': round(ma60, 2) if ma60 else None,
        'atr': round(atr, 3) if atr else None,
        'bias20': round(bias20, 1) if bias20 else None,
        'mom1m': round(mom1m, 1),
        'mom3m': round(mom3m, 1),
        'vol_ratio': round(vol_ratio, 2),
        'zone': zone,
        'signal': signal,
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }

def generate_report():
    """產出分析報告"""
    print("=" * 60)
    print(" ETF 深度技術分析 — 0050 / 00631L / 00981A")
    print(f" 時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    results = []
    for sym, name, etype, *rest in ETF_LIST:
        r = analyze_etf(sym, name, etype)
        if r:
            results.append(r)
            rsi = f"{r['rsi_14']}" if r['rsi_14'] else 'N/A'
            zone_emoji = '[OVERBOUGHT]' if r['zone'] == 'OVERBOUGHT' else '[OVERSOLD]' if r['zone'] == 'OVERSOLD' else '[NEUTRAL]'
            
            print(f"\n{r['name']} ({r['symbol']})")
            print(f"  價格: {r['price']} ({r['chg_pct']:+.2f}%)")
            print(f"  RSI(14): {rsi} {zone_emoji}")
            print(f"  MA20: {r['ma20']} | BIAS20: {r['bias20']}%")
            print(f"  動量: 1M {r['mom1m']:+.1f}% | 3M {r['mom3m']:+.1f}%")
            print(f"  ATR: {r['atr']} | 成交量比: {r['vol_ratio']}")
            print(f"  信號: [{r['signal']}]")
            if r['type'] == 2:
                print(f"  [注意] 槓桿型ETF，會加速損耗，不適合長期持有")
    
    # 綜合建議
    print(f"\n{'=' * 60}")
    print(" 綜合建議:")
    
    rsi_values = [(r['symbol'], r['rsi_14'], r['signal']) for r in results if r['rsi_14']]
    
    buy_signals = [r for r in results if r['signal'] == 'BUY']
    watch_signals = [r for r in results if r['signal'] == 'WATCH']
    
    if buy_signals:
        print(f"  進場訊號: {', '.join([r['name'] for r in buy_signals])}")
    if watch_signals:
        overbought = [r for r in watch_signals if r['rsi_14'] and r['rsi_14'] > 70]
        if overbought:
            print(f"  過熱觀望: {', '.join([r['name'] for r in overbought])}")
    
    print("\n[OK] 分析完成")
    return results

def update_db(results):
    """寫入每日報告到 News Trends DB"""
    news_db = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\news_trends.db'
    conn = sqlite3.connect(news_db)
    cur = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    for r in results:
        # 寫入 daily_trends
        hot_cats = '["ETF","macro"]'
        hot_stocks = f'["{r["symbol"].replace(".TW","")}"]'
        direction = 'bullish' if r['rsi_14'] and r['rsi_14'] > 50 else 'bearish' if r['rsi_14'] and r['rsi_14'] < 40 else 'neutral'
        
        # 簡單用 RSI 當 sentiment
        sent = (r['rsi_14'] - 50) / 50 if r['rsi_14'] else 0
        sent = max(-1, min(1, sent))
        
        headline = f"{r['name']} ({r['symbol'].replace('.TW','')}) — RSI {r['rsi_14']} [{r['zone']}]"
        content = f"價格:{r['price']} 動量1M:{r['mom1m']:+.1f}% ATR:{r['atr']} MA20:{r['ma20']}"
        
        cur.execute('''
            INSERT OR REPLACE INTO news_articles 
            (country, date, datetime, category, headline, content, sentiment, sentiment_score, source, url, related_stocks, fetched_at)
            VALUES ('TW', ?, ?, 'ETF', ?, ?, ?, 2, 'etf_analyzer', '', ?, ?)
        ''', (today, f'{today} 08:30:00', headline, content, round(sent, 3), r['symbol'].replace('.TW',''), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    
    conn.commit()
    conn.close()
    print(f"[OK] Wrote {len(results)} ETF articles to news_trends.db")

if __name__ == '__main__':
    results = generate_report()
    update_db(results)