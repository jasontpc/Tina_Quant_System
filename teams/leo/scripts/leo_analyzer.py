import yfinance as yf
import json
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

MONITOR_STOCKS = {
    '2330': '台積電',
    '2454': '聯發科',
    '2317': '鴻海',
    '2379': '瑞昱',
    '2376': '技嘉',
    '2382': '廣達',
    '3665': '穎崴',
    '3034': '緯穎',
}

SIGNAL_MAP = {
    'OVERHEAT': '[!] 過熱',
    'OVERSOLD': '[+] 超賣回升',
    'BELOW_MA20': '[+] 低於MA20',
    'OVER偏离': '[!] 偏離過大',
    'NEUTRAL': '[~] 中性'
}

def analyze_stock(symbol, name):
    ticker = f'{symbol}.TW'
    h = yf.Ticker(ticker).history(period='1y')
    if len(h) < 20:
        return None
    
    closes = h['Close'].dropna()
    vol = h['Volume']
    
    cur = closes.iloc[-1]
    ma20 = closes.rolling(20).mean().iloc[-1]
    ma60 = closes.rolling(60).mean().iloc[-1] if len(closes) >= 60 else None
    ma120 = closes.rolling(120).mean().iloc[-1] if len(closes) >= 120 else None
    
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1]
    
    vol5 = vol.rolling(5).mean().iloc[-1]
    vol_now = vol.iloc[-1]
    from_high = (cur - closes.max()) / closes.max() * 100
    pos_ma20 = (cur - ma20) / ma20 * 100
    
    if rsi > 80:
        signal_key = 'OVERHEAT'
    elif rsi < 40:
        signal_key = 'OVERSOLD'
    elif cur < ma20:
        signal_key = 'BELOW_MA20'
    elif pos_ma20 > 10:
        signal_key = 'OVER偏离'
    else:
        signal_key = 'NEUTRAL'
    
    return {
        'symbol': symbol,
        'name': name,
        'price': round(cur, 2),
        'ma20': round(ma20, 2),
        'pos_ma20': round(pos_ma20, 1),
        'ma60': round(ma60, 2) if ma60 else None,
        'rsi': round(rsi, 1),
        'from_high': round(from_high, 1),
        'vol_ratio': round((vol_now / vol5) * 100, 0) if vol5 > 0 else 0,
        'signal': signal_key,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def run_leo_analyzer():
    print('=== Leo AI科技股波段分析 ===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()
    print('股票        價格      RSI    訊號       MA20偏離   距高點')
    print('-' * 65)
    
    results = []
    for symbol, name in MONITOR_STOCKS.items():
        r = analyze_stock(symbol, name)
        if r:
            results.append(r)
            sig = SIGNAL_MAP.get(r['signal'], r['signal'])
            print(f'{symbol} {name:<4s}  {r["price"]:>8.2f}  {r["rsi"]:>5.1f}  {sig:<10s}  {r["pos_ma20"]:>+6.1f}%  {r["from_high"]:>+6.1f}%')
    
    out_path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\reports\leo_analysis.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print(f'分析完成: {len(results)} 檔股票')
    return results

if __name__ == '__main__':
    run_leo_analyzer()