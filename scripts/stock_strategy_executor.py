"""
stock_strategy_executor.py
===========================
讀取個股策略配置，檢查進場/出场條件，產出交易訊號。
"""

import json
import os
import sys
import io
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Windows cp950 UTF-8 fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── 路徑設定 ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent.resolve()
CONFIG_DIR = BASE_DIR / "configs" / "stock_strategies"
DATA_DIR   = BASE_DIR / "data"   / "stock_strategies"
LOG_DIR    = BASE_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── 嘗試引入 yfinance ────────────────────────────────────────────────────
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

import argparse


# ═══════════════════════════════════════════════════════════════════════════
# 工具函式
# ═══════════════════════════════════════════════════════════════════════════

def calc_atr(high, low, close, period=14):
    """計算 ATR (Average True Range)."""
    trs = []
    for i in range(1, len(high)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i]  - close[i-1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def calc_rsi(prices, period=14):
    """計算 RSI."""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains  = [d for d in deltas[-period:] if d > 0]
    losses = [-d for d in deltas[-period:] if d < 0]
    avg_gain = sum(gains)  / period if gains  else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_ma(prices, n):
    """簡單移動平均."""
    if len(prices) < n:
        return None
    return sum(prices[-n:]) / n


def calc_bias(price, ma20):
    """偏離度 BIAS20."""
    if ma20 is None or ma20 == 0:
        return None
    return (price - ma20) / ma20 * 100


def ma_slope(prices, n=20, lookback=5):
    """MA 斜率（最後 n 日趨勢）."""
    if len(prices) < n + lookback - 1:
        return None
    ma_vals = [calc_ma(prices[:i+1], n) for i in range(n-1, len(prices))]
    if len(ma_vals) < lookback:
        return None
    # 簡單線性迴歸斜率
    x = list(range(lookback))
    y = ma_vals[-lookback:]
    x_mean = sum(x) / lookback
    y_mean = sum(y) / lookback
    num = sum((x[i]-x_mean)*(y[i]-y_mean) for i in range(lookback))
    den = sum((x[i]-x_mean)**2 for i in range(lookback))
    return num / den if den != 0 else 0


def load_strategy(stock_id):
    """載入個股策略配置."""
    path = CONFIG_DIR / f"{stock_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到策略檔：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_recent_data(stock_id, market="TW", days=60):
    """用 yfinance 抓取歷史數據."""
    if not HAS_YF:
        return None

    # 轉換代碼：台股加 .TW，美股不變
    yf_symbol = stock_id
    if market == "TW":
        yf_symbol = f"{stock_id}.TW"

    try:
        ticker = yf.Ticker(yf_symbol)
        hist   = ticker.history(period=f"{days}d", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None
        return hist
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 進場條件評估
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_entry(stock_id, strategy, data):
    """
    根據策略配置評估是否滿足進場條件。
    data: yfinance History (columns: Open/High/Low/Close/Volume)
    回傳 (signal: str, details: dict)
    """
    if data is None or len(data) < 30:
        return "NO_DATA", {}

    close  = list(data["Close"])
    high   = list(data["High"])
    low    = list(data["Low"])
    volume = list(data["Volume"])

    price   = close[-1]
    rsi     = calc_rsi(close)
    ma20    = calc_ma(close, 20)
    ma60    = calc_ma(close, 60) if len(close) >= 60 else None
    bias20  = calc_bias(price, ma20)
    slope20 = ma_slope(close)
    avg_vol = sum(volume[-20:]) / 20 if len(volume) >= 20 else 0
    vol_ratio = volume[-1] / avg_vol if avg_vol > 0 else 0
    atr     = calc_atr(high, low, close)

    entry = strategy["entry"]

    # ── RSI 檢查 ──────────────────────────────────────────────────────────
    rsi_ok  = entry.get("rsi_min", 0)  <= rsi <= entry.get("rsi_max", 100)
    rsi_ideal_hit = False
    if "rsi_ideal" in entry:
        try:
            lo, hi = map(float, entry["rsi_ideal"].split("-"))
            rsi_ideal_hit = lo <= rsi <= hi
        except Exception:
            rsi_ideal_hit = rsi_ok

    # ── MA 排列 ─────────────────────────────────────────────────────────────
    ma_ok = True
    if entry.get("ma_required"):
        if ma20 is None or ma60 is None:
            ma_ok = False
        elif "MA20>MA60" in entry["ma_required"]:
            ma_ok = ma20 > ma60

    # ── MA 斜率 ─────────────────────────────────────────────────────────────
    slope_ok = True
    if entry.get("ma20_slope_min"):
        slope_ok = slope20 is not None and slope20 >= entry["ma20_slope_min"]

    # ── BIAS20 ──────────────────────────────────────────────────────────────
    bias_ok = True
    if entry.get("bias20_max"):
        bias_ok = bias20 is not None and abs(bias20) <= entry["bias20_max"]

    # ── 成交量 ──────────────────────────────────────────────────────────────
    vol_ok = True
    if entry.get("volume_min"):
        vol_min_tw = entry["volume_min"]  # 股數（台股）
        vol_ok = volume[-1] >= vol_min_tw
    elif entry.get("volume_ratio_min"):
        vol_ok = vol_ratio >= entry["volume_ratio_min"]

    # ── 法人（暫時用 volume ratio 代理，未來可串 FINMIND） ──────────────────
    inst_ok = True  # 預設通過

    score = sum([
        rsi_ok, rsi_ideal_hit,
        ma_ok, slope_ok, bias_ok,
        vol_ok, inst_ok
    ])

    details = {
        "price":     round(price, 2),
        "rsi":       round(rsi, 1) if rsi else None,
        "ma20":      round(ma20, 2) if ma20 else None,
        "ma60":      round(ma60, 2) if ma60 else None,
        "bias20":    round(bias20, 2) if bias20 else None,
        "slope20":   round(slope20, 4) if slope20 else None,
        "atr":       round(atr, 2) if atr else None,
        "vol":       volume[-1],
        "vol_ratio": round(vol_ratio, 2),
        "checks": {
            "rsi":       rsi_ok,
            "rsi_ideal": rsi_ideal_hit,
            "ma":        ma_ok,
            "slope":     slope_ok,
            "bias":      bias_ok,
            "volume":    vol_ok,
        },
        "score": score,
        "max_score": 7,
    }

    # signal
    if not rsi_ok:
        return "RSI_OUT_OF_RANGE", details
    if not ma_ok:
        return "MA排列不符", details
    if not slope_ok:
        return "MA斜率不足", details
    if not bias_ok:
        return "BIAS過大", details
    if not vol_ok:
        return "成交量不足", details
    if rsi_ideal_hit and ma_ok and slope_ok and bias_ok and vol_ok:
        return "ENTRY_READY", details
    # 部分滿足但非理想
    if score >= 5:
        return "ENTRY_WATCH", details
    return "NO_SIGNAL", details


# ═══════════════════════════════════════════════════════════════════════════
# 停損 / 停利計算
# ═══════════════════════════════════════════════════════════════════════════

def calc_exit_prices(stock_id, strategy, entry_price, data):
    """
    根據進場價與策略計算停損/停利/移動停損價格。
    回傳 dict of prices.
    """
    high  = list(data["High"])
    low   = list(data["Low"])
    close = list(data["Close"])
    atr   = calc_atr(high, low, close)

    if atr is None:
        atr = entry_price * 0.02  # fallback: 2%

    ex = strategy["exit"]

    stop_loss      = round(entry_price * (1 - ex["stop_loss_pct"] / 100), 2)
    take_profit    = round(entry_price * (1 + ex.get("take_profit_pct", 10) / 100), 2)
    trailing_stop  = None
    if ex.get("trailing_stop_atr"):
        trailing_stop = round(entry_price - ex["trailing_stop_atr"] * atr, 2)

    return {
        "entry_price":  entry_price,
        "stop_loss":    stop_loss,
        "take_profit":  take_profit,
        "trailing_stop": trailing_stop,
        "atr":           round(atr, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 主報告產生器
# ═══════════════════════════════════════════════════════════════════════════

def generate_signal_report(stock_id):
    """對單一股票產生完整策略訊號報告."""
    try:
        strategy = load_strategy(stock_id)
    except FileNotFoundError:
        return None, f"[{stock_id}] 找不到策略設定檔"

    market = strategy.get("market", "TW")
    data   = fetch_recent_data(stock_id, market)

    signal, details = evaluate_entry(stock_id, strategy, data)

    if signal == "NO_DATA":
        return None, f"[{stock_id}] 無法取得資料"

    report = {
        "stock":       stock_id,
        "name":        strategy.get("name", stock_id),
        "market":      market,
        "signal":      signal,
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M"),
        "indicators":  details,
    }

    if signal == "ENTRY_READY" and data is not None:
        entry_price = float(data["Close"].iloc[-1])
        exit_prices = calc_exit_prices(stock_id, strategy, entry_price, data)
        report["entry_price"] = entry_price
        report["exit_levels"] = exit_prices

    return report, None


def scan_all_strategies():
    """掃描所有策略檔，產出訊號報告."""
    configs = list(CONFIG_DIR.glob("*.json"))
    results = []
    errors  = []

    for cfg in configs:
        stock_id = cfg.stem
        report, err = generate_signal_report(stock_id)
        if err:
            errors.append(err)
        elif report:
            results.append(report)

    return results, errors


# ═══════════════════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="個股策略訊號掃描器")
    parser.add_argument("--stock",  help="指定股票代碼（不含 .json）")
    parser.add_argument("--all",    action="store_true", help="掃描所有策略")
    parser.add_argument("--format", default="text", choices=["text", "json"])
    args = parser.parse_args()

    if args.stock:
        report, err = generate_signal_report(args.stock)
        if err:
            print(f"錯誤：{err}")
            sys.exit(1)
        output = json.dumps(report, ensure_ascii=False, indent=2)
    elif args.all:
        results, errors = scan_all_strategies()
        if args.format == "json":
            output = json.dumps({"results": results, "errors": errors}, ensure_ascii=False, indent=2)
        else:
            lines = []
            lines.append(f"{'='*60}")
            lines.append(f"  個股策略掃描報告  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append(f"{'='*60}")
            for r in results:
                sig_emoji = {
                    "ENTRY_READY": "ENTRY_READY",
                    "ENTRY_WATCH": "ENTRY_WATCH",
                    "RSI_OUT_OF_RANGE": "RSI_OUT_OF_RANGE",
                    "MA排列不符": "MA排列不符",
                    "MA斜率不足": "MA斜率不足",
                    "BIAS過大": "BIAS過大",
                    "成交量不足": "成交量不足",
                }.get(r["signal"], "UNKNOWN")

                lines.append(f"\n[{sig_emoji}] [{r['stock']}] {r['name']}")
                lines.append(f"   Signal: {r['signal']}")
                ind = r.get("indicators", {})
                lines.append(f"   Price={ind.get('price')}  RSI={ind.get('rsi')}  BIAS20={ind.get('bias20')}")
                lines.append(f"   MA20={ind.get('ma20')}  MA60={ind.get('ma60')}  slope={ind.get('slope20')}")
                lines.append(f"   ATR={ind.get('atr')}  vol_ratio={ind.get('vol_ratio')}  score={ind.get('score')}/{ind.get('max_score')}")

                if "exit_levels" in r:
                    ex = r["exit_levels"]
                    lines.append(f"   => Entry: {ex['entry_price']}  SL: {ex['stop_loss']}  TP: {ex['take_profit']}  TS: {ex.get('trailing_stop')}")

            for e in errors:
                lines.append(f"\nERROR: {e}")
            output = "\n".join(lines)
    else:
        print("Usage: stock_strategy_executor.py --stock 2330 --all --format json")
        sys.exit(0)

    print(output)
    return output


if __name__ == "__main__":
    main()