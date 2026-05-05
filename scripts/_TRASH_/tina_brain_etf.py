import sqlite3, pandas as pd, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

ETF_DB = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\etf.db")


def compute_rsi(series, period=13):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss))


def analyze_etf_db():
    conn = sqlite3.connect(str(ETF_DB))
    c = conn.cursor()
    c.execute('SELECT symbol, name FROM etf_info ORDER BY symbol')
    etfs = c.fetchall()
    c.execute('SELECT COUNT(*), COUNT(DISTINCT symbol) FROM etf_daily')
    rows, syms = c.fetchone()
    conn.close()

    print('='*65)
    print('  Tina Brain - ETF 本地資料庫')
    print('='*65)
    print()
    print('  DB:', ETF_DB)
    print('  Rows:', rows, '/ Symbols:', syms)
    print()
    print('  ETF List:')
    for sym, name in etfs:
        conn = sqlite3.connect(str(ETF_DB))
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM etf_daily WHERE symbol=?', (sym,))
        cnt = c.fetchone()[0]
        c.execute('SELECT MAX(date) FROM etf_daily WHERE symbol=?', (sym,))
        latest = c.fetchone()[0]
        conn.close()
        print('   ', sym, ' ('+str(cnt)+' rows)', latest)
    print()
    print('='*65)


def get_etf_indicators(symbol):
    conn = sqlite3.connect(str(ETF_DB))
    c = conn.cursor()
    c.execute('SELECT date, close, volume FROM etf_daily WHERE symbol=? ORDER BY date DESC LIMIT 90', (symbol,))
    rows = c.fetchall()
    conn.close()
    if len(rows) < 30:
        return None

    closes = [float(r[1]) for r in rows][::-1]
    vols = [int(r[2]) for r in rows][::-1]
    close_s = pd.Series(closes)

    rsi_v = float(compute_rsi(close_s).iloc[-1])
    ema12 = close_s.ewm(span=12, adjust=False).mean()
    ema26 = close_s.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_s = macd_l.ewm(span=9, adjust=False).mean()
    macd_v = float((macd_l - macd_s).iloc[-1])
    sma20_v = float(close_s.ewm(span=20, adjust=False).mean().iloc[-1])
    sma60_v = float(close_s.ewm(span=60, adjust=False).mean().iloc[-1])
    price = closes[-1]
    chg_5d = (closes[-1]/closes[-6]-1)*100 if len(closes) >= 6 else 0

    return {
        'symbol': symbol,
        'price': price,
        'rsi': rsi_v,
        'macd': macd_v,
        'sma20': sma20_v,
        'sma60': sma60_v,
        'chg_5d': chg_5d,
    }


def scan_all_etfs():
    conn = sqlite3.connect(str(ETF_DB))
    c = conn.cursor()
    c.execute('SELECT symbol FROM etf_info')
    etfs = [r[0] for r in c.fetchall()]
    conn.close()

    results = []
    for sym in etfs:
        d = get_etf_indicators(sym)
        if d:
            score = 0
            if 40 <= d['rsi'] <= 50: score += 30
            elif d['rsi'] < 40: score += 15
            if d['macd'] > 0: score += 25
            if d['sma20'] > d['sma60']: score += 15
            d['score'] = score
            results.append(d)

    return sorted(results, key=lambda x: -x['score'])


if __name__ == '__main__':
    analyze_etf_db()
    print()
    print('='*65)
    print('  ETF 技術指標掃描')
    print('='*65)
    results = scan_all_etfs()
    print()
    print('%-10s %8s %5s %7s %5s %5s' % ('Symbol', 'Price', 'RSI', 'MACD', '5d%', 'Score'))
    print('-'*65)
    for d in results:
        tags = []
        if 40 <= d['rsi'] <= 50: tags.append('進場')
        if d['macd'] > 0: tags.append('多頭')
        if d['sma20'] > d['sma60']: tags.append('MA多')
        rsi_t = '🟢' if 40<=d['rsi']<=50 else ('🔵' if d['rsi']<60 else '🔴')
        macd_t = '🟢' if d['macd']>0 else '🔴'
        print('%-10s $%8.2f %5.1f%s %+7.2f%s %+5.1f%% %5d %s' % (
            d['symbol'], d['price'], d['rsi'], rsi_t, d['macd'], macd_t, d['chg_5d'], d['score'], ' '.join(tags)))

    print()
    print('='*65)
    print('  ETF DB 加入 Tina Brain 整合 ✅')
    print('='*65)