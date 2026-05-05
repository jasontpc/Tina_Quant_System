# -*- coding: utf-8 -*-
"""
Tina Brain - 個股特性分析與參數推薦系統 v1.1
============================================
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
DB = DATA / "yfinance.db"
CHAR_DB = DATA / "stock_characteristics.db"


def compute_characteristics(sym, days=730):
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c.execute("SELECT date, close, high, low, volume FROM daily_ohlcv WHERE symbol=? AND date>=? ORDER BY date", (sym, cutoff))
    rows = c.fetchall()
    conn.close()
    if len(rows) < 60:
        return None

    prices = [r[1] for r in rows]
    highs = [r[2] for r in rows]
    lows = [r[3] for r in rows]
    vols = [r[4] for r in rows]
    s = pd.Series(prices)
    delta = s.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    ema12 = s.ewm(span=12, adjust=False).mean()
    ema26 = s.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_sig = macd_l.ewm(span=9, adjust=False).mean()
    macd_h = macd_l - macd_sig
    ema20 = s.ewm(span=20, adjust=False).mean()
    ema60 = s.ewm(span=60, adjust=False).mean()

    rsi_list = [float(r) for r in rsi]
    macd_list = [float(m) for m in macd_h]

    rsi_below_35 = sum(1 for r in rsi_list if r < 35) / len(rsi_list) * 100
    rsi_35_50 = sum(1 for r in rsi_list if 35 <= r <= 50) / len(rsi_list) * 100
    rsi_50_70 = sum(1 for r in rsi_list if 50 <= r <= 70) / len(rsi_list) * 100
    rsi_above_70 = sum(1 for r in rsi_list if r > 70) / len(rsi_list) * 100

    ma_bull_count = 0
    for i in range(60, len(prices)):
        if float(ema20.iloc[i]) > float(ema60.iloc[i]):
            ma_bull_count += 1
    ma_bull_pct = ma_bull_count / max(1, len(prices) - 60) * 100

    macd_pos_pct = sum(1 for m in macd_list if m > 0) / len(macd_list) * 100

    chg_yy = (prices[-1] / prices[0] - 1) * 100 if len(prices) > 0 else 0

    atr_list = [max(highs[j]-lows[j], abs(highs[j]-prices[j-1]) if j > 0 else 0) for j in range(len(prices))]
    atr_avg = sum(atr_list) / len(atr_list)
    atr_pct = atr_avg / prices[-1] * 100

    returns = [0] + [(prices[i]/(prices[i-1]+0.001)-1)*100 for i in range(1, len(prices))]
    volatility = (sum(r*r for r in returns) / len(returns)) ** 0.5

    return {
        'symbol': sym,
        'rsi_below_35': round(rsi_below_35, 1),
        'rsi_35_50': round(rsi_35_50, 1),
        'rsi_50_70': round(rsi_50_70, 1),
        'rsi_above_70': round(rsi_above_70, 1),
        'macd_pos_pct': round(macd_pos_pct, 1),
        'ma_bull_pct': round(ma_bull_pct, 1),
        'chg_yy': round(chg_yy, 1),
        'atr_pct': round(atr_pct, 1),
        'volatility': round(volatility, 2),
        'latest_rsi': round(rsi_list[-1], 1),
        'latest_macd': round(macd_list[-1], 3),
        'latest_price': prices[-1],
        'data_days': len(prices),
    }


def classify_stock(char):
    if char['ma_bull_pct'] >= 90 and char['macd_pos_pct'] >= 70:
        return 'STRONG_UPTREND'
    elif char['rsi_below_35'] >= 40:
        return 'OVERSOLD_REGULAR'
    elif char['rsi_35_50'] >= 40:
        return 'MEAN_REVERSION'
    elif char['ma_bull_pct'] <= 30:
        return 'RANGE_BOUND'
    elif char['rsi_50_70'] >= 50:
        return 'TREND_FOLLOWING'
    else:
        return 'MIXED'


def recommend_team_and_params(char):
    cls = classify_stock(char)
    recs = {
        'STRONG_UPTREND': {'team': 'LEO', 'strategy': 'RSI 40-60 + 順勢追蹤', 'rsi_min': 40, 'rsi_max': 60, 'filter': 'vol_1.3x', 'note': '強趨勢股'},
        'MEAN_REVERSION': {'team': 'NANA', 'strategy': 'RSI 35-50 + MA多頭', 'rsi_min': 35, 'rsi_max': 50, 'filter': 'ma_bull', 'note': '均值回歸'},
        'OVERSOLD_REGULAR': {'team': 'LEO', 'strategy': 'RSI 25-40 + 量能確認', 'rsi_min': 25, 'rsi_max': 40, 'filter': 'vol_1.5x', 'note': '超跌反彈'},
        'TREND_FOLLOWING': {'team': 'LEO', 'strategy': 'RSI 45-65 + MACD多頭', 'rsi_min': 45, 'rsi_max': 65, 'filter': 'macd_positive', 'note': '趨勢明確'},
        'RANGE_BOUND': {'team': 'FINMAX', 'strategy': 'RSI 35-55 + 區間操作', 'rsi_min': 35, 'rsi_max': 55, 'filter': 'none', 'note': '區間整理'},
        'MIXED': {'team': 'NANA', 'strategy': 'RSI 35-50 + MA確認', 'rsi_min': 35, 'rsi_max': 50, 'filter': 'ma_bull', 'note': '混合訊號'},
    }
    return recs.get(cls, recs['MIXED'])


def init_char_db():
    conn = sqlite3.connect(str(CHAR_DB))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS stock_characteristics (
        symbol TEXT PRIMARY KEY, updated TEXT,
        rsi_below_35 REAL, rsi_35_50 REAL, rsi_50_70 REAL, rsi_above_70 REAL,
        macd_pos_pct REAL, ma_bull_pct REAL, chg_yy REAL, atr_pct REAL, volatility REAL,
        latest_rsi REAL, latest_macd REAL, latest_price REAL, data_days INTEGER,
        classification TEXT, recommended_team TEXT, recommended_params TEXT,
        rsi_min INTEGER, rsi_max INTEGER, filter TEXT, note TEXT
    )""")
    conn.commit()
    conn.close()


def save_characteristics(char, recommendation):
    conn = sqlite3.connect(str(CHAR_DB))
    c = conn.cursor()
    cls = classify_stock(char)
    c.execute("""INSERT OR REPLACE INTO stock_characteristics
        (symbol, updated, rsi_below_35, rsi_35_50, rsi_50_70, rsi_above_70,
         macd_pos_pct, ma_bull_pct, chg_yy, atr_pct, volatility,
         latest_rsi, latest_macd, latest_price, data_days,
         classification, recommended_team, recommended_params, rsi_min, rsi_max, filter, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (char['symbol'], datetime.now().strftime('%Y-%m-%d'),
         char['rsi_below_35'], char['rsi_35_50'], char['rsi_50_70'], char['rsi_above_70'],
         char['macd_pos_pct'], char['ma_bull_pct'], char['chg_yy'], char['atr_pct'], char['volatility'],
         char['latest_rsi'], char['latest_macd'], char['latest_price'], char['data_days'],
         cls, recommendation['team'], recommendation['strategy'],
         recommendation['rsi_min'], recommendation['rsi_max'],
         recommendation['filter'], recommendation['note']))
    conn.commit()
    conn.close()


def main():
    print('='*70)
    print('  Tina Brain - 個股特性分析與參數推薦系統')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*70)

    init_char_db()

    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    c.execute("SELECT DISTINCT symbol FROM daily_ohlcv ORDER BY symbol")
    all_symbols = [r[0] for r in c.fetchall()]
    conn.close()

    print('\n分析 %d 檔股票...' % len(all_symbols))

    classified = {}
    team_counts = {}

    for sym in all_symbols:
        char = compute_characteristics(sym)
        if not char:
            continue
        recommendation = recommend_team_and_params(char)
        save_characteristics(char, recommendation)

        cls = classify_stock(char)
        if cls not in classified:
            classified[cls] = []
        classified[cls].append(sym)

        team = recommendation['team']
        team_counts[team] = team_counts.get(team, 0) + 1
        print('.', end='', flush=True)

    print('\n\n【分類結果】')
    icons = {'STRONG_UPTREND': '↑↑', 'MEAN_REVERSION': '↔↔', 'OVERSOLD_REGULAR': '↓↓',
             'TREND_FOLLOWING': '→→', 'RANGE_BOUND': '↕↕', 'MIXED': '??'}
    for cls, syms in sorted(classified.items(), key=lambda x: -len(x[1])):
        print('  %s %s: %d 檔' % (icons.get(cls, '??'), cls, len(syms)))
        for s in syms[:5]:
            print('      %s' % s)
        if len(syms) > 5:
            print('      ...+%d more' % (len(syms) - 5))

    print('\n【團隊推薦統計】')
    for team, count in sorted(team_counts.items(), key=lambda x: -x[1]):
        print('  %s: %d 檔' % (team, count))

    print('\n【參數推薦範例（前10檔）】')
    conn = sqlite3.connect(str(CHAR_DB))
    c = conn.cursor()
    c.execute("SELECT symbol, classification, recommended_team, rsi_min, rsi_max, note FROM stock_characteristics ORDER BY symbol LIMIT 10")
    print('  %-12s %-20s %-8s %-5s %-5s %s' % ('Symbol', 'Classification', 'Team', 'RSImin', 'RSImax', 'Note'))
    print('  ' + '-'*70)
    for row in c.fetchall():
        print('  %-12s %-20s %-8s %-5s %-5s %s' % (row[0], row[1], row[2], row[3], row[4], row[5]))
    conn.close()

    print('\n  --> data/stock_characteristics.db')


if __name__ == '__main__':
    main()