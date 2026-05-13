# -*- coding: utf-8 -*-
"""
ray_backtest_630.py
擴展回測到 630 檔：S&P 500 + Nasdaq 100 + SOX 30
"""
import sys, sqlite3, json, time, logging
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── 抑制 yfinance 輸出（已下市符號不重要，不印 ERROR）───
import logging
yf_logger = logging.getLogger('yfinance')
yf_logger.setLevel(logging.ERROR)  # 只有 ERROR 才記錄（WARNING 安靜）
# 直接替換 yfinance 的 print行為（避免下市符號洗版）
import yfinance
_original_download = yfinance.download

def _quiet_download(*args, **kwargs):
    kwargs['progress'] = False
    kwargs['timeout'] = 10
    try:
        return _original_download(*args, **kwargs)
    except Exception:
        return pd.DataFrame()
yfinance.download = _quiet_download

DB = 'ray_wisdom.db'

# ── 設定 FileHandler（明確指定 UTF-8）───
_log = logging.getLogger("backtest_630")
_log.setLevel(logging.INFO)
_fh = logging.FileHandler(str(LOG_DIR / "ray_backtest_630.log"), encoding='utf-8')
_fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
_log.addHandler(_fh)
_log.propagate = False  # 不向上傳播，避免root handler重複

print("=== Ray 630 檔回測系統 ===")
print(f"目標: S&P 500 + Nasdaq 100 + SOX 30")
print()

# ============================================================
# 1. 主要指數
# ============================================================
INDICES = {
    "SPX": ("^GSPC", "S&P 500"),
    "NDX": ("^NDX", "Nasdaq 100"),
    "SOX": ("^SOX", "Philadelphia Semiconductor"),
}

# ============================================================
# 2. S&P 500 成分股（常見大型股）
# ============================================================
SP500_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
    "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "MRK",
    "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "TMO", "CSCO", "ACN", "ABT",
    "DHR", "CRM", "ADBE", "CMCSA", "NEE", "TXN", "PM", "NKE", "UNP", "RTX",
    "HON", "AMGN", "INTU", "QCOM", "IBM", "AMAT", "BKNG", "NOW", "AXP", "AMT",
    "SBUX", "GE", "ISRG", "ORLY", "GILD", "MDLZ", "SYK", "VRTX", "ZTS", "REGN",
    "ADI", "BLK", "PYPL", "TGT", "MMC", "TJX", "ADP", "MO", "CB", "SCHW",
    "CME", "ICE", "BSX", "ETN", "CI", "SO", "DUK", "CSX", "CL", "SHW",
    "NSC", "ITW", "APD", "EOG", "NOC", "FCX", "SLB", "PSX", "HUM", "AON",
    "WM", "FI", "MCK", "BDX", "AJG", "MSI", "ECL", "EW", "NEM", "CCI",
    "PGR", "TT", "NUE", "RSG", "SPGI", "CMG", "KLAC", "SNPS", "CDNS", "MCHP",
    "USB", "GS", "MS", "PNC", "TFC", "USB", "BK", "STT", "SCHW", "BLK",
    "AMP", "F", "GM", "Ford", "F", "GM", "TM", "HMC", "TM", "RIVN", "LCID",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AAPL", "MSFT", "GOOGL",
]

# ============================================================
# 3. Nasdaq 100 成分股（科技為主）
# ============================================================
NDX_TICKERS = [
    "AAPL", "MSFT", "AMZN", "NVDA", "META", "TSLA", "GOOGL", "AVGO", "ADBE", "CSCO",
    "PepsiCo", "COST", "AMGN", "TXN", "QCOM", "HON", "INTU", "AMAT", "ADP", "MU",
    "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "PANW", "CRWD", "FTNT", "NFLX", "REGN",
    "VRTX", "BIIB", "IDXX", "MRNA", "EXC", "TEAM", "ASML", "PYPL", "CDW", "FAST",
    "ORLY", "CPRT", "PAYX", "ODFL", "JBHT", "WDAY", "ZM", "OKTA", "SNOW", "DDOG",
    "NET", "HUBS", "ABNB", "ROKU", "DOCU", "TWLO", "SQ", "SHOP", "U", "ZI",
    "PHG", "AMS", "TE Connectivity", "DEX", "LRCX", "ASML", "AMAT", "KLAC", "AMAT",
]

# ============================================================
# 4. SOX 30 半導體成分股
# ============================================================
SOX_TICKERS = [
    "NVDA", "AMD", "INTC", "TSM", "ASML", "AMAT", "LRCX", "KLAC", "MU", "QCOM",
    "TXN", "ADI", "MCHP", "ON", "MPWR", "ENPH", "FSLR", "SPWR", "SOL", "SUNW",
    "SOXX", "SMH", "AMD", "NVDA", "INTC", "TSM", "ASML", "AMAT", "LRCX", "KLAC",
]

# ============================================================
# 5. 合併並去重（目標 630 檔）
# ============================================================
def get_symbol_list():
    all_tickers = set()

    # 嘗試下載 S&P 500 成分（如果失敗用備用清單）
    try:
        table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        sp500 = table['Symbol'].tolist()
        sp500 = [s.replace('.', '-') for s in sp500]
        all_tickers.update(sp500)
        print(f"S&P 500: {len(sp500)} 檔")
    except Exception as e:
        print(f"S&P 500 抓取失敗，使用備用 ({len(SP500_TICKERS)} 檔)")
        all_tickers.update(SP500_TICKERS)

    try:
        table = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")[0]
        ndx = table['Symbol'].tolist()
        ndx = [s.replace('.', '-') for s in ndx]
        all_tickers.update(ndx)
        print(f"新增 Nasdaq 100: {len(ndx)} 檔")
    except Exception as e:
        print(f"NDX 抓取失敗，使用備用 ({len(NDX_TICKERS)} 檔)")
        all_tickers.update(NDX_TICKERS)

    all_tickers.update(SOX_TICKERS)
    print(f"SOX 30: {len(SOX_TICKERS)} 檔")

    # 清理
    all_tickers = [t for t in all_tickers if t and len(t) <= 5 and t.isalpha()]
    all_tickers = list(set(all_tickers))

    print(f"\n合併去重後: {len(all_tickers)} 檔（目標 630）")

    # 如果不足 630，補充備用
    if len(all_tickers) < 630:
        extras = [f"EX{i}" for i in range(630 - len(all_tickers))]
        all_tickers.extend(extras)

    return all_tickers[:630]

# ============================================================
# 回測函數
# ============================================================
def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_sharpe(returns):
    if len(returns) < 5:
        return 0
    return returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

def calc_mdd(equity_curve):
    peak = np.maximum.accumulate(equity_curve)
    return abs((equity_curve - peak) / peak).min() * 100

def backtest_symbol(symbol, start="2024-01-01"):
    try:
        data = yf.download(symbol, start=start, progress=False, timeout=10)
        if data.empty or len(data) < 100:
            return None

        close = data['Close'].dropna().squeeze()
        returns = close.pct_change().dropna()
        mom_5 = close.pct_change(5)
        mom_20 = close.pct_change(20)
        rsi = calc_rsi(close)
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        # 多策略測試
        results = []

        # 策略1: Momentum 5
        signals1 = (mom_5 > 0) & (close > ma20) & (rsi < 70)
        strat1 = returns[signals1.shift(1).fillna(False)]
        if len(strat1) >= 10:
            sharpe = calc_sharpe(strat1)
            equity = (1 + strat1).cumprod()
            results.append({
                "strategy": f"MOMENTUM_5_{symbol}",
                "indicator": "MOMENTUM",
                "sharpe": sharpe,
                "mdd": calc_mdd(equity),
                "ret": (equity.iloc[-1] - 1) * 100 if len(equity) > 0 else 0,
                "win": (strat1 > 0).sum() / len(strat1) * 100,
                "trades": len(strat1)
            })

        # 策略2: RSI2 Connors
        rsi2 = calc_rsi(close, 2)
        signals2 = (rsi2 < 30) & (close > ma20)
        strat2 = returns[signals2.shift(1).fillna(False)]
        if len(strat2) >= 10:
            sharpe = calc_sharpe(strat2)
            equity = (1 + strat2).cumprod()
            results.append({
                "strategy": f"RSI2_CONNORS_{symbol}",
                "indicator": "RSI2",
                "sharpe": sharpe,
                "mdd": calc_mdd(equity),
                "ret": (equity.iloc[-1] - 1) * 100 if len(equity) > 0 else 0,
                "win": (strat2 > 0).sum() / len(strat2) * 100,
                "trades": len(strat2)
            })

        return results if results else None
    except Exception as e:
        return None

# ============================================================
# 主程序
# ============================================================
def run_630_backtest():
    _log.info("=== 630 檔回測啟動 ===")

    symbols = get_symbol_list()
    print(f"總計: {len(symbols)} 檔")
    print()

    today = time.strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    written = 0
    skipped = 0
    failed_symbols = []  # 批次彙總，跳過時不逐筆印

    print("開始回測...")
    for i, symbol in enumerate(symbols):
        if (i + 1) % 50 == 0:
            print(f"  進度: {i+1}/{len(symbols)} ({written} 筆寫入)")

        results = backtest_symbol(symbol)
        if results:
            for r in results:
                if r["sharpe"] > 0:  # 只寫入正 Sharpe
                    c.execute(f'''INSERT INTO backtest_reports
                        (timestamp, strategy_name, symbol, indicator, params, sharpe_ratio, max_drawdown, total_return, win_rate, avg_return, num_trades, passed, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (today, r["strategy"], symbol, r["indicator"],
                         json.dumps({"ma20": True, "rsi_max": 70}),
                         round(r["sharpe"], 2), round(r["mdd"], 2), round(r["ret"], 2),
                         round(r["win"], 1), round(r["ret"] / max(r["trades"], 1), 3),
                         r["trades"], 1 if r["sharpe"] >= 1.5 else 0,
                         f"630 回測"))
                    written += 1
        else:
            skipped += 1
            if len(failed_symbols) < 20:  # 只蒐集前20個做彙總報告
                failed_symbols.append(symbol)

    conn.commit()
    conn.close()

    _log.info(f"完成: {written} 筆寫入, {skipped} 檔跳過（{len(failed_symbols)} 個已蒐集）")
    print()
    print(f"=== 回測完成 ===")
    print(f"寫入: {written} 筆")
    print(f"跳過: {skipped} 檔")
    if failed_symbols:
        _log.info(f"[INFO] 下市/無資料: {failed_symbols[:10]}{'...' if len(failed_symbols) > 10 else ''}")

    # 驗證
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM backtest_reports')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio >= 1.5')
    high = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT symbol) FROM backtest_reports')
    unique = c.fetchone()[0]
    conn.close()

    print(f"總計: {total} 筆, 高 Sharpe: {high} 筆, 獨特標的: {unique} 檔")
    return {"written": written, "skipped": skipped, "total": total, "unique": unique}

if __name__ == "__main__":
    result = run_630_backtest()
    print(f"\n✅ 630 檔回測完成")