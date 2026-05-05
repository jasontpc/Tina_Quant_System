import sqlite3, json, sys, yfinance
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
DB = DATA / "yfinance.db"

# CPO/散熱產業鏈
CPO_CHAIN = {
    '散熱模組': ['6230.TW', '3324.TWO', '6278.TWO', '3653.TW', '6120.TW'],
    '風扇/馬達': ['6592.TW', '6236.TW'],
    'VC/均熱板': ['3711.TW', '6269.TW'],
    '導熱管': ['3017.TW', '2486.TW'],
    '散熱膏/材料': ['3128.TW', '4908.TW'],
    '基板/模造': ['5227.TW', '6109.TW', '6243.TW'],
}

CPO_ALL = [s for stocks in CPO_CHAIN.values() for s in stocks]
CPO_ALL.sort()

def get_db_cpo_status():
    """檢查DB中CPO個股狀態"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    results = []
    for sym in CPO_ALL:
        c.execute("SELECT COUNT(*), MAX(date), MIN(date) FROM daily_ohlcv WHERE symbol=?", (sym,))
        cnt, mx, mn = c.fetchone()
        c.execute("SELECT rsi_14, macd_hist FROM daily_ohlcv WHERE symbol=? ORDER BY date DESC LIMIT 1", (sym,))
        row = c.fetchone()
        results.append({
            'symbol': sym, 'rows': cnt, 'latest': mx, 'oldest': mn,
            'rsi': row[0] if row else None,
            'macd': row[1] if row else None,
        })
    conn.close()
    return results

def get_latest_indicators():
    """取得最新技術指標"""
    results = {}
    for sym in CPO_ALL:
        try:
            tk = yfinance.Ticker(sym)
            h = tk.history(period='60d')
            if len(h) < 30:
                results[sym] = {'error': '不足30筆'}
                continue
            prices = list(h['Close'])
            vols = list(h['Volume'])
            s = pd.Series(prices)
            delta = s.diff()
            gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])
            ema12 = s.ewm(span=12, adjust=False).mean()
            ema26 = s.ewm(span=26, adjust=False).mean()
            macd_l = ema12 - ema26
            macd_s = macd_l.ewm(span=9, adjust=False).mean()
            macd_h = float((macd_l - macd_s).iloc[-1])
            sma20 = float(s.ewm(span=20, adjust=False).mean().iloc[-1])
            sma60 = float(s.ewm(span=60, adjust=False).mean().iloc[-1])
            vol20 = pd.Series(vols).rolling(20).mean().iloc[-1]
            vol_r = vols[-1] / vol20 if vol20 > 0 else 1
            chg_5d = (prices[-1]/prices[-6]-1)*100 if len(prices) >= 6 else 0
            atr = float(pd.Series([max(h['High'].iloc[i]-h['Low'].iloc[i], abs(h['High'].iloc[i]-h['Close'].iloc[i-1]) if i>0 else 0) for i in range(len(prices))]).ewm(span=14, adjust=False).mean().iloc[-1])
            atr_pct = atr/prices[-1]*100
            results[sym] = {
                'price': prices[-1], 'rsi': rsi, 'macd': macd_h,
                'sma20': sma20, 'sma60': sma60, 'ma_bull': sma20 > sma60,
                'vol_r': vol_r, 'chg_5d': chg_5d, 'atr_pct': atr_pct
            }
        except Exception as e:
            results[sym] = {'error': str(e)[:50]}
    return results

def cpo_backtest():
    """CPO個股簡單回測"""
    print('\n【CPO 90日回測】')
    conn = sqlite3.connect(str(DB))
    results = []
    for sym in CPO_ALL:
        cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        c = conn.cursor()
        c.execute("""SELECT date, close, high, low, rsi_14 FROM daily_ohlcv
            WHERE symbol=? AND date>=? ORDER BY date""", (sym, cutoff))
        rows = list(c.fetchall())
        if len(rows) < 30:
            continue

        prices = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        lows = [r[3] for r in rows]
        rsi_list = [r[4] for r in rows]

        wins = total = 0
        for i in range(20, len(prices) - 7):
            rsi_val = rsi_list[i] if rsi_list[i] is not None else 50
            if rsi_val < 30 or rsi_val > 55:
                continue
            entry = prices[i]
            tr = max(highs[j]-lows[j] for j in range(max(0,i-13), i+1))
            atr = tr / 14
            sl = entry - atr * 1.5
            tp = entry + atr * 3.0
            for j in range(i+1, min(i+8, len(prices))):
                if prices[j] <= sl:
                    total += 1; break
                elif prices[j] >= tp:
                    wins += 1; total += 1; break

        wr = wins/total*100 if total > 0 else 0
        results.append({'symbol': sym, 'wr': wr, 'trades': total})

    conn.close()
    results.sort(key=lambda x: -x['wr'])
    print(f"  {'Symbol':<12} {'WR':>6} {'筆數':>4}")
    print(f"  {'-'*25}")
    for r in results:
        icon = '🟢' if r['wr'] >= 60 else ('🟡' if r['wr'] >= 40 else '⚪')
        print(f"  {r['symbol']:<12} {icon}{r['wr']:>5.1f}% {r['trades']:>4}")
    return results

def main():
    print('='*60)
    print('  CPO 散熱產業分析')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)

    db_status = get_db_cpo_status()
    print(f'\n【DB 覆蓋狀態】')
    in_db = [s for s in db_status if s['rows'] > 0]
    print(f"  DB已有: {len(in_db)}/{len(CPO_ALL)} 檔")
    for cat, stocks in CPO_CHAIN.items():
        covered = [s for s in stocks if any(x['symbol']==s and x['rows']>0 for x in db_status)]
        status = '✅' if len(covered) == len(stocks) else '⚠️'
        missing = [s for s in stocks if s not in covered]
        print(f"  {status} {cat}: {len(covered)}/{len(stocks)}")
        if missing:
            print(f"      缺失: {missing}")

    indics = get_latest_indicators()
    print(f'\n【CPO 個股技術面】({len(indics)} 檔)')

    buy = []
    watch = []
    for sym in CPO_ALL:
        if sym not in indics:
            print(f"  {sym}: 無數據")
            continue
        d = indics[sym]
        if 'error' in d:
            print(f"  {sym}: {d['error']}")
            continue
        rsi_i = '🔴' if d['rsi'] > 75 else ('🟢' if d['rsi'] < 40 else '🟡')
        macd_i = '▲' if d['macd'] > 0 else '▼'
        ma = '▲' if d['ma_bull'] else '▼'
        chg = f"{'+' if d['chg_5d'] > 0 else ''}{d['chg_5d']:.1f}%"
        print(f"  {sym}: ${d['price']:.2f} {chg} RSI={rsi_i}{d['rsi']:.1f} MACD={macd_i}{d['macd']:.2f} MA={ma} Vol={d['vol_r']:.1f}x")

        if 30 <= d['rsi'] <= 50 and d['macd'] > 0 and d['ma_bull']:
            buy.append(sym)
        elif d['rsi'] < 50 and d['macd'] > 0:
            watch.append(sym)

    print(f'\n【信號】')
    if buy:
        print(f"  🟢 進場候選: {', '.join(buy)}")
    else:
        print(f"  ⚪ 無進場候選")
    if watch:
        print(f"  🟡 觀望: {', '.join(watch)}")

    bk_results = cpo_backtest()


if __name__ == '__main__':
    main()