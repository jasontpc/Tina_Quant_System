# -*- coding: utf-8 -*-
"""
Leveraged ETF Analysis & Entry Signals
自動分析槓桿 ETF 並給出進場建議

Signals generated:
  - ENTRY_OVERSOLD  : RSI 從超賣區翻轉
  - ENTRY_PULLBACK  : 回測 20SMA 支撐
  - ENTRY_GOLDEN_X  : 短均線黃金交叉
  - ENTRY_MOMENTUM   : 動能突破
  - EXIT_OVERBOUGHT : RSI 進入超買區
  - EXIT_TRAILING    : 移動停損觸發

Usage:
    python leverage_etf_analysis.py             # scan all
    python leverage_etf_analysis.py SOXL TQQQ   # specific ETFs
    python leverage_etf_analysis.py --report    # full report
"""
import sys, os, sqlite3, logging
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import yfinance as yf

# ─── Config ──────────────────────────────────────────────────────────────────
DATA_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data")
DB_PATH  = DATA_DIR / "leverage_etf.db"
CSV_PATH = DATA_DIR / "leverage_etf_database.csv"
LOG_PATH = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\logs\leverage_etf_update.log")

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8", mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("lev_etf_analysis")

# ─── Default ETF list ────────────────────────────────────────────────────────
DEFAULT_ETFS = [
    "SOXL", "TQQQ", "QLD", "TECL", "TNA", "EDC", "DRN",
    "SPXL", "UPRO", "YINN", "NAIL", "CURE",
    "SOXS", "SQQQ", "QID", "SDS", "SPXS", "TZA", "EDZ", "YANG", "FAZ",
]

SYMBOLS = [a for a in sys.argv[1:] if not a.startswith("--")] or DEFAULT_ETFS
REPORT_MODE = "--report" in sys.argv

# ─── Signals DB ──────────────────────────────────────────────────────────────
def get_connection():
    if not DB_PATH.exists():
        log.error("DB not found: %s  (run leverage_etf_db.py first)", DB_PATH)
        return None
    return sqlite3.connect(DB_PATH)

def init_signals_db(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            signal_type TEXT    NOT NULL,
            zone        TEXT,
            price       REAL,
            rsi_14      REAL,
            bias_20     REAL,
            momentum_1m  REAL,
            macd_hist   REAL,
            atr_14      REAL,
            score       INTEGER,
            strength    TEXT,
            action      TEXT,
            notes       TEXT,
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date, signal_type)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entry_recommendations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            entry_price REAL,
            stop_loss   REAL,
            take_profit REAL,
            risk_pct    REAL,
            reward_pct  REAL,
            rr_ratio    REAL,
            position_size_pct REAL,
            confidence  TEXT,
            action      TEXT,
            status      TEXT    DEFAULT 'ACTIVE',
            created_at  TEXT    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date, action)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sig_symbol ON signals(symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sig_date   ON signals(date)")
    conn.commit()

# ─── Analysis Functions ──────────────────────────────────────────────────────
def get_latest_data(conn, symbol, lookback=252):
    cur = conn.cursor()
    cur.execute("""
        SELECT date, open, high, low, close, volume,
               rsi_14, sma_20, sma_60, atr_14, macd_hist, zone, change_pct, vol_ratio
        FROM daily_ohlcv
        WHERE symbol = ?
        ORDER BY date DESC
        LIMIT ?
    """, (symbol, lookback))
    rows = cur.fetchall()
    if not rows:
        return None
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]  # newest first

def calc_annualised_return(closes, periods=252):
    if len(closes) < 2:
        return None
    ret = (closes[-1] / closes[0]) - 1
    yrs = len(closes) / periods
    if yrs < 0.01:
        return None
    return ((1 + ret) ** (1 / yrs) - 1) * 100

def analyse_symbol(conn, symbol):
    data = get_latest_data(conn, symbol)
    if not data:
        return None

    d      = data[0]   # latest
    d_1    = data[1] if len(data) > 1 else d
    d_5    = data[4] if len(data) > 4 else d
    d_20   = data[19] if len(data) > 19 else d
    d_60   = data[59] if len(data) > 59 else d

    price  = d["close"]
    rsi    = d["rsi_14"] or 50
    zone   = d["zone"]   or "N/A"
    sma20  = d["sma_20"] or price
    sma60  = d["sma_60"] or price
    atr    = d["atr_14"] or (price * 0.02)
    macd_h = d["macd_hist"] or 0
    chg    = d["change_pct"] or 0
    vr     = d["vol_ratio"] or 1

    # Bias
    bias20 = (price / sma20 - 1) * 100 if sma20 and sma20 > 0 else 0
    bias60 = (price / sma60 - 1) * 100 if sma60 and sma60 > 0 else 0

    # Momentum
    if len(data) >= 21:
        momentum_1m = (price / data[20]["close"] - 1) * 100
    else:
        momentum_1m = 0

    # 52w high / low
    closes_52w = [x["close"] for x in data[:252] if x["close"]]
    hi52  = max(closes_52w) if closes_52w else price
    lo52  = min(closes_52w) if closes_52w else price
    pos52 = (price - lo52) / (hi52 - lo52) * 100 if hi52 > lo52 else 50

    # Trend
    above_sma20 = price > sma20
    above_sma60 = price > sma60

    # MACD direction
    macd_bullish = macd_h > 0

    # Previous zone
    prev_zone = d_1["zone"] if len(data) > 1 else zone
    prev_rsi  = d_1["rsi_14"] if len(data) > 1 else rsi

    # ── Score ──────────────────────────────────────────────────────────────────
    score   = 0
    factors = {}

    # RSI zone scoring
    if rsi <= 30:      rs = 30
    elif rsi <= 40:    rs = 20
    elif rsi <= 50:    rs = 10
    elif rsi <= 60:    rs = 5
    elif rsi <= 70:    rs = 0
    else:              rs = -20
    factors["rsi"] = rs

    # Trend alignment
    if above_sma20 and above_sma60:   ts = 25
    elif above_sma20:                 ts = 15
    elif not above_sma20 and not above_sma60: ts = -15
    else:                             ts = 0
    factors["trend"] = ts

    # MACD momentum
    ms = 15 if macd_bullish else -10
    factors["macd"] = ms

    # Momentum 1M
    if momentum_1m > 10:   ms2 = 15
    elif momentum_1m > 5:  ms2 = 10
    elif momentum_1m > 0:  ms2 = 5
    elif momentum_1m > -5: ms2 = 0
    else:                  ms2 = -10
    factors["momentum"] = ms2

    # Volume
    vs = 10 if vr >= 1.5 else 5 if vr >= 1.0 else 0 if vr >= 0.5 else -5
    factors["volume"] = vs

    # 52w position
    p52 = 15 if pos52 >= 80 else 10 if pos52 >= 60 else 5 if pos52 >= 40 else 0 if pos52 >= 20 else -10
    factors["pos52w"] = p52

    score = sum(factors.values())

    # ── Signal detection ───────────────────────────────────────────────────────
    signals = []

    # ENTRY_OVERSOLD: RSI exits oversold zone
    if prev_rsi and prev_rsi <= 30 and rsi > 30:
        sig = "ENTRY_OVERSOLD"
        strength = "STRONG" if rsi >= 45 else "MODERATE"
        signals.append({
            "type": sig, "zone": zone, "strength": strength,
            "score": min(score + 15, 100),
            "action": "BUY",
            "notes": f"RSI {prev_rsi:.1f}→{rsi:.1f} 脫離超賣"
        })

    # ENTRY_PULLBACK: price within 5% of SMA20
    if abs(bias20) <= 5 and above_sma20 and rsi < 65:
        sig = "ENTRY_PULLBACK"
        strength = "STRONG" if abs(bias20) <= 2 else "MODERATE"
        signals.append({
            "type": sig, "zone": zone, "strength": strength,
            "score": min(score + 10, 100),
            "action": "BUY",
            "notes": f"回測 SMA20 偏離 {bias20:+.1f}%"
        })

    # ENTRY_GOLDEN_X: SMA20 crosses above SMA60
    if (len(data) >= 2 and
        d["sma_20"] and d_1["sma_20"] and
        d["sma_60"] and d_1["sma_60"] and
        d["sma_20"] > d["sma_60"] and
        d_1["sma_20"] <= d_1["sma_60"]):
        sig = "ENTRY_GOLDEN_X"
        strength = "STRONG"
        signals.append({
            "type": sig, "zone": zone, "strength": strength,
            "score": min(score + 20, 100),
            "action": "BUY",
            "notes": "MA20 黃金交叉 MA60"
        })

    # ENTRY_MOMENTUM: strong 1M momentum + volume confirmation
    if momentum_1m > 10 and vr >= 1.3 and above_sma20:
        sig = "ENTRY_MOMENTUM"
        strength = "STRONG" if momentum_1m > 20 else "MODERATE"
        signals.append({
            "type": sig, "zone": zone, "strength": strength,
            "score": min(score + 10, 100),
            "action": "BUY",
            "notes": f"動能 +{momentum_1m:.1f}% 成交量 {vr:.1f}x"
        })

    # EXIT_OVERBOUGHT
    if prev_rsi and prev_rsi < 70 and rsi >= 70:
        sig = "EXIT_OVERBOUGHT"
        strength = "STRONG" if rsi >= 80 else "MODERATE"
        signals.append({
            "type": sig, "zone": zone, "strength": strength,
            "score": max(score - 20, 0),
            "action": "SELL",
            "notes": f"RSI {prev_rsi:.1f}→{rsi:.1f} 進入超買"
        })

    # EXIT_DEATH_X: SMA20 crosses below SMA60 (for long positions)
    if (len(data) >= 2 and
        d["sma_20"] and d_1["sma_20"] and
        d["sma_60"] and d_1["sma_60"] and
        d["sma_20"] < d["sma_60"] and
        d_1["sma_20"] >= d_1["sma_60"]):
        sig = "EXIT_DEATH_X"
        strength = "STRONG"
        signals.append({
            "type": sig, "zone": zone, "strength": strength,
            "score": max(score - 25, 0),
            "action": "SELL",
            "notes": "MA20 死亡交叉 MA60"
        })

    # Best signal
    best = max(signals, key=lambda s: s["score"]) if signals else None

    # ── Entry recommendation ───────────────────────────────────────────────────
    recommendation = None
    if best and best["action"] == "BUY":
        atr_risk = atr * 2   # 2 ATR stop
        tp_risk  = atr * 6   # 6 ATR take-profit (3:1 R/R)
        sl       = round(price - atr_risk, 2)
        tp       = round(price + tp_risk, 2)
        risk_pct = (atr_risk / price) * 100
        reward_pct = (tp_risk / price) * 100
        rr      = tp_risk / atr_risk if atr_risk > 0 else 0

        # Position size: risk 2% of capital
        # position_size = capital * 0.02 / risk_pct  (capital assumed 100 for relative)
        # We report as % of notional for 2% risk on 100k base
        pos_pct  = round(2.0 / risk_pct * 100, 1) if risk_pct > 0 else 0

        confidence = ("HIGH" if best["score"] >= 80
                      else "MEDIUM" if best["score"] >= 60
                      else "LOW")

        recommendation = {
            "entry_price":        round(price, 2),
            "stop_loss":          sl,
            "take_profit":        tp,
            "risk_pct":           round(risk_pct, 2),
            "reward_pct":         round(reward_pct, 2),
            "rr_ratio":           round(rr, 2),
            "position_size_pct": pos_pct,
            "confidence":        confidence,
            "action":            "BUY",
        }

    # ── Annualised returns ────────────────────────────────────────────────────
    closes_all = [x["close"] for x in data[::-1] if x["close"]]  # oldest first

    ann_ret_1y  = calc_annualised_return(closes_all[:min(252, len(closes_all))]) if len(closes_all) >= 60 else None
    ann_ret_3y  = calc_annualised_return(closes_all[:min(756, len(closes_all))]) if len(closes_all) >= 252 else None
    ann_ret_max = calc_annualised_return(closes_all) if len(closes_all) >= 252 else None

    return {
        "symbol":              symbol,
        "price":               round(price, 2),
        "rsi":                 round(rsi, 1),
        "zone":                zone,
        "bias_20":             round(bias20, 2),
        "bias_60":             round(bias60, 2),
        "momentum_1m":         round(momentum_1m, 2),
        "pos52w":              round(pos52, 1),
        "atr14":               round(atr, 2),
        "macd_hist":           round(macd_h, 4),
        "vol_ratio":           round(vr, 2),
        "sma20":               round(sma20, 2),
        "sma60":               round(sma60, 2),
        "above_sma20":         above_sma20,
        "above_sma60":         above_sma60,
        "ann_ret_1y":          round(ann_ret_1y, 2) if ann_ret_1y else None,
        "ann_ret_3y":          round(ann_ret_3y, 2) if ann_ret_3y else None,
        "ann_ret_max":         round(ann_ret_max, 2) if ann_ret_max else None,
        "score":               score,
        "factors":            factors,
        "signals":             signals,
        "best_signal":         best,
        "recommendation":      recommendation,
        "data_date":           d["date"],
    }

# ─── Store signals ──────────────────────────────────────────────────────────
def store_signals(conn, results):
    cur = conn.cursor()
    init_signals_db(conn)

    for r in results:
        if not r:
            continue
        sym   = r["symbol"]
        date  = r["data_date"]
        best  = r.get("best_signal")
        rec   = r.get("recommendation")

        if best:
            cur.execute("""
                INSERT OR REPLACE INTO signals
                (symbol, date, signal_type, zone, price, rsi_14, bias_20,
                 momentum_1m, macd_hist, atr_14, score, strength, action, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sym, date, best["type"], best["zone"], r["price"],
                r["rsi"], r["bias_20"], r["momentum_1m"], r["macd_hist"], r["atr14"],
                best["score"], best["strength"], best["action"], best["notes"]
            ))

        if rec:
            cur.execute("""
                INSERT OR REPLACE INTO entry_recommendations
                (symbol, date, entry_price, stop_loss, take_profit,
                 risk_pct, reward_pct, rr_ratio, position_size_pct,
                 confidence, action, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (
                sym, date,
                rec["entry_price"], rec["stop_loss"], rec["take_profit"],
                rec["risk_pct"], rec["reward_pct"], rec["rr_ratio"],
                rec["position_size_pct"], rec["confidence"], rec["action"]
            ))

    conn.commit()
    log.info("Signals stored for %d ETFs", len([r for r in results if r]))

# ─── Report ──────────────────────────────────────────────────────────────────
def print_report(results):
    print()
    print("=" * 80)
    print("  LEVERAGED ETF ANALYSIS REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    # ── Summary table ──────────────────────────────────────────────────────────
    print(f"\n{'Symbol':<7} {'Price':>8} {'RSI':>5} {'Zone':<13} {'BIAS20':>7} "
          f"{'1M Mom':>7} {'52w%':>5} {'Score':>6} {'Signal':<22}")
    print("-" * 90)
    for r in results:
        if not r:
            continue
        best = r.get("best_signal") or {}
        sig_str = f"{best.get('type','')} [{best.get('strength','')}]" if best else "—"
        action  = best.get("action", "") if best else ""
        print(
            f"{r['symbol']:<7} {r['price']:>8.2f} {r['rsi']:>5.1f} "
            f"{r['zone']:<13} {r['bias_20']:>+7.1f}% {r['momentum_1m']:>+7.1f}% "
            f"{r['pos52w']:>5.1f} {r['score']:>6} {action:<4} {sig_str}"
        )

    # ── BUY signals ───────────────────────────────────────────────────────────
    print("\n─── 📗 BUY SIGNALS ───")
    buys = [r for r in results if r and (r.get('best_signal') or {}).get('action') == 'BUY']
    if not buys:
        print("  (none)")
    for r in buys:
        best = r["best_signal"]
        rec  = r.get("recommendation") or {}
        print(f"\n  [{r['symbol']}] {best['type']}  ({best['strength']})")
        print(f"    Price: ${r['price']}  RSI: {r['rsi']}  Zone: {r['zone']}")
        print(f"    BIAS20: {r['bias_20']:+.1f}%  1M Mom: {r['momentum_1m']:+.1f}%")
        print(f"    Score: {best['score']}/100")
        if rec:
            print(f"    → Entry: ${rec['entry_price']}  |  SL: ${rec['stop_loss']}  |  TP: ${rec['take_profit']}")
            print(f"    → Risk: {rec['risk_pct']}%  Reward: {rec['reward_pct']}%  R/R: {rec['rr_ratio']}:1")
            print(f"    → Position size: {rec['position_size_pct']:.0f}%  Confidence: {rec['confidence']}")
        print(f"    Notes: {best['notes']}")

    # ── SELL signals ──────────────────────────────────────────────────────────
    print("\n─── 📕 SELL SIGNALS ───")
    sells = [r for r in results if r and (r.get('best_signal') or {}).get('action') == 'SELL']
    if not sells:
        print("  (none)")
    for r in sells:
        best = r["best_signal"]
        print(f"\n  [{r['symbol']}] {best['type']}  ({best['strength']})")
        print(f"    Price: ${r['price']}  RSI: {r['rsi']}  Zone: {r['zone']}")
        print(f"    Score: {best['score']}  Notes: {best['notes']}")

    # ── Annualised Returns ─────────────────────────────────────────────────────
    print("\n─── 📊 ANNUALISED RETURNS (estimated from price history) ───")
    print(f"  {'Symbol':<7} {'1Y Ann.Ret':>10} {'3Y Ann.Ret':>10} {'Max Ann.Ret':>12} {'Score':>6}")
    print("-" * 50)
    for r in results:
        if not r:
            continue
        print(f"  {r['symbol']:<7} "
              f"{str(r.get('ann_ret_1y') or 'N/A'):>10} "
              f"{str(r.get('ann_ret_3y') or 'N/A'):>10} "
              f"{str(r.get('ann_ret_max') or 'N/A'):>12} "
              f"{r['score']:>6}")

    print("\n" + "=" * 80)
    print(f"  Report complete — {len(results)} ETFs analyzed")
    print("=" * 80)

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    log.info("LEVERAGED ETF ANALYSIS  symbols=%s", SYMBOLS)

    conn = get_connection()
    if not conn:
        sys.exit(1)

    results = []
    for sym in SYMBOLS:
        r = analyse_symbol(conn, sym)
        if r:
            results.append(r)
            log.info("  %s: price=%.2f RSI=%.1f zone=%s score=%d signal=%s",
                     sym, r["price"], r["rsi"], r["zone"], r["score"],
                     (r.get("best_signal") or {}).get("type") or "—")
        else:
            log.warning("  %s: no data (run leverage_etf_db.py first)", sym)

    conn.close()
    conn2 = get_connection()
    if conn2:
        store_signals(conn2, results)
        conn2.close()

    print_report(results)

    log.info("Analysis complete — %d/%d ETFs", len(results), len(SYMBOLS))
    return 0

if __name__ == "__main__":
    sys.exit(main())