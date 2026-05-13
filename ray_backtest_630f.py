# -*- coding: utf-8 -*-
"""
ray_backtest_630_fast.py — 快速擴展回測（真實檔）
只處理真實 S&P 500 + Nasdaq 100 + SOX 成分股
"""
import sys, sqlite3, json, time, logging
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np
import pandas as pd

DB = 'ray_wisdom.db'
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_log = logging.getLogger("backtest_630f")
_log.setLevel(logging.INFO)
if not _log.handlers:
    h = logging.FileHandler(str(LOG_DIR / "ray_backtest_630f.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(h)

print("=== 630 快速回測 ===")
print()

def get_real_symbols():
    """只抓真實檔"""
    all_tickers = set()

    # S&P 500 成分
    try:
        table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        sp = table['Symbol'].tolist()
        sp = [s.replace('.', '-') for s in sp]
        all_tickers.update(sp)
        print(f"S&P 500: {len(sp)} 檔")
    except Exception as e:
        print(f"S&P 500 抓取失敗: {e}")

    # Nasdaq 100 成分
    try:
        table = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")[0]
        ndx = table['Symbol'].tolist()
        ndx = [s.replace('.', '-') for s in ndx]
        all_tickers.update(ndx)
        print(f"Nasdaq 100: {len(ndx)} 檔")
    except Exception as e:
        print(f"NDX 抓取失敗: {e}")

    # SOX 半導體（真實）
    sox_real = ["NVDA", "AMD", "INTC", "TSM", "ASML", "AMAT", "LRCX", "KLAC", "MU", "QCOM",
                "TXN", "ADI", "MCHP", "ON", "MPWR", "ENPH", "FSLR", "SMH", "SOXX"]
    all_tickers.update(sox_real)

    # 清理
    all_tickers = [t for t in all_tickers if t and len(t) <= 5 and t.isalpha() and '-' not in t and len(t) >= 2]
    return list(set(all_tickers))

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_sharpe(returns):
    if len(returns) < 5 or returns.std() == 0:
        return 0
    return returns.mean() / returns.std() * np.sqrt(252)

def calc_mdd(equity):
    peak = np.maximum.accumulate(equity)
    return abs((equity - peak) / peak).min() * 100

def backtest_one(symbol, start="2024-01-01"):
    try:
        data = yf.download(symbol, start=start, progress=False, timeout=5)
        if data.empty or len(data) < 100:
            return []

        close = data['Close'].dropna().squeeze()
        returns = close.pct_change().dropna()
        mom5 = close.pct_change(5)
        rsi = calc_rsi(close)
        ma20 = close.rolling(20).mean()

        results = []

        # Momentum 策略
        sig1 = (mom5 > 0) & (close > ma20) & (rsi < 75)
        ret1 = returns[sig1.shift(1).fillna(False)]
        if len(ret1) >= 10:
            sh = calc_sharpe(ret1)
            if sh > 0:
                eq = (1 + ret1).cumprod()
                results.append({
                    "strategy": f"MOM_5_{symbol}",
                    "indicator": "MOMENTUM",
                    "sharpe": sh,
                    "mdd": calc_mdd(eq),
                    "ret": (eq.iloc[-1] - 1) * 100,
                    "win": (ret1 > 0).sum() / len(ret1) * 100,
                    "trades": len(ret1)
                })

        # RSI2 策略
        rsi2 = calc_rsi(close, 2)
        sig2 = (rsi2 < 25) & (close > ma20)
        ret2 = returns[sig2.shift(1).fillna(False)]
        if len(ret2) >= 10:
            sh = calc_sharpe(ret2)
            if sh > 0:
                eq = (1 + ret2).cumprod()
                results.append({
                    "strategy": f"RSI2_{symbol}",
                    "indicator": "RSI2",
                    "sharpe": sh,
                    "mdd": calc_mdd(eq),
                    "ret": (eq.iloc[-1] - 1) * 100,
                    "win": (ret2 > 0).sum() / len(ret2) * 100,
                    "trades": len(ret2)
                })

        return results
    except Exception as e:
        return []

def run_fast():
    symbols = get_real_symbols()
    print(f"\n真實檔: {len(symbols)} 檔")
    print(f"目標: 630+ 檔（如果不足就只處理真實檔）\n")

    today = time.strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    written = 0
    total = len(symbols)

    for i, sym in enumerate(symbols):
        if (i + 1) % 100 == 0:
            print(f"進度: {i+1}/{total} ({written} 筆寫入)")

        results = backtest_one(sym)
        for r in results:
            c.execute(f'''INSERT INTO backtest_reports
                (timestamp, strategy_name, symbol, indicator, params, sharpe_ratio, max_drawdown, total_return, win_rate, avg_return, num_trades, passed, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (today, r["strategy"], sym, r["indicator"],
                 json.dumps({"ma20": True}),
                 round(r["sharpe"], 2), round(r["mdd"], 2), round(r["ret"], 2),
                 round(r["win"], 1), round(r["ret"] / max(r["trades"], 1), 3),
                 r["trades"], 1 if r["sharpe"] >= 1.5 else 0,
                 "630_fast"))

        if results:
            written += len(results)

    conn.commit()
    conn.close()

    # 結果
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM backtest_reports')
    total_reports = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT symbol) FROM backtest_reports')
    unique_sym = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio >= 1.5')
    high = c.fetchone()[0]
    conn.close()

    _log.info(f"完成: {total_reports} 筆, {unique_sym} 檔, {high} 高Sharpe")
    print(f"\n=== 完成 ===")
    print(f"總筆數: {total_reports}")
    print(f"獨特檔: {unique_sym}")
    print(f"高 Sharpe: {high}")
    return {"total": total_reports, "unique": unique_sym, "high": high}

if __name__ == "__main__":
    run_fast()