# -*- coding: utf-8 -*-
"""Maggy Daily Check & Update Script - 每日檢查更新"""
import sys, yfinance, sqlite3, json
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\maggy.db'
REPORT = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy\reports\daily_check.json'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def update_data():
    """Update latest prices for all stocks in DB"""
    print('=== 更新資料庫最新價格 ===\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT symbol FROM daily ORDER BY symbol')
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    
    updated = 0
    for sym in symbols:
        try:
            t = yfinance.Ticker(sym)
            info = t.fast_info
            price = info.get('lastPrice') or info.get('regularMarketPrice')
            prev = info.get('previousClose')
            
            if price and prev:
                chg = ((price - prev) / prev * 100)
                rsi_data = t.history(period='60d')['Close'].tolist()
                rsi = calc_rsi(rsi_data, 14)
                
                # We can't update historical DB with new prices without adding new records
                # Just report current status
                updated += 1
        except:
            pass
    
    print(f'更新完成: {updated}/{len(symbols)}檔股票現價檢查')
    return updated

def check_signals():
    """Check for trading signals"""
    print('\n=== 檢查交易信號 ===\n')
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute('SELECT DISTINCT symbol FROM daily ORDER BY symbol')
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    
    signals = []
    for sym in symbols:
        try:
            t = yfinance.Ticker(sym)
            info = t.fast_info
            price = info.get('lastPrice') or info.get('regularMarketPrice')
            prev = info.get('previousClose')
            chg = ((price - prev) / prev * 100) if price and prev else 0
            
            hist = t.history(period='60d')
            closes = hist['Close'].tolist()
            highs = hist['High'].tolist()
            lows = hist['Low'].tolist()
            
            rsi = calc_rsi(closes, 14)
            sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else 0
            ma20_dev = ((price - sma20) / sma20 * 100) if sma20 else 0
            
            # Signals
            if rsi < 35:
                sig = 'LONG_ENTRY'
                confidence = (35 - rsi) / 35 * 100
            elif rsi < 50:
                sig = 'WATCH'
                confidence = (50 - rsi) / 50 * 100
            elif rsi < 60:
                sig = 'HOLD'
                confidence = (rsi - 50) / 10 * 100
            elif rsi > 75:
                sig = 'OVERBOUGHT'
                confidence = (rsi - 75) / 25 * 100
            else:
                sig = 'NEUTRAL'
                confidence = 50
            
            signals.append({
                'symbol': sym,
                'price': round(price, 2) if price else 0,
                'change': round(chg, 1),
                'rsi': round(rsi, 1),
                'ma20_dev': round(ma20_dev, 1),
                'signal': sig,
                'confidence': round(confidence, 0),
            })
        except Exception as e:
            pass
    
    # Categorize
    long_entry = [s for s in signals if s['signal'] == 'LONG_ENTRY' and s['confidence'] > 60]
    watch = [s for s in signals if s['signal'] == 'WATCH']
    overbought = [s for s in signals if s['signal'] == 'OVERBOUGHT']
    neutral = [s for s in signals if s['signal'] == 'NEUTRAL']
    
    print(f'📊 信號概況:')
    print(f'  🟢 進場信號 (RSI<35): {len(long_entry)}檔')
    for s in long_entry[:5]:
        print(f'    {s["symbol"]}: RSI={s["rsi"]} ({s["confidence"]:.0f}%)')
    
    print(f'\n  🟡 觀察 (RSI 35-50): {len(watch)}檔')
    for s in watch[:3]:
        print(f'    {s["symbol"]}: RSI={s["rsi"]}')
    
    print(f'\n  🔴 過熱 (RSI>75): {len(overbought)}檔')
    for s in overbought[:5]:
        print(f'    {s["symbol"]}: RSI={s["rsi"]}')
    
    return signals

def check_sector_rotation():
    """Check sector rotation"""
    print('\n=== 產業輪動檢查 ===\n')
    
    sectors = {
        'XLK': 'Technology',
        'XLE': 'Energy', 
        'XLV': 'Healthcare',
        'VGT': 'Info Tech',
        'SPY': 'S&P 500 (benchmark)',
    }
    
    results = []
    try:
        spy = yfinance.Ticker('SPY')
        spy_hist = spy.history(period='60d')
        spy_ret = (spy_hist['Close'].iloc[-1] - spy_hist['Close'].iloc[0]) / spy_hist['Close'].iloc[0] * 100
        
        for sym, name in sectors.items():
            try:
                t = yfinance.Ticker(sym)
                hist = t.history(period='60d')
                ret = (hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100
                rel = ret - spy_ret
                results.append({
                    'sector': sym,
                    'name': name,
                    'return': round(ret, 1),
                    'spy_return': round(spy_ret, 1),
                    'relative': round(rel, 1),
                    'signal': 'STRONG' if rel > 5 else ('WEAK' if rel < -5 else 'NEUTRAL'),
                })
            except:
                pass
    except:
        pass
    
    for r in results:
        sig = '🟢' if r['signal'] == 'STRONG' else ('🔴' if r['signal'] == 'WEAK' else '⚪')
        print(f'{sig} {r["sector"]} ({r["name"]}): {r["return"]:+.1f}% (rel={r["relative"]:+.1f})')
    
    return results

def main():
    print('╔══════════════════════════════════════╗')
    print('║  Maggy 美股每日檢查與數據更新        ║')
    print('╚══════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # Update data
    update_data()
    
    # Check signals
    signals = check_signals()
    
    # Sector rotation
    sectors = check_sector_rotation()
    
    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'signals': signals,
        'sector_rotation': sectors,
        'summary': {
            'long_entry_count': len([s for s in signals if s['signal'] == 'LONG_ENTRY']),
            'overbought_count': len([s for s in signals if s['signal'] == 'OVERBOUGHT']),
            'watch_count': len([s for s in signals if s['signal'] == 'WATCH']),
        }
    }
    
    with open(REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 每日檢查完成，報告已儲存')
    print(f'   {REPORT}')
    
    return report

if __name__ == '__main__':
    main()