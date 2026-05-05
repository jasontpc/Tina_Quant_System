"""
stock_tracking_update.py
==========================
讀取所有 stock_strategies/*.json → 更新 stock_tracking.db
檢查進場/出场條件 → 產出訊號（ENTRY_WATCH, ENTRY_LONG, EXIT_SIGNAL）
"""

import csv
import io
import json
import os
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# ── UTF-8 fix for Windows ────────────────────────────────────────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import yfinance as yf

BASE_DIR    = Path(__file__).parent.parent.resolve()
CONFIG_DIR  = BASE_DIR / "configs" / "stock_strategies"
DATA_DIR    = BASE_DIR / "data"
DB_PATH     = DATA_DIR / "stock_tracking.db"
REPORT_DIR  = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# 資料庫工具
# ═══════════════════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def upsert_tracking(conn, row):
    cols = [
        "stock_code","name","market","current_price","rsi","bias20","ma_status",
        "entry_ideal_rsi","entry_signal","entry_price",
        "stop_loss","take_profit","trailing_stop",
        "position_size","max_position","last_updated","next_check",
    ]
    placeholders = ",".join(["?"] * len(cols))
    sql = f"INSERT OR REPLACE INTO stock_tracking ({','.join(cols)}) VALUES ({placeholders})"
    conn.execute(sql, [row.get(c) for c in cols])


def upsert_strategy_params(conn, stock_code, params, updated_at):
    sql = """INSERT OR REPLACE INTO strategy_params
             (stock_code, entry_rsi_min, entry_rsi_max,
              stop_loss_atr, take_profit_atr, max_hold_days, updated_at)
             VALUES (?,?,?,?,?,?,?)"""
    conn.execute(sql, (
        stock_code,
        params.get("entry_rsi_min"),
        params.get("entry_rsi_max"),
        params.get("stop_loss_atr"),
        params.get("take_profit_atr"),
        params.get("max_hold_days"),
        updated_at,
    ))


def log_entry_signal(conn, date, stock_code, signal_type, price, rsi, reason, score):
    sql = """INSERT INTO entry_signals
             (date, stock_code, signal_type, price, rsi, reason, score)
             VALUES (?,?,?,?,?,?,?)"""
    conn.execute(sql, (date, stock_code, signal_type, price, rsi, reason, score))


def log_exit_signal(conn, date, stock_code, exit_type, price, pnl_pct, hold_days, reason):
    sql = """INSERT INTO exit_signals
             (date, stock_code, exit_type, price, pnl_pct, hold_days, reason)
             VALUES (?,?,?,?,?,?,?)"""
    conn.execute(sql, (date, stock_code, exit_type, price, pnl_pct, hold_days, reason))


# ═══════════════════════════════════════════════════════════════════════════
# 技術指標計算
# ═══════════════════════════════════════════════════════════════════════════

def compute_rsi(prices, period=14):
    """計算 RSI（Close price series）。"""
    if len(prices) < period + 1:
        return None
    deltas = prices.diff().dropna()
    gain = deltas.clip(lower=0).rolling(period).mean()
    loss = (-deltas.clip(upper=0)).rolling(period).mean()
    if loss.iloc[-1] == 0:
        return 100
    rs = gain.iloc[-1] / loss.iloc[-1]
    return 100 - (100 / (1 + rs))


def compute_ma(prices, window):
    """簡單移動平均。"""
    if len(prices) < window:
        return None
    return prices.rolling(window).mean().iloc[-1]


def compute_bias20(prices):
    """偏離度 = (current - MA20) / MA20 * 100。"""
    ma20 = compute_ma(prices, 20)
    if ma20 is None or ma20 == 0:
        return None
    return round((prices.iloc[-1] - ma20) / ma20 * 100, 3)


def compute_atr(high, low, close, period=14):
    """計算 ATR。"""
    if len(high) < period + 1:
        return None
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def ma_status(prices):
    """MA 多頭狀態：MA20 > MA60 回傳 'BULL'，否則 'BEAR'。"""
    if len(prices) < 60:
        return "UNKNOWN"
    ma20 = compute_ma(prices, 20)
    ma60 = compute_ma(prices, 60)
    if ma20 is None or ma60 is None:
        return "UNKNOWN"
    return "BULL" if ma20 > ma60 else "BEAR"


import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════
# 取得報價 & 指標
# ═══════════════════════════════════════════════════════════════════════════

def fetch_indicators(stock_code, market, period=None):
    """下載歷史資料並計算指標。TW股需要更長期間才能湊足MA60。"""
    sym = f"{stock_code}.TW" if market == "TW" else stock_code
    if period is None:
        period = "6mo" if market == "TW" else "3mo"
    try:
        ticker = yf.Ticker(sym)
        hist   = ticker.history(period=period, auto_adjust=True)
        if hist.empty or len(hist) < 60:
            return None
        close  = hist["Close"]
        high   = hist["High"]
        low    = hist["Low"]
        volume = hist["Volume"]

        rsi     = compute_rsi(close)
        bias20  = compute_bias20(close)
        status  = ma_status(close)
        atr     = compute_atr(high, low, close)
        current = round(float(close.iloc[-1]), 2)
        return {
            "price":    current,
            "rsi":      round(float(rsi), 1)  if rsi else None,
            "bias20":   bias20,
            "ma_status": status,
            "atr":      round(float(atr), 3) if atr else None,
            "volume":   int(volume.iloc[-1]),
        }
    except Exception as e:
        print(f"  ⚠ [{stock_code}] fetch failed: {e}", file=sys.stderr)
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 訊號評估
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_signals(stock, ind, now_str):
    """根據策略配置與當前指標，判斷訊號。"""
    sig      = "HOLD"
    entry_lo = stock["entry"]["rsi_min"]
    entry_hi = stock["entry"]["rsi_max"]
    rsi      = ind.get("rsi")
    price    = ind.get("price")
    bias20   = ind.get("bias20")
    status   = ind.get("ma_status")
    atr      = ind.get("atr")

    # ── ENTRY_LONG：RSI 在理想區間且 MA 多頭 ──
    if rsi is not None and bias20 is not None:
        rsi_ideal_lo = float(stock["entry"]["rsi_ideal"].split("-")[0])
        rsi_ideal_hi = float(stock["entry"]["rsi_ideal"].split("-")[1])
        bias_ideal   = stock["entry"]["bias20_ideal"].replace("-", " ").split()
        bias_lo      = float(bias_ideal[0])
        bias_hi      = float(bias_ideal[1])

        ma_ok   = status == "BULL"
        rsi_ok  = rsi_ideal_lo <= rsi <= rsi_ideal_hi
        bias_ok = bias_lo <= bias20 <= bias_hi

        if rsi_ok and bias_ok and ma_ok:
            sig = "ENTRY_LONG"
        elif entry_lo <= rsi <= entry_hi and status == "BULL":
            sig = "ENTRY_WATCH"

    # ── EXIT 檢查 ──
    # （由持仓模組單獨觸發，這裡只記錄警示）
    exit_sig = None
    if rsi is not None:
        overbought = stock["exit"].get("rsi_overbought_exit", 72)
        if rsi >= overbought:
            exit_sig = "RSI_OVERBOUGHT"

    return sig, exit_sig


# ═══════════════════════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'═'*60}")
    print(f"  stock_tracking_update.py  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'═'*60}\n")

    config_files = sorted(CONFIG_DIR.glob("*.json"))
    print(f"Loading {len(config_files)} strategy files...\n")

    now_str     = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_str    = datetime.now().strftime("%Y-%m-%d")
    alerts      = []
    summary_rows = []

    conn = get_db()

    for cfg_path in config_files:
        stock_code = cfg_path.stem
        with open(cfg_path, "r", encoding="utf-8") as f:
            stock = json.load(f)

        name    = stock.get("name", stock_code)
        market  = stock.get("market", "TW")
        print(f"  [{stock_code}] {name} ({market})... ", end="", flush=True)

        # ── 抓報價 ──
        ind = fetch_indicators(stock_code, market)
        if ind is None:
            print("SKIP (data unavailable)")
            continue
        print(f"price={ind['price']} rsi={ind['rsi']} bias={ind['bias20']} ma={ind['ma_status']}")

        # ── 訊號評估 ──
        sig, exit_sig = evaluate_signals(stock, ind, now_str)

        # ── 解析策略參數 ──
        rsi_ideal     = stock["entry"].get("rsi_ideal", "40-55")
        rsi_lo, rsi_hi = map(float, rsi_ideal.split("-"))
        stop_loss_atr = stock["exit"].get("stop_loss_atr", 2.0)
        take_profit_atr = stock["exit"].get("take_profit_atr", 4.0)
        max_hold      = stock["exit"].get("max_hold_days", 10)

        # ── 計算停利/停損價（根據 ATR）──
        atr = ind.get("atr", 0)
        stop_loss    = round(ind["price"] * (1 - stock["exit"].get("stop_loss_pct", 5) / 100), 2)
        take_profit  = round(ind["price"] * (1 + stock["exit"].get("take_profit_pct", 10) / 100), 2)
        trailing_stop = round(ind["price"] - atr * stock["exit"].get("trailing_stop_atr", 2.0), 2)

        max_pos_pct  = stock["position"].get("max_position_pct", 20)

        # ── 更新 stock_tracking ──
        row = {
            "stock_code":     stock_code,
            "name":           name,
            "market":         market,
            "current_price":  ind["price"],
            "rsi":            ind["rsi"],
            "bias20":         ind["bias20"],
            "ma_status":      ind["ma_status"],
            "entry_ideal_rsi": rsi_ideal,
            "entry_signal":   sig,
            "entry_price":    None,           # 進場後才填
            "stop_loss":      stop_loss,
            "take_profit":    take_profit,
            "trailing_stop":  trailing_stop,
            "position_size":  0,
            "max_position":   max_pos_pct,
            "last_updated":   now_str,
            "next_check":     date_str,
        }
        upsert_tracking(conn, row)

        # ── 更新 strategy_params ──
        upsert_strategy_params(conn, stock_code, {
            "entry_rsi_min":   rsi_lo,
            "entry_rsi_max":   rsi_hi,
            "stop_loss_atr":   stop_loss_atr,
            "take_profit_atr": take_profit_atr,
            "max_hold_days":   max_hold,
        }, now_str)

        # ── 記錄進場訊號 ──
        if sig in ("ENTRY_LONG", "ENTRY_WATCH"):
            log_entry_signal(
                conn, date_str, stock_code, sig,
                ind["price"], ind["rsi"],
                f"RSI={ind['rsi']} BIAS={ind['bias20']} MA={ind['ma_status']}",
                80 if sig == "ENTRY_LONG" else 60,
            )
            alerts.append(f"  🚀 **{sig}** [{stock_code}] {name}  price={ind['price']}  RSI={ind['rsi']}")

        if exit_sig:
            alerts.append(f"  ⚠️  **EXIT_ALERT** [{stock_code}] {name}: {exit_sig}  RSI={ind['rsi']}")

        # ── 寫入 summary ──
        summary_rows.append({
            "stock":       stock_code,
            "name":        name,
            "market":      market,
            "entry_rsi_min":  rsi_lo,
            "entry_rsi_max":  rsi_hi,
            "stop_loss_atr":  stop_loss_atr,
            "take_profit_atr": take_profit_atr,
            "max_hold":       max_hold,
            "current_price":  ind["price"],
            "current_rsi":   ind["rsi"],
            "bias20":         ind["bias20"],
            "ma_status":      ind["ma_status"],
            "signal":         sig,
        })

    conn.commit()
    conn.close()

    # ── 寫入 stock_strategies_summary.csv ──
    csv_path = DATA_DIR / "stock_strategies_summary.csv"
    if summary_rows:
        cols = ["stock","name","market","entry_rsi_min","entry_rsi_max",
                "stop_loss_atr","take_profit_atr","max_hold",
                "current_price","current_rsi","bias20","ma_status","signal"]
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(summary_rows)
        print(f"\n📄 策略摘要已寫入：{csv_path}")

    # ── 產出每日追蹤報告 ──
    rpt_path = REPORT_DIR / f"stock_tracking_daily_{date_str}.md"
    lines = [
        f"# 📊 股票追蹤每日報告",
        f"**{now_str}**  （共 {len(summary_rows)} 檔）\n",
        "## 訊號摘要\n",
    ]
    entry_long = [r for r in summary_rows if r["signal"] == "ENTRY_LONG"]
    entry_watch = [r for r in summary_rows if r["signal"] == "ENTRY_WATCH"]
    if entry_long:
        lines.append(f"### 🚀 ENTRY_LONG（共 {len(entry_long)} 檔）\n")
        lines.append("| 代碼 | 名稱 | 市場 | 現價 | RSI | BIAS20 | MA |")
        lines.append("|------|------|------|------|-----|--------|---|")
        for r in entry_long:
            lines.append(f"| {r['stock']} | {r['name']} | {r['market']} | {r['current_price']} | {r['current_rsi']} | {r['bias20']} | {r['ma_status']} |")
        lines.append("")
    if entry_watch:
        lines.append(f"### 👀 ENTRY_WATCH（共 {len(entry_watch)} 檔）\n")
        lines.append("| 代碼 | 名稱 | 市場 | 現價 | RSI | BIAS20 | MA |")
        lines.append("|------|------|------|------|-----|--------|---|")
        for r in entry_watch:
            lines.append(f"| {r['stock']} | {r['name']} | {r['market']} | {r['current_price']} | {r['current_rsi']} | {r['bias20']} | {r['ma_status']} |")
        lines.append("")

    if not entry_long and not entry_watch:
        lines.append("_今日無進場訊號_\n")

    lines.append("## 全部股票現況\n")
    lines.append("| 代碼 | 名稱 | 市場 | 現價 | RSI | BIAS20 | MA | 訊號 |")
    lines.append("|------|------|------|------|-----|--------|---|------|")
    for r in summary_rows:
        lines.append(f"| {r['stock']} | {r['name']} | {r['market']} | {r['current_price']} | {r['current_rsi']} | {r['bias20']} | {r['ma_status']} | {r['signal']} |")

    with open(rpt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"📄 每日追蹤報告已寫入：{rpt_path}")

    # ── Alert 列表 ──
    if alerts:
        print("\n═══ 今日 Alert ═══")
        for a in alerts:
            print(a)

    print(f"\n✅ 完成！{datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__":
    main()