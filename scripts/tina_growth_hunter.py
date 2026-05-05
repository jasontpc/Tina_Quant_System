import yfinance as yf
import sqlite3
import pandas as pd
import json
import sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DB = WORKSPACE / "data" / "yfinance.db"
CANDIDATES_LOG = WORKSPACE / "data" / "growth_candidates.json"

GROWTH_WATCHLIST = [
    'SOXL', 'SOXS', 'YANG', 'TQQQ', 'UPRO',
    'NVDA', 'AVGO', 'AMD', 'INTC', 'MU',
    'AMZN', 'MSFT', 'GOOGL', 'META',
    '2330.TW', '2454.TW', '2382.TW', '2317.TW',
    '3665.TW', '3034.TW', '3443.TW', '3661.TW',
    '8299.TW', '6230.TW', '6182.TW',
    '2344.TW', '6442.TW', '3450.TW', '3090.TW',
    '6515.TW', '3533.TW', '2360.TW', '2303.TW',
    '5269.TW', '4966.TW', '4977.TW', '4908.TW',
    '6515.TW', '3533.TW',
]


def compute_rsi(series, period=13):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss))


def compute_indicators(prices, highs, lows):
    close = pd.Series(prices)
    rsi = compute_rsi(close)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_s = macd_l.ewm(span=9, adjust=False).mean()
    macd_hist = macd_l - macd_s
    sma20 = close.ewm(span=20, adjust=False).mean()
    sma60 = close.ewm(span=60, adjust=False).mean()
    tr = pd.Series([max(highs[i]-lows[i], abs(highs[i]-prices[i-1]) if i>0 else 0, abs(lows[i]-prices[i-1]) if i>0 else 0) for i in range(len(prices))]).ewm(com=14, adjust=False).mean()
    return rsi, macd_hist, sma20, sma60, tr


def analyze_symbol(sym):
    try:
        tk = yf.Ticker(sym)
        h = tk.history(period='3mo')
        if len(h) < 60: return None
        prices = h['Close'].tolist()
        highs = h['High'].tolist()
        lows = h['Low'].tolist()
        volumes = h['Volume'].tolist()
        rsi, macd, sma20, sma60, tr = compute_indicators(prices, highs, lows)
        rsi_v = float(rsi.iloc[-1])
        macd_v = float(macd.iloc[-1])
        s20 = float(sma20.iloc[-1])
        s60 = float(sma60.iloc[-1])
        atr = float(tr.iloc[-1])
        price = prices[-1]
        high52 = max(highs)
        low52 = min(lows)
        avg_vol = sum(volumes[-20:])/20
        vol_ratio = volumes[-1]/avg_vol if avg_vol > 0 else 0
        chg_5d = (prices[-1]/prices[-6]-1)*100 if len(prices) >= 6 else 0
        chg_20d = (prices[-1]/prices[-21]-1)*100 if len(prices) >= 21 else 0

        score = 0
        tags = []
        if 40 <= rsi_v <= 50:
            score += 30
            tags.append('RSI進場')
        elif rsi_v < 40:
            score += 15
            tags.append('RSI超賣')
        if macd_v > 0:
            score += 25
            tags.append('MACD多頭')
        if s20 > s60:
            score += 15
            tags.append('MA多頭')
        if vol_ratio > 1.5:
            score += 10
            tags.append('放量')
        if chg_5d > 5:
            score += 10
            tags.append('5日動能')

        priority = '高度' if score >= 60 else ('觀察' if score >= 30 else '中立')

        return {
            'symbol': sym,
            'price': round(price, 2),
            'rsi': round(rsi_v, 1),
            'macd': round(macd_v, 2),
            'atr_pct': round(atr/price*100, 1),
            'sma20': round(s20, 2),
            'sma60': round(s60, 2),
            'vol_ratio': round(vol_ratio, 2),
            'chg_5d': round(chg_5d, 1),
            'chg_20d': round(chg_20d, 1),
            'dist_high': round((price-high52)/high52*100, 1),
            'dist_low': round((price-low52)/low52*100, 1),
            'score': score,
            'priority': priority,
            'tags': tags,
        }
    except:
        return None


def scan_growth():
    results = []
    for sym in GROWTH_WATCHLIST:
        d = analyze_symbol(sym)
        if d:
            results.append(d)
    return sorted(results, key=lambda x: -x['score'])


def load_previous_candidates():
    if CANDIDATES_LOG.exists():
        with open(CANDIDATES_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_candidates(candidates):
    with open(CANDIDATES_LOG, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)


def detect_new_opportunities(candidates, previous):
    new = []
    prev_dict = {c['symbol']: c for c in previous}
    for c in candidates:
        if c['symbol'] not in prev_dict:
            if c['score'] >= 40:
                new.append(c)
        else:
            old_score = prev_dict[c['symbol']]['score']
            if c['score'] - old_score >= 20:
                new.append(c)
    return new


def main():
    print('='*65)
    print('  Tina Brain 成長股海巡系統 啟動')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*65)
    print()

    print('[1/4] 掃描成長股候選...')
    results = scan_growth()

    print('[2/4] 載入歷史記錄...')
    previous = load_previous_candidates()

    print('[3/4] 偵測新機會...')
    new_opps = detect_new_opportunities(results, previous)

    print('[4/4] 生成報告...')
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    print()
    print('='*65)
    print('  Tina Brain 成長股海巡報告')
    print('  ' + now)
    print('='*65)
    print()

    if new_opps:
        print('[NEW] 新發現機會')
        for c in new_opps:
            tag_str = ' / '.join(c['tags'])
            print('  + ' + c['symbol'] + ' $' + str(c['price']) + '  Score=' + str(c['score']) + '  RSI=' + str(c['rsi']) + '  MACD=' + str(c['macd']))
            print('       Tags: ' + tag_str)
            print('       距高 ' + str(c['dist_high']) + '% / 5日 ' + str(c['chg_5d']) + '%')
        print()

    print('[TOP] 成長股排行（' + str(len(results)) + '檔）')
    print('%-10s %8s %5s %7s %5s %5s %s' % ('Symbol', 'Price', 'RSI', 'MACD', '5d%', 'Score', 'Tags'))
    print('-'*65)
    for c in results[:15]:
        tag_str = ' '.join(c['tags'][:3])
        print('%-10s $%8s %5.1f %+7.2f %5.1f%% %5d %s' % (c['symbol'], str(c['price']), c['rsi'], c['macd'], c['chg_5d'], c['score'], tag_str))
    print()

    print('[ROTATION] 板塊輪動')
    tag_scores = {}
    for c in results:
        for tag in c['tags']:
            if tag not in tag_scores:
                tag_scores[tag] = []
            tag_scores[tag].append(c['score'])
    sorted_tags = sorted(tag_scores.items(), key=lambda x: -sum(x[1])/len(x[1]))
    for tag, scores in sorted_tags[:4]:
        avg = sum(scores)/len(scores)
        print('  ' + tag + ': ' + str(len(scores)) + '檔  平均Score=' + str(round(avg)) + '')
    print()

    print('[ACTION] 行動建議')
    high = [c for c in results if c['priority'] == '高度']
    if high:
        symbols = ', '.join([c['symbol'] for c in high[:8]])
        print('  高度關注 (' + str(len(high)) + '檔): ' + symbols)
    else:
        print('  目前無高度關注標的（等RSI回調）')

    print()
    print('='*65)
    print()

    save_candidates(results)

    print('掃描結果：' + str(len(results)) + '檔')
    print('新發現：' + str(len(new_opps)) + '檔')
    print('高度關注：' + str(len(high)) + '檔')
    print('='*65)


if __name__ == '__main__':
    main()