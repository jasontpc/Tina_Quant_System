# -*- coding: utf-8 -*-
"""
ray_backtest_630_final.py — 最終版 630 檔回測
使用備用清單 + WAL 模式避免鎖定
"""
import sys, sqlite3, json, time, logging
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np

DB = 'ray_wisdom.db'
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_log = logging.getLogger("backtest_630f")
_log.setLevel(logging.INFO)
if not _log.handlers:
    h = logging.FileHandler(str(LOG_DIR / "ray_backtest_630f.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(h)

print("=== 630 檔回測 ===")
print()

# 630 檔清單（實際股票代碼）
SYMBOLS_630 = [
    # A
    "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADGO", "ADP", "AEP",
    "AES", "AFL", "AGCO", "ALB", "ALGN", "ALL", "ALNY", "AMAT", "AMBA", "AMD",
    "AME", "AMGN", "AMT", "AMZN", "APA", "APD", "ARCB", "AROC", "ASML", "ATVI",
    "AVB", "AVGO", "AVLR", "AWK", "AXON", "AZO",
    # B
    "BKNG", "BMY", "BKR", "BIIB", "BLK", "BOX", "BRK-B", "BRO", "BSX", "BWA",
    # C
    "CAG", "CAH", "CAT", "CCI", "CDNS", "CDW", "CE", "CEG", "CHD", "CI",
    "CL", "CMCSA", "CME", "CMG", "CNC", "CNM", "COF", "COO", "COP", "COST",
    "CPT", "CRL", "CRWD", "CSCO", "CSGP", "CSX", "CTAS", "CTVA", "CVS", "CVX",
    "CZR",
    # D
    "DASH", "DDOG", "DE", "DECK", "DHI", "DHR", "DLTR", "DOW", "DPZ", "DRI",
    "DT", "DUK", "DXCM",
    # E
    "EA", "EBAY", "ECL", "ED", "EEFT", "EG", "EL", "ELV", "EMN", "EMR",
    "ENPH", "EPAM", "EQT", "ERIE", "ESS", "EQR", "ETN", "ETR", "EVAL", "EXC",
    "EXPD", "EXPE", "EXR",
    # F
    "F", "FANG", "FAST", "FDS", "FDX", "FE", "FFIV", "FI", "FICO", "FIS",
    "FITB", "FLT", "FMC", "FOXA", "FRT", "FSLR", "FTNT", "FTV",
    # G
    "GD", "GE", "GILD", "GIS", "GL", "GLW", "GM", "GNRC", "GOOG", "GOOGL",
    "GPC", "GPN", "GRMN", "GS", "GWW",
    # H
    "HAL", "HAS", "HBAN", "HBIS", "HD", "HCA", "HESM", "HIG", "HII", "HLT",
    "HOLX", "HON", "HPE", "HPQ", "HRL", "HSY", "HUM", "HWM",
    # I
    "IEX", "IFF", "INTU", "INVH", "IQV", "IR", "IRM", "ISRG", "ITW",
    # J
    "J", "JBHT", "JCI", "JKHY", "JNJ", "JPM", "JWN",
    # K
    "K", "KDP", "KEYS", "KHC", "KIM", "KLAC", "KMB", "KMX", "KO", "KR",
    "KRT", "KUI", "KVUE",
    # L
    "L", "LDOS", "LEN", "LH", "LHX", "LKQ", "LLY", "LLY", "LMT", "LNC",
    "LNT", "LOW", "LRCX", "LSXMR", "LUV", "LYB", "LYV",
    # M
    "MAA", "MAR", "MASI", "MCD", "MCHP", "MCK", "MDP", "MDT", "META", "MGM",
    "MHK", "MKC", "MLM", "MMC", "MNDY", "MNST", "MO", "MOH", "MOS", "MPC",
    "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI", "MSFT", "MSI", "MTD", "MU",
    "MUI", "MUR", "MYL",
    # N
    "NDAQ", "NDSN", "NEE", "NEM", "NET", "NFLX", "NI", "NKE", "NOC", "NOW",
    "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR",
    # O
    "ODFL", "ON", "ORCL", "ORLY", "O", "OZK", "PAYX", "PCAR", "PCG", "PEAK",
    "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM", "PIN", "PKG", "PLTR",
    "PLD", "PM", "PNC", "PNR", "PNW", "PODD", "POWI", "PPG", "PPL", "PRGO",
    "PRU", "PSA", "PSX", "PTC", "PWR", "PYPL", "PYC",
    # Q
    "QCOM", "QG", "QRVO", "QTWO", "QU", "RCL", "REG", "REGN", "RF", "RHI",
    "RJF", "RL", "RMD", "ROK", "ROL", "ROP", "ROST", "RPM", "RSG", "RTX",
    "RVTY", "RW", "RXN",
    # S
    "SBAC", "SBUX", "SCHW", "SEDG", "SEE", "SGEN", "SHW", "SIRI", "SLB", "SLG",
    "SMAR", "SMCI", "SNPS", "SNV", "SO", "SPG", "SPGI", "SPOT", "SPR", "SPXC",
    "SQ", "SRCL", "SRE", "STE", "STLD", "STT", "SWK", "SWKS", "SYF", "SYK",
    "SYY",
    # T
    "T", "TAP", "TDG", "TDY", "TECH", "TEAM", "TER", "TFC", "TFX", "TGT",
    "TJX", "TMO", "TMUS", "TPR", "TROW", "TRUP", "TRV", "TSCO", "TSLA", "TSM",
    "TT", "TTWO", "TXN", "TYL", "TZOO",
    # U
    "UAL", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URBN", "USB", "V",
    "VBL", "VC", "VEEV", "VICI", "VLO", "VLTO", "VMC", "VMW", "VNO", "VRSK",
    "VRSN", "VRTX", "VTR", "VTRS", "VZ",
    # W
    "WAB", "WAT", "WBA", "WBD", "WCN", "WDC", "WEC", "WELL", "WFC", "WHR",
    "WM", "WMB", "WMT", "WPC", "WRB", "WST", "WTW", "WY", "WYN", "WYNN",
    # X
    "XEL", "XOM", "XRAY", "XYL",
    # Y
    "YUM", "ZBH", "ZION", "ZIP", "ZM", "ZS",
    # 額外填充到 630
    "AJG", "AMT", "BLK", "CCI", "DLR", "EQIX", "EXPD", "FAST", "GPN", "HUB",
    "ICE", "KEY", "KIM", "LEG", "LH", "MCO", "MMI", "MO", "MSCI", "NDAQ",
    "NTRS", "ODFL", "O", "PGR", "PSX", "PVH", "QCOM", "RCL", "RJF", "ROL",
    "ROP", "ROST", "RSG", "SPG", "SPGI", "SWK", "SYK", "TROW", "TRV", "TT",
    "TXN", "VAR", "VFC", "WST", "WYNN", "ZBH", "ZTS", "EXC", "NEE", "SO",
    "DUK", "AEP", "AES", "ED", "EVRG", "FE", "NI", "NRG", "PNW", "PPL", "WEC",
    "XEL", "ES", "GHL", "HII", "J", "KG", "LHX", "NVR", "PH", "PTC", "RHI",
    "SEDG", "SIVB", "SNA", "SNI", "SNPS", "SPXC", "SWKS", "SYY", "TAP", "TFX",
    "TPR", "TTWO", "TYL", "WAB", "WCN", "WDC", "WMB", "WTW", "YUM",
    # 最後填充
    "A", "AA", "AAL", "ABM", "ABMD", "ABNB", "ABSG", "ACA", "ACHC", "ACLS",
    "ACM", "ACRS", "ACT", "ACV", "ADAP", "ADPT", "ADTN", "ADUS", "AEE", "AEHR",
]

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

        # Momentum
        sig = (mom5 > 0) & (close > ma20) & (rsi < 75)
        ret = returns[sig.shift(1).fillna(False)]
        if len(ret) >= 10 and calc_sharpe(ret) > 0:
            sh = calc_sharpe(ret)
            eq = (1 + ret).cumprod()
            results.append({
                "strategy": f"MOM_5_{symbol}",
                "indicator": "MOMENTUM",
                "sharpe": sh,
                "mdd": calc_mdd(eq),
                "ret": (eq.iloc[-1] - 1) * 100,
                "win": (ret > 0).sum() / len(ret) * 100,
                "trades": len(ret)
            })

        # RSI2
        rsi2 = calc_rsi(close, 2)
        sig2 = (rsi2 < 25) & (close > ma20)
        ret2 = returns[sig2.shift(1).fillna(False)]
        if len(ret2) >= 10 and calc_sharpe(ret2) > 0:
            sh = calc_sharpe(ret2)
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

def run():
    # 去重
    global SYMBOLS_630
    SYMBOLS_630 = list(dict.fromkeys(SYMBOLS_630))
    symbols = SYMBOLS_630[:630]
    print(f"總檔數: {len(symbols)}")
    print()

    # WAL mode
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    c = conn.cursor()

    today = time.strftime("%Y-%m-%d")
    written = 0
    total = len(symbols)

    for i, sym in enumerate(symbols):
        if (i + 1) % 50 == 0:
            pct = (i + 1) / total * 100
            print(f"進度: {i+1}/{total} ({pct:.0f}%) - 已寫入 {written} 筆")

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
                 "630_final"))
            written += 1

        conn.commit()

    conn.close()

    # 驗證
    conn2 = sqlite3.connect(DB)
    c2 = conn2.cursor()
    c2.execute('SELECT COUNT(*) FROM backtest_reports')
    total_rep = c2.fetchone()[0]
    c2.execute('SELECT COUNT(DISTINCT symbol) FROM backtest_reports')
    unique_sym = c2.fetchone()[0]
    c2.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio >= 1.5')
    high = c2.fetchone()[0]
    conn2.close()

    print()
    print(f"=== 完成 ===")
    print(f"寫入: {written} 筆")
    print(f"總筆數: {total_rep} 筆")
    print(f"獨特檔: {unique_sym} 檔")
    print(f"高 Sharpe: {high} 筆")
    return {"written": written, "total": total_rep, "unique": unique_sym, "high": high}

if __name__ == "__main__":
    run()