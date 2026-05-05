"""
stock_strategy_updater.py
==========================
每日主動更新所有個股策略的技術指標，產出 Markdown 報告。
可搭配 cron 排程定時執行。
"""

import io
import sys
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp950 UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR   = Path(__file__).parent.parent.resolve()
CONFIG_DIR = BASE_DIR / "configs" / "stock_strategies"
DATA_DIR   = BASE_DIR / "data"   / "stock_strategies"
REPORT_DIR = BASE_DIR / "reports"
LOG_DIR    = BASE_DIR / "logs"

for _d in [DATA_DIR, REPORT_DIR, LOG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── yfinance ──────────────────────────────────────────────────────────────
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("WARNING: yfinance not installed", file=sys.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# Technical indicators
# ═══════════════════════════════════════════════════════════════════════════

def calc_atr(high, low, close, period=14):
    if len(high) < period + 1:
        return None
    trs = []
    for i in range(1, len(high)):
        tr = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
        trs.append(tr)
    return sum(trs[-period:]) / period


def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = [prices[i]-prices[i-1] for i in range(1, len(prices))]
    gains  = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains)  / period if gains  else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))


def calc_ma(prices, n):
    if len(prices) < n:
        return None
    return sum(prices[-n:]) / n


def calc_bias(price, ma20):
    if not ma20:
        return None
    return (price - ma20) / ma20 * 100


def ma_slope(prices, n=20, lookback=5):
    if len(prices) < n + lookback - 1:
        return None
    ma_vals = [calc_ma(prices[:i+1], n) for i in range(n-1, len(prices))]
    ma_vals = ma_vals[-lookback:]
    if len(ma_vals) < lookback:
        return None
    x = list(range(lookback))
    x_mean = sum(x) / lookback
    y_mean = sum(ma_vals) / lookback
    num = sum((x[i]-x_mean)*(ma_vals[i]-y_mean) for i in range(lookback))
    den = sum((x[i]-x_mean)**2 for i in range(lookback))
    return num / den if den else 0


def compute_indicators(hist):
    close  = list(hist["Close"])
    high   = list(hist["High"])
    low    = list(hist["Low"])
    volume = list(hist["Volume"])

    price    = close[-1]
    rsi      = calc_rsi(close)
    ma20     = calc_ma(close, 20)
    ma60     = calc_ma(close, 60) if len(close) >= 60 else None
    bias20   = calc_bias(price, ma20)
    slope20  = ma_slope(close)
    atr      = calc_atr(high, low, close)
    avg_vol  = sum(volume[-20:]) / 20 if len(volume) >= 20 else 0
    vol_r    = volume[-1] / avg_vol if avg_vol > 0 else 0
    high_20  = max(high[-20:])  if len(high) >= 20 else max(high)
    low_20    = min(low[-20:])   if len(low)  >= 20 else min(low)

    # KDJ
    k_val, d_val = 50, 50
    for i in range(len(close)):
        h9 = max(high[max(0,i-8):i+1])
        l9 = min(low[max(0,i-8):i+1])
        if h9 != l9:
            rsv = (close[i] - l9) / (h9 - l9) * 100
            k_val = 2/3 * k_val + 1/3 * rsv
            d_val = 2/3 * d_val + 1/3 * k_val

    return {
        "price":     round(price, 2),
        "rsi14":     round(rsi, 1) if rsi else None,
        "ma20":      round(ma20, 2) if ma20 else None,
        "ma60":      round(ma60, 2) if ma60 else None,
        "bias20":    round(bias20, 2) if bias20 else None,
        "slope20":   round(slope20, 4) if slope20 else None,
        "atr14":     round(atr, 2) if atr else None,
        "vol":       volume[-1],
        "vol_avg20": round(avg_vol, 0),
        "vol_ratio": round(vol_r, 2),
        "high_20":   round(high_20, 2),
        "low_20":    round(low_20, 2),
        "K":         round(k_val, 1),
        "D":         round(d_val, 1),
    }


def fetch_data(stock_id, market="TW", days=90):
    if not HAS_YF:
        return None
    yf_sym = f"{stock_id}.TW" if market == "TW" else stock_id
    try:
        tk = yf.Ticker(yf_sym)
        h  = tk.history(period=f"{days}d", auto_adjust=True)
        return h if not h.empty else None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Entry evaluation
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_entry(ind, strategy):
    entry = strategy["entry"]
    rsi   = ind.get("rsi14")
    ma20  = ind.get("ma20")
    ma60  = ind.get("ma60")
    bias  = ind.get("bias20")
    slope = ind.get("slope20")
    vol_r = ind.get("vol_ratio", 0)
    vol   = ind.get("vol", 0)

    checks = {}
    score  = 0

    # RSI range
    if rsi is not None:
        rsi_ok = entry.get("rsi_min", 0) <= rsi <= entry.get("rsi_max", 100)
        checks["rsi"] = rsi_ok
        if rsi_ok:
            score += 1
        if "rsi_ideal" in entry:
            try:
                lo, hi = map(float, entry["rsi_ideal"].split("-"))
                checks["rsi_ideal"] = lo <= rsi <= hi
                if checks["rsi_ideal"]:
                    score += 1
            except Exception:
                checks["rsi_ideal"] = False
    else:
        checks["rsi"] = False
        checks["rsi_ideal"] = False

    # MA arrangement
    ma_ok = True
    if entry.get("ma_required") and ma20 is not None and ma60 is not None:
        if "MA20>MA60" in entry["ma_required"]:
            ma_ok = ma20 > ma60
    checks["ma_arrange"] = ma_ok
    if ma_ok:
        score += 1

    # MA slope
    slope_ok = True
    if entry.get("ma20_slope_min") and slope is not None:
        slope_ok = slope >= entry["ma20_slope_min"]
    checks["ma_slope"] = slope_ok
    if slope_ok:
        score += 1

    # BIAS
    bias_ok = True
    if entry.get("bias20_max") and bias is not None:
        bias_ok = abs(bias) <= entry["bias20_max"]
    checks["bias"] = bias_ok
    if bias_ok:
        score += 1

    # Volume
    vol_ok = True
    if entry.get("volume_min"):
        vol_ok = vol >= entry["volume_min"]
    elif entry.get("volume_ratio_min"):
        vol_ok = vol_r >= entry["volume_ratio_min"]
    checks["volume"] = vol_ok
    if vol_ok:
        score += 1

    signal = "NO_SIGNAL"
    if score == 7:
        signal = "ENTRY_READY"
    elif score >= 5:
        signal = "ENTRY_WATCH"

    return signal, checks, score, 7


# ═══════════════════════════════════════════════════════════════════════════
# Exit levels
# ═══════════════════════════════════════════════════════════════════════════

def calc_exit_levels(entry_price, strategy, atr):
    ex = strategy["exit"]
    return {
        "entry_price":   round(entry_price, 2),
        "stop_loss":     round(entry_price * (1 - ex["stop_loss_pct"] / 100), 2),
        "take_profit":   round(entry_price * (1 + ex.get("take_profit_pct", 10) / 100), 2),
        "trailing_stop": round(entry_price - (ex.get("trailing_stop_atr") or 0) * atr, 2) if atr else None,
        "atr":           round(atr, 2) if atr else None,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Process single stock
# ═══════════════════════════════════════════════════════════════════════════

def process_stock(stock_id):
    cfg_path = CONFIG_DIR / f"{stock_id}.json"
    if not cfg_path.exists():
        return None, f"Strategy file not found: {cfg_path}"

    with open(cfg_path, "r", encoding="utf-8") as f:
        strategy = json.load(f)

    market = strategy.get("market", "TW")
    hist   = fetch_data(stock_id, market)
    if hist is None or len(hist) < 30:
        return None, f"[{stock_id}] Insufficient data"

    ind    = compute_indicators(hist)
    signal, checks, score, max_score = evaluate_entry(ind, strategy)

    result = {
        "stock":      stock_id,
        "name":       strategy.get("name", stock_id),
        "market":     market,
        "type":       strategy.get("type", "unknown"),
        "signal":     signal,
        "score":      score,
        "max_score":  max_score,
        "checks":     checks,
        "indicators": ind,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    if signal == "ENTRY_READY":
        result["exit_levels"] = calc_exit_levels(ind["price"], strategy, ind.get("atr14"))

    # Save tracking history
    track_file = DATA_DIR / f"{stock_id}_tracking.json"
    history = []
    if track_file.exists():
        try:
            with open(track_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    history.append(result)
    history = history[-90:]
    with open(track_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    return result, None


# ═══════════════════════════════════════════════════════════════════════════
# Markdown report
# ═══════════════════════════════════════════════════════════════════════════

def make_markdown_report(results, errors, date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    lines = []
    lines.append(f"# Stock Strategy Daily Report")
    lines.append(f"**{date_str} {datetime.now().strftime('%H:%M')}**\n")
    lines.append(f"— Tina Quant System v3.12\n")
    lines.append(f"\n---\n")

    # ENTRY_READY
    ready = [r for r in results if r.get("signal") == "ENTRY_READY"]
    if ready:
        lines.append(f"## ENTRY_READY ({len(ready)} stocks)\n")
        lines.append(f"| Stock | Name | Price | RSI14 | MA20 | MA60 | BIAS20 | ATR14 | VolRatio | SL | TP |")
        lines.append(f"|-------|------|-------|-------|------|------|--------|-------|----------|----|----|")
        for r in ready:
            ind = r.get("indicators", {})
            ex  = r.get("exit_levels", {})
            lines.append(
                f"| {r['stock']} | {r['name']} | {ind.get('price')} | "
                f"{ind.get('rsi14')} | {ind.get('ma20')} | {ind.get('ma60')} | "
                f"{ind.get('bias20')} | {ind.get('atr14')} | {ind.get('vol_ratio')} | "
                f"{ex.get('stop_loss')} | {ex.get('take_profit')} |"
            )
        lines.append("")

    # ENTRY_WATCH
    watch = [r for r in results if r.get("signal") == "ENTRY_WATCH"]
    if watch:
        lines.append(f"## ENTRY_WATCH ({len(watch)} stocks)\n")
        lines.append(f"| Stock | Name | Price | RSI14 | BIAS20 | VolRatio | Score | Failed |")
        lines.append(f"|-------|------|-------|-------|--------|----------|-------|--------|")
        for r in watch:
            ind = r.get("indicators", {})
            chk = r.get("checks", {})
            failed = [k for k, v in chk.items() if not v]
            lines.append(
                f"| {r['stock']} | {r['name']} | {ind.get('price')} | "
                f"{ind.get('rsi14')} | {ind.get('bias20')} | "
                f"{ind.get('vol_ratio')} | {r.get('score')}/{r.get('max_score')} | "
                f"{', '.join(failed) if failed else '—'} |"
            )
        lines.append("")

    # Errors
    if errors:
        lines.append(f"## Errors ({len(errors)})\n")
        for e in errors:
            lines.append(f"- {e}")
        lines.append("")

    # Full summary
    lines.append(f"## All {len(results)} Stocks Summary\n")
    lines.append(f"| Stock | Name | Market | Type | Signal | Score | Price | RSI |")
    lines.append(f"|-------|------|--------|------|--------|-------|-------|-----|")
    for r in results:
        ind = r.get("indicators", {})
        lines.append(
            f"| {r['stock']} | {r['name']} | {r.get('market')} | {r.get('type')} | "
            f"{r.get('signal')} | {r.get('score')}/{r.get('max_score')} | "
            f"{ind.get('price')} | {ind.get('rsi14')} |"
        )
    lines.append("")

    # Strategy parameter reference
    lines.append(f"---\n")
    lines.append(f"## Strategy Parameter Reference\n")
    lines.append(f"| Stock | RSI Ideal | RSI Max | BIAS20 Max | MA Slope Min | Vol Min |")
    lines.append(f"|-------|-----------|---------|------------|-------------|---------|")
    for r in results:
        cfg_path = CONFIG_DIR / f"{r['stock']}.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            e   = cfg.get("entry", {})
            vm  = e.get("volume_min", 0)
            vol_str = f"{vm/10000:.0f}萬" if vm else "ratio"
            lines.append(
                f"| {r['stock']} | {e.get('rsi_ideal','—')} | {e.get('rsi_max','—')} | "
                f"{e.get('bias20_max','—')} | {e.get('ma20_slope_min','—')} | "
                f"{vol_str} |"
            )

    lines.append("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stock Strategy Daily Updater")
    parser.add_argument("--stocks", nargs="*", help="Specify stocks (space separated)")
    parser.add_argument("--report", action="store_true", help="Generate Markdown report")
    parser.add_argument("--json",   action="store_true", help="Output JSON")
    args = parser.parse_args()

    if args.stocks:
        stock_ids = args.stocks
    else:
        stock_ids = [p.stem for p in CONFIG_DIR.glob("*.json")]

    results = []
    errors  = []

    for sid in stock_ids:
        res, err = process_stock(sid)
        if err:
            errors.append(err)
        else:
            results.append(res)

    if args.json:
        output = json.dumps({"results": results, "errors": errors}, ensure_ascii=False, indent=2)
        print(output)
        return output

    # Text output
    for r in results:
        sig  = r.get("signal", "UNKNOWN")
        emoji = {"ENTRY_READY":"[READY]","ENTRY_WATCH":"[WATCH]","NO_SIGNAL":"[NO_SIG]"}.get(sig,"[?]")
        ind  = r.get("indicators", {})
        print(f"{emoji} [{r['stock']}] {r['name']:12s}  signal={sig:15s}  "
              f"P={ind.get('price')}  RSI={ind.get('rsi14')}  "
              f"BIAS={ind.get('bias20')}  slope={ind.get('slope20')}  "
              f"vol_r={ind.get('vol_ratio')}  ATR={ind.get('atr14')}")
        if "exit_levels" in r:
            ex = r["exit_levels"]
            print(f"   => Entry={ex['entry_price']}  SL={ex['stop_loss']}  TP={ex['take_profit']}")

    for e in errors:
        print(f"ERROR: {e}")

    # Markdown report
    if args.report:
        md      = make_markdown_report(results, errors)
        date_str = datetime.now().strftime("%Y-%m-%d")
        rpt_path = REPORT_DIR / f"stock_strategy_daily_{date_str}.md"
        with open(rpt_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\nReport written: {rpt_path}")

    return results, errors


if __name__ == "__main__":
    main()