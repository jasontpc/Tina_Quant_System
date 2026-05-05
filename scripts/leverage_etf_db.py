# -*- coding: utf-8 -*-
"""
Leveraged ETF Daily Database Builder
自動更新美股槓桿 ETF 資料庫
Target: 3x/2x/-3x Leveraged ETFs (US)

Usage:
    python leverage_etf_db.py           # daily update (incremental)
    python leverage_etf_db.py --full      # full refresh (max history)
    python leverage_etf_db.py --test      # test with 3 ETFs
"""
import sys, os, time, sqlite3, logging
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

import numpy as np
import yfinance as yf

# ─── Config ──────────────────────────────────────────────────────────────────
DATA_DIR   = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data")
DB_PATH    = DATA_DIR / "leverage_etf.db"
CSV_PATH   = DATA_DIR / "leverage_etf_database.csv"
LOG_PATH   = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\logs\leverage_etf_update.log")
FULL_REFRESH = "--full" in sys.argv or "--reset" in sys.argv
TEST_MODE     = "--test" in sys.argv

# ─── ETF List ─────────────────────────────────────────────────────────────────
# 3x = triple leveraged, 2x = double, -1x/-3x = inverse
LEVERAGED_ETFS = [
    # ── Long 3x ──
    ("SOXL", "Direxion Daily Semiconductor Bull 3X",    "semiconductor",  3),
    ("TQQQ", "ProShares UltraPro QQQ",                  "nasdaq100",      3),
    ("QLD",  "ProShares Ultra QQQ",                      "nasdaq100",      2),
    ("TECL", "Direxion Daily Technology Bull 3X",        "tech",           3),
    ("TNA",  "Direxion Daily Small Cap Bull 3X",          "small_cap",      3),
    ("EDC",  "Direxion Daily Emerging Markets Bull 3X",  "emerging",       3),
    ("DRN",  "Direxion Daily Real Estate Bull 3X",       "real_estate",    3),
    ("SPXL", "Direxion Daily S&P 500 Bull 3X",           "sp500",          3),
    ("UPRO", "ProShares UltraPro S&P 500",               "sp500",          3),
    ("YINN", "Direxion Daily China Bull 3X",              "china",          3),
    ("NAIL", "Direxion Daily Home Builders Bull 3X",      "homebuilders",   3),
    ("CURE", "Direxion Daily Healthcare Bull 3X",          "healthcare",     3),
    ("SOXX", "iShares Semiconductor SOXX",                "semiconductor",  1),  # regular ETF (proxy)
    ("FAZ",  "Direxion Daily Financial Bear 3X",          "financial",     -3),
    # ── Short 3x / Inverse ──
    ("SOXS", "Direxion Daily Semiconductor Bear 3X",     "semiconductor", -3),
    ("SQQQ", "ProShares UltraPro Short QQQ",              "nasdaq100",     -3),
    ("QID",  "ProShares UltraShort QQQ",                  "nasdaq100",     -2),
    ("SDS",  "ProShares UltraShort S&P 500",              "sp500",         -2),
    ("SPXS", "Direxion Daily S&P 500 Bear 3X",            "sp500",         -3),
    ("TZA",  "Direxion Daily Small Cap Bear 3X",          "small_cap",     -3),
    ("EDZ",  "Direxion Daily Emerging Markets Bear 3X",  "emerging",      -3),
    ("YINN", "Direxion Daily China Bull 3X",              "china",          3),
    ("YANG", "Direxion Daily China Bear 3X",              "china",         -3),
]

# Filter for test mode
if TEST_MODE:
    LEVERAGED_ETFS = [e for e in LEVERAGED_ETFS if e[0] in ("SOXL", "TQQQ", "SQQQ")]

# ─── Logging ───────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("lev_etf")

# ─── Technical Indicators ─────────────────────────────────────────────────────
def calc_rsi(closes, period=14):
    closes = np.array(closes, dtype=float)
    n = len(closes)
    if n < period + 1:
        return np.full(n, np.nan)
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_g  = np.convolve(gains,  np.ones(period)/period, mode="valid")
    avg_l  = np.convolve(losses, np.ones(period)/period, mode="valid")
    rs     = avg_g / (avg_l + 1e-10)
    rsi    = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, np.nan), rsi])

def calc_sma(data, period):
    data   = np.array(data, dtype=float)
    n      = len(data)
    result = np.full(n, np.nan)
    for i in range(period - 1, n):
        result[i] = np.mean(data[i - period + 1:i + 1])
    return result

def calc_ema(data, period):
    data   = np.array(data, dtype=float)
    n      = len(data)
    result = np.full(n, np.nan)
    ema    = float(data[0])
    mult   = 2.0 / (period + 1)
    for i in range(n):
        if np.isnan(data[i]):
            continue
        ema    = (data[i] - ema) * mult + ema
        result[i] = ema
    return result

def calc_atr(highs, lows, closes, period=14):
    n = len(highs)
    tr_list = []
    for i in range(n):
        if i == 0:
            tr_list.append(float(highs[i]) - float(lows[i]))
        else:
            hl = float(highs[i]) - float(lows[i])
            hc = abs(float(highs[i]) - float(closes[i-1]))
            lc = abs(float(lows[i])  - float(closes[i-1]))
            tr_list.append(max(hl, hc, lc))
    atr = np.full(n, np.nan)
    if n >= period:
        atr[period-1] = np.mean(tr_list[:period])
        for i in range(period, n):
            atr[i] = (atr[i-1] * (period - 1) + tr_list[i]) / period
    return atr

def calc_annual_return(price_start, price_end, years):
    if years <= 0 or price_start <= 0:
        return None
    return (price_end / price_start) ** (1 / years) - 1

def annualised_volatility(closes, periods_per_year=252):
    if len(closes) < 30:
        return None
    rets = np.diff(closes) / np.array(closes[:-1])
    rets = rets[~np.isnan(rets)]
    if len(rets) == 0:
        return None
    return float(np.std(rets) * np.sqrt(periods_per_year))

def rsi_zone(rsi_val):
    if rsi_val is None or np.isnan(rsi_val): return "N/A"
    if rsi_val >= 70: return "OVERBOUGHT"
    if rsi_val <= 30: return "OVERSOLD"
    if rsi_val >= 60: return "NEUTRAL_HIGH"
    if rsi_val <= 40: return "NEUTRAL_LOW"
    return "NEUTRAL"

# ─── Database ─────────────────────────────────────────────────────────────────
def init_db():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS etf_meta (
            symbol          TEXT PRIMARY KEY,
            name            TEXT,
            sector          TEXT,
            leverage        INTEGER,
            dividend_yield  REAL,
            expense_ratio   REAL,
            inception_date  TEXT,
            updated_at      TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_ohlcv (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol     TEXT    NOT NULL,
            date       TEXT    NOT NULL,
            open       REAL,
            high       REAL,
            low        REAL,
            close      REAL,
            volume     INTEGER,
            change_pct REAL,
            rsi_14     REAL,
            sma_20     REAL,
            sma_60     REAL,
            atr_14     REAL,
            macd       REAL,
            macd_sig   REAL,
            macd_hist  REAL,
            vol_ratio  REAL,
            zone       TEXT,
            UNIQUE(symbol, date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS performance (
            symbol        TEXT PRIMARY KEY,
            ret_1d        REAL,
            ret_1w        REAL,
            ret_1m        REAL,
            ret_3m        REAL,
            ret_6m        REAL,
            ret_ytd       REAL,
            ret_1y        REAL,
            ret_3y        REAL,
            ret_5y        REAL,
            ann_ret_1y    REAL,
            ann_ret_3y    REAL,
            ann_ret_5y    REAL,
            ann_vol_1y    REAL,
            max_dd_1y     REAL,
            sharpe_1y     REAL,
            updated_at    TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol     TEXT    NOT NULL,
            date       TEXT    NOT NULL,
            amount     REAL,
            UNIQUE(symbol, date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_version (
            id         INTEGER PRIMARY KEY,
            version    TEXT    NOT NULL,
            updated_at TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("INSERT OR REPLACE INTO db_version (id, version) VALUES (1, 'v1.0 Leveraged ETF DB')")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_lev_symbol  ON daily_ohlcv(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lev_date     ON daily_ohlcv(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_div_symbol  ON dividends(symbol)")

    conn.commit()
    return conn

# ─── Fetch & Store ────────────────────────────────────────────────────────────
def fetch_info(ticker_sym):
    """Fetch ETF info from yfinance (dividendYield, expenseRatio, inceptionDate, etc.)"""
    try:
        t   = yf.Ticker(ticker_sym)
        info = t.info or {}
        return {
            "dividend_yield": info.get("dividendYield") or info.get("dividendYieldTMT"),
            "expense_ratio":  info.get("expenseRatio")  or info.get("annualReportExpenseRatio"),
            "inception_date": info.get("fundInceptionDate") or info.get("inceptionDate"),
            "name":           info.get("longName") or info.get("shortName") or ticker_sym,
        }
    except Exception as e:
        log.warning("  [INFO] %s: %e", ticker_sym, e)
        return {"dividend_yield": None, "expense_ratio": None, "inception_date": None, "name": ticker_sym}

def fetch_dividends(conn, ticker_sym):
    """Fetch dividend history"""
    try:
        t    = yf.Ticker(ticker_sym)
        divs = t.dividends
        if divs is None or divs.empty:
            return 0
        cur = conn.cursor()
        count = 0
        for dt, amt in divs.items():
            dt_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
            cur.execute(
                "INSERT OR IGNORE INTO dividends (symbol, date, amount) VALUES (?, ?, ?)",
                (ticker_sym, dt_str, float(amt)),
            )
            count += 1
        conn.commit()
        return count
    except Exception as e:
        log.warning("  [DIV] %s: %e", ticker_sym, e)
        return 0

def fetch_and_store_ohlcv(conn, ticker_sym, force_full=False):
    """Fetch full/max history, compute indicators, store to DB"""
    try:
        t   = yf.Ticker(ticker_sym)
        h   = t.history(period="max")
        if h is None or h.empty or len(h) < 30:
            log.warning("  [WARN] %s: insufficient data (%d rows)", ticker_sym, 0 if h is None else len(h))
            return 0

        opens   = list(h["Open"].values)
        highs   = list(h["High"].values)
        lows    = list(h["Low"].values)
        closes  = list(h["Close"].values)
        volumes = list(h["Volume"].values)
        dates   = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d) for d in h.index]
        n       = len(closes)

        # Indicators
        rsi14   = list(calc_rsi(closes, 14))
        sma20   = list(calc_sma(closes, 20))
        sma60   = list(calc_sma(closes, 60))
        atr14   = list(calc_atr(highs, lows, closes, 14))
        ema12   = list(calc_ema(closes, 12))
        ema26   = list(calc_ema(closes, 26))
        macd_v  = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
        macd_s  = list(calc_ema(macd_v, 9))
        macd_h  = [mv - ms for mv, ms in zip(macd_v, macd_s)]

        # Volume ratio (today vs 20-day avg)
        vol_arr  = np.array(volumes, dtype=float)
        vol_ma20 = np.convolve(vol_arr, np.ones(20)/20, mode="valid")
        vol_ratio = [np.nan] * 19 + [v / vol_ma20[i] if vol_ma20[i] > 0 else np.nan for i, v in enumerate(vol_arr[19:])]

        cur    = conn.cursor()
        inserted = 0

        for i in range(n):
            c  = float(closes[i])
            if np.isnan(c):
                continue
            chg_pct = float((closes[i] - closes[i-1]) / closes[i-1] * 100) if i > 0 and closes[i-1] != 0 else 0.0
            rs14    = float(rsi14[i])    if not np.isnan(rsi14[i])    else None
            vr      = float(vol_ratio[i]) if not np.isnan(vol_ratio[i]) else None
            zone    = rsi_zone(rs14)

            def v(x):
                return round(float(x), 4) if x is not None and not np.isnan(x) else None

            cur.execute("""
                INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume, change_pct,
                 rsi_14, sma_20, sma_60, atr_14, macd, macd_sig, macd_hist,
                 vol_ratio, zone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker_sym, dates[i],
                v(opens[i]), v(highs[i]), v(lows[i]), c,
                int(volumes[i]), round(chg_pct, 4),
                v(rsi14[i]), v(sma20[i]), v(sma60[i]), v(atr14[i]),
                v(macd_v[i]), v(macd_s[i]), v(macd_h[i]),
                v(vr), zone
            ))
            inserted += 1

        conn.commit()
        log.info("  [OK] %s: %d rows stored", ticker_sym, inserted)
        return inserted

    except Exception as e:
        log.error("  [ERR] %s: %e", ticker_sym, e)
        return 0

def update_performance(conn, ticker_sym, closes, dates):
    """Calculate and store performance metrics"""
    if len(closes) < 60:
        return
    try:
        c      = np.array(closes, dtype=float)
        d      = dates
        n      = len(c)

        def ret(period):
            idx = period
            if idx < n and c[n - idx - 1] > 0 and c[-1] > 0:
                return round((c[-1] / c[n - idx - 1] - 1) * 100, 2)
            return None

        def ann_ret(years):
            start_idx = 0
            end_idx   = n - 1
            y = years * 252
            if y >= n:
                start_idx = 0
            else:
                start_idx = n - y
            if c[start_idx] > 0 and c[end_idx] > 0:
                yrs = min((n - start_idx) / 252, years)
                if yrs < 0.01:
                    return None
                return round(((c[end_idx] / c[start_idx]) ** (1 / yrs) - 1) * 100, 2)
            return None

        vol = annualised_volatility(c)

        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO performance
            (symbol, ret_1d, ret_1w, ret_1m, ret_3m, ret_6m, ret_ytd,
             ret_1y, ret_3y, ret_5y,
             ann_ret_1y, ann_ret_3y, ann_ret_5y,
             ann_vol_1y, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker_sym,
            ret(1), ret(5), ret(21),
            ret(63), ret(126),
            ret(int((datetime.now() - datetime(datetime.now().year, 1, 1)).days)),  # YTD approx
            ret(252), ret(756), ret(1260),
            ann_ret(1), ann_ret(3), ann_ret(5),
            round(vol * 100, 2) if vol else None,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()
    except Exception as e:
        log.warning("  [PERF] %s: %e", ticker_sym, e)

# ─── CSV Export ────────────────────────────────────────────────────────────────
def export_csv(conn):
    try:
        cur = conn.cursor()

        # Build combined view: meta + latest performance + latest daily
        cur.execute("""
            SELECT
                m.symbol,
                m.name,
                m.sector,
                m.leverage,
                m.dividend_yield,
                m.expense_ratio,
                m.inception_date,
                p.ret_1d, p.ret_1w, p.ret_1m, p.ret_3m, p.ret_6m, p.ret_ytd,
                p.ret_1y, p.ret_3y, p.ret_5y,
                p.ann_ret_1y, p.ann_ret_3y, p.ann_ret_5y,
                p.ann_vol_1y,
                d.date       AS last_date,
                d.close      AS last_price,
                d.rsi_14,
                d.sma_20,
                d.sma_60,
                d.zone,
                d.change_pct,
                d.vol_ratio,
                d.macd_hist
            FROM etf_meta m
            LEFT JOIN performance p ON m.symbol = p.symbol
            LEFT JOIN (
                SELECT symbol, date, close, rsi_14, sma_20, sma_60, zone,
                       change_pct, vol_ratio, macd_hist,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
                FROM daily_ohlcv
            ) d ON m.symbol = d.symbol AND d.rn = 1
            ORDER BY m.symbol
        """)

        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]

        import csv
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)

        log.info("CSV exported → %s (%d rows)", CSV_PATH, len(rows))
        return len(rows)

    except Exception as e:
        log.error("CSV export failed: %e", e)
        return 0

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("LEVERAGED ETF DB BUILDER  (mode=%s)", "FULL" if FULL_REFRESH else "INCREMENTAL")
    log.info("Time: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    log.info("DB:   %s", DB_PATH)
    log.info("CSV:  %s", CSV_PATH)

    conn = init_db()
    total_rows = 0

    # ── Upsert ETF meta ───────────────────────────────────────────────────────
    cur = conn.cursor()
    for sym, name, sector, lev in LEVERAGED_ETFS:
        info = fetch_info(sym)
        cur.execute("""
            INSERT OR REPLACE INTO etf_meta
            (symbol, name, sector, leverage, dividend_yield, expense_ratio,
             inception_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sym, name, sector, lev,
            info.get("dividend_yield"), info.get("expense_ratio"),
            info.get("inception_date"),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        log.info("  [META] %s | %s | %dx | DY=%.2f%% | ER=%.3f",
                 sym, name, lev,
                 (info.get("dividend_yield") or 0) * 100,
                 info.get("expense_ratio") or 0)
        time.sleep(0.25)

    conn.commit()

    # ── Fetch OHLCV & Dividends ────────────────────────────────────────────────
    log.info("\n─── Fetching OHLCV + Dividends ───")
    for i, (sym, name, sector, lev) in enumerate(LEVERAGED_ETFS):
        log.info("[%d/%d] %s %s", i+1, len(LEVERAGED_ETFS), sym, name)

        # Dividends
        n_div = fetch_dividends(conn, sym)
        if n_div > 0:
            log.info("  [DIV] %d dividend records", n_div)

        # OHLCV
        n_rows = fetch_and_store_ohlcv(conn, sym, force_full=FULL_REFRESH)
        total_rows += n_rows

        time.sleep(0.4)

    # ── Update performance metrics ─────────────────────────────────────────────
    log.info("\n─── Computing Performance Metrics ───")
    cur = conn.cursor()
    for sym, _, _, _ in LEVERAGED_ETFS:
        try:
            cur.execute(
                "SELECT date, close FROM daily_ohlcv WHERE symbol=? ORDER BY date ASC",
                (sym,)
            )
            rows = cur.fetchall()
            if len(rows) > 60:
                dates  = [r[0] for r in rows]
                closes = [float(r[1]) for r in rows]
                update_performance(conn, sym, closes, dates)
                log.info("  [PERF] %s: performance updated", sym)
        except Exception as e:
            log.warning("  [PERF] %s: %e", sym, e)
        time.sleep(0.2)

    # ── Stats ──────────────────────────────────────────────────────────────────
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    n_etfs = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM daily_ohlcv")
    n_rows_total = cur.fetchone()[0]
    cur.execute("SELECT MIN(date), MAX(date) FROM daily_ohlcv")
    row = cur.fetchone()
    log.info("\n─── DB Stats ───")
    log.info("  ETFs:         %d", n_etfs)
    log.info("  OHLCV rows:   %d", n_rows_total)
    log.info("  Date range:   %s ~ %s", row[0], row[1])
    cur.execute("SELECT COUNT(*) FROM dividends")
    log.info("  Dividends:    %d", cur.fetchone()[0])

    # ── Export CSV ────────────────────────────────────────────────────────────
    csv_rows = export_csv(conn)

    log.info("\nTotal OHLCV rows stored this run: %d", total_rows)
    log.info("CSV rows exported: %d", csv_rows)
    log.info("DB: %s", DB_PATH)
    log.info("Log: %s", LOG_PATH)
    log.info("─── DONE %s ───", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())