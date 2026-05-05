"""
stock_signal_scanner.py
==========================
每日掃描所有股票，根據策略配置檢查進場條件。
產出 Markdown 格式的每日訊號報告。
"""

import csv
import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import yfinance as yf
import pandas as pd

BASE_DIR   = Path(__file__).parent.parent.resolve()
CONFIG_DIR = BASE_DIR / "configs" / "stock_strategies"
DATA_DIR   = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_CSV = DATA_DIR / "stock_strategies_summary.csv"


# ═══════════════════════════════════════════════════════════════════════════
# 指標計算（同 stock_tracking_update.py）
# ═══════════════════════════════════════════════════════════════════════════

def compute_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    deltas = prices.diff().dropna()
    gain   = deltas.clip(lower=0).rolling(period).mean()
    loss   = (-deltas.clip(upper=0)).rolling(period).mean()
    if loss.iloc[-1] == 0:
        return 100
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100 - (100 / (1 + rs)))


def compute_ma(prices, window):
    if len(prices) < window:
        return None
    return float(prices.rolling(window).mean().iloc[-1])


def compute_bias20(prices):
    ma20 = compute_ma(prices, 20)
    if ma20 is None or ma20 == 0:
        return None
    return round(float((prices.iloc[-1] - ma20) / ma20 * 100), 3)


def ma_status(prices):
    if len(prices) < 60:
        return "UNKNOWN"
    ma20 = compute_ma(prices, 20)
    ma60 = compute_ma(prices, 60)
    if ma20 is None or ma60 is None:
        return "UNKNOWN"
    return "BULL" if ma20 > ma60 else "BEAR"


def fetch_latest(stock_code, market, period=None):
    sym = f"{stock_code}.TW" if market == "TW" else stock_code
    if period is None:
        period = "6mo" if market == "TW" else "3mo"
    try:
        ticker = yf.Ticker(sym)
        h      = ticker.history(period=period, auto_adjust=True)
        if h.empty or len(h) < 60:
            return None
        close = h["Close"]
        return {
            "price":     round(float(close.iloc[-1]), 2),
            "prev_close": round(float(close.iloc[-2]), 2),
            "rsi":       round(compute_rsi(close), 1),
            "bias20":    compute_bias20(close),
            "ma_status": ma_status(close),
            "volume":    int(h["Volume"].iloc[-1]),
            "change_pct": round(float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100), 2),
        }
    except Exception as e:
        print(f"  ⚠ [{stock_code}] {e}", file=sys.stderr)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 訊號評估
# ═══════════════════════════════════════════════════════════════════════════

def score_entry(stock, ind):
    """回傳 (signal, score, reasons)"""
    rsi   = ind.get("rsi")
    bias  = ind.get("bias20")
    ma    = ind.get("ma_status")
    price = ind.get("price")

    if rsi is None or bias is None or ma == "UNKNOWN":
        return "HOLD", 0, []

    rsi_ideal = stock["entry"]["rsi_ideal"]
    rsi_lo, rsi_hi = map(float, rsi_ideal.split("-"))

    bias_ideal = stock["entry"]["bias20_ideal"].replace("-", " ").split()
    bias_lo    = float(bias_ideal[0])
    bias_hi    = float(bias_ideal[1])

    score = 0
    reasons = []

    # MA 多頭
    if ma == "BULL":
        score += 30
        reasons.append("MA多頭")
    else:
        reasons.append("MA空頭")

    # RSI 理想區間
    if rsi_lo <= rsi <= rsi_hi:
        score += 40
        reasons.append(f"RSI理想區間({rsi_lo}-{rsi_hi})")
    elif stock["entry"]["rsi_min"] <= rsi <= stock["entry"]["rsi_max"]:
        score += 20
        reasons.append(f"RSI可接受區間")
    else:
        reasons.append(f"RSI偏離({rsi})")

    # BIAS 理想區間
    if bias_lo <= bias <= bias_hi:
        score += 20
        reasons.append(f"BIAS理想({bias})")
    elif abs(bias) < abs(stock["entry"]["bias20_max"]):
        score += 10
        reasons.append(f"BIAS合理")
    else:
        reasons.append(f"BIAS偏離({bias})")

    # 成交量放大
    vol_ratio = stock["entry"].get("volume_ratio_min", 1.2)
    # 簡化：分數已足夠

    # 法人買超條件（可選）
    inst_req = stock["entry"].get("inst_required", False)

    if score >= 80 and ma == "BULL" and rsi_lo <= rsi <= rsi_hi:
        signal = "ENTRY_LONG"
    elif score >= 55 and ma == "BULL":
        signal = "ENTRY_WATCH"
    else:
        signal = "HOLD"

    return signal, score, reasons


# ═══════════════════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════════════════

def main():
    now_str  = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'═'*60}")
    print(f"  stock_signal_scanner.py  {now_str}")
    print(f"{'═'*60}\n")

    configs = sorted(CONFIG_DIR.glob("*.json"))
    rows   = []
    signals = []

    for cfg_path in configs:
        stock_code = cfg_path.stem
        with open(cfg_path, "r", encoding="utf-8") as f:
            stock = json.load(f)

        name   = stock.get("name", stock_code)
        market = stock.get("market", "TW")

        print(f"  [{stock_code}] {name} ({market})... ", end="", flush=True)
        ind = fetch_latest(stock_code, market)
        if ind is None:
            print("SKIP")
            continue
        print(f"price={ind['price']} rsi={ind['rsi']} bias={ind['bias20']} ma={ind['ma_status']}")

        sig, score, reasons = score_entry(stock, ind)

        rsi_ideal = stock["entry"]["rsi_ideal"]
        rsi_lo, rsi_hi = map(float, rsi_ideal.split("-"))

        row = {
            "stock":        stock_code,
            "name":         name,
            "market":       market,
            "type":         stock.get("type", "unknown"),
            "team":         stock.get("team", "Nana"),
            "entry_rsi_min": stock["entry"]["rsi_min"],
            "entry_rsi_max": stock["entry"]["rsi_max"],
            "stop_loss_atr": stock["exit"]["stop_loss_atr"],
            "take_profit_atr": stock["exit"]["take_profit_atr"],
            "max_hold":     stock["exit"]["max_hold_days"],
            "current_price": ind["price"],
            "prev_close":   ind["prev_close"],
            "change_pct":   ind["change_pct"],
            "current_rsi":   ind["rsi"],
            "bias20":        ind["bias20"],
            "ma_status":     ind["ma_status"],
            "volume":        ind["volume"],
            "signal":        sig,
            "score":         score,
            "reasons":       "; ".join(reasons),
        }
        rows.append(row)

        if sig != "HOLD":
            emoji = "🚀" if sig == "ENTRY_LONG" else "👀"
            signals.append(f"  {emoji} **{sig}** [{stock_code}] {name}  "
                          f"price={ind['price']}  RSI={ind['rsi']}  score={score}")
            signals.append(f"      原因: {row['reasons']}")

    # ── 寫入 CSV ──
    if rows:
        cols = ["stock","name","market","type","team",
                "entry_rsi_min","entry_rsi_max","stop_loss_atr","take_profit_atr","max_hold",
                "current_price","prev_close","change_pct","current_rsi","bias20",
                "ma_status","volume","signal","score","reasons"]
        with open(SUMMARY_CSV, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        print(f"\n📄 Summary CSV → {SUMMARY_CSV}")

    # ── 產出 Markdown 報告 ──
    entry_long  = [r for r in rows if r["signal"] == "ENTRY_LONG"]
    entry_watch = [r for r in rows if r["signal"] == "ENTRY_WATCH"]
    holds       = [r for r in rows if r["signal"] == "HOLD"]

    lines = [
        f"# 📡 每日訊號報告",
        f"**{now_str}**  掃描 {len(rows)} 檔\n",
    ]

    if entry_long:
        lines += [
            f"## 🚀 ENTRY_LONG（共 {len(entry_long)} 檔）\n",
            "| 代碼 | 名稱 | 市場 | 現價 | 漲跌% | RSI | BIAS20 | MA | 分數 |",
            "|------|------|------|------|------|-----|--------|---|------|",
        ]
        for r in sorted(entry_long, key=lambda x: x["score"], reverse=True):
            lines.append(
                f"| {r['stock']} | {r['name']} | {r['market']} | "
                f"{r['current_price']} | {r['change_pct']}% | "
                f"{r['current_rsi']} | {r['bias20']} | {r['ma_status']} | "
                f"{r['score']} |"
            )
        lines.append("")

    if entry_watch:
        lines += [
            f"## 👀 ENTRY_WATCH（共 {len(entry_watch)} 檔）\n",
            "| 代碼 | 名稱 | 市場 | 現價 | 漲跌% | RSI | BIAS20 | MA | 分數 | 原因 |",
            "|------|------|------|------|------|-----|--------|---|------|------|",
        ]
        for r in sorted(entry_watch, key=lambda x: x["score"], reverse=True):
            lines.append(
                f"| {r['stock']} | {r['name']} | {r['market']} | "
                f"{r['current_price']} | {r['change_pct']}% | "
                f"{r['current_rsi']} | {r['bias20']} | {r['ma_status']} | "
                f"{r['score']} | {r['reasons']} |"
            )
        lines.append("")

    lines += [
        f"## 📋 全部股票摘要（共 {len(rows)} 檔）\n",
        "| 代碼 | 名稱 | 市場 | 現價 | 漲跌% | RSI | MA | 訊號 |",
        "|------|------|------|------|------|-----|---|------|",
    ]
    for r in sorted(rows, key=lambda x: (0 if x["signal"] != "HOLD" else 1, -x["score"])):
        sig_emoji = {"ENTRY_LONG": "🚀", "ENTRY_WATCH": "👀"}.get(r["signal"], "—")
        lines.append(
            f"| {r['stock']} | {r['name']} | {r['market']} | "
            f"{r['current_price']} | {r['change_pct']}% | "
            f"{r['current_rsi']} | {r['ma_status']} | "
            f"{sig_emoji} {r['signal']} |"
        )

    rpt_path = REPORT_DIR / f"daily_signal_report_{date_str}.md"
    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"📄 訊號報告 → {rpt_path}")

    if signals:
        print("\n═══ 今日訊號 ═══")
        for s in signals:
            print(s)

    print(f"\n✅ 完成！")


if __name__ == "__main__":
    main()