# -*- coding: utf-8 -*-
"""
Tina Brain - 團隊學習引擎 v3
============================
每個團隊自動：
  1. 從本地 DB（NANA/LEO）或 yfinance 即時（MAGGY/SHERKY）抓取數據
  2. 執行回測（固定進場：RSI區間 + MA多頭 + MACD正）
  3. 評估勝率/平均報酬
  4. 輸出學習報告
"""
import sqlite3
import yfinance as yf
import pandas as pd
import sys
import json
import os
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DB = WORKSPACE / "data" / "yfinance.db"

# ===== 團隊回測參數 =====
TEAM_CONFIG = {
    "NANA": {
        "symbols": ["2382.TW", "2330.TW", "3665.TW", "2317.TW", "3034.TW"],
        "rsi_entry": (30, 45),
        "tp_pct": 0.05, "sl_pct": 0.08,
        "mode": "db",
    },
    "LEO": {
        "symbols": ["2330.TW", "2454.TW", "2317.TW", "2382.TW", "3665.TW",
                     "2344.TW", "6442.TW", "3450.TW", "4908.TW", "3234.TW",
                     "AAOI", "LRCX", "AMAT"],
        "rsi_entry": (30, 50),
        "tp_pct": 0.08, "sl_pct": 0.10,
        "mode": "db",
    },
    "MAGGY": {
        "symbols": ["INTC", "ASML", "AVGO", "QCOM", "MU", "NVDA", "AMD", "META", "AMZN", "TSLA"],
        "rsi_entry": (30, 55),
        "tp_pct": 0.06, "sl_pct": 0.10,
        "mode": "live",
    },
    "SHERKY": {
        "symbols": ["XLV", "VHT", "GLD", "TLT", "LQD", "AGG", "BND", "HYG"],
        "rsi_entry": (25, 45),
        "tp_pct": 0.04, "sl_pct": 0.06,
        "mode": "live",
    },
}


def calc_indicators_from_df(h):
    """計算指標 Series"""
    close = h['Close']
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_l = ema12 - ema26
    macd_s = macd_l.ewm(span=9, adjust=False).mean()
    macd_hist = macd_l - macd_s
    sma20 = close.ewm(span=20, adjust=False).mean()
    sma60 = close.ewm(span=60, adjust=False).mean()
    return close, rsi, macd_hist, sma20, sma60


def backtest_from_df(close, rsi, macd_hist, sma20, sma60, rsi_low, rsi_high, tp_pct, sl_pct, offset=60):
    """通用回測邏輯"""
    trades = []
    in_pos = False
    entry_price = 0.0
    entry_date = ""

    for i in range(offset, len(close)):
        cl = float(close.iloc[i])
        rsi_v = float(rsi.iloc[i]) if not pd.isna(rsi.iloc[i]) else 50
        macd_v = float(macd_hist.iloc[i]) if not pd.isna(macd_hist.iloc[i]) else 0
        sma20_v = float(sma20.iloc[i]) if not pd.isna(sma20.iloc[i]) else 0
        sma60_v = float(sma60.iloc[i]) if not pd.isna(sma60.iloc[i]) else 0

        if not in_pos:
            if rsi_low <= rsi_v <= rsi_high and sma60_v > sma20_v and macd_v > 0:
                in_pos = True
                entry_price = cl
                dt_idx = close.index[i]
                entry_date = dt_idx if isinstance(dt_idx, str) else dt_idx.strftime('%Y-%m-%d')
        else:
            pnl = (cl - entry_price) / entry_price
            if pnl >= tp_pct or pnl <= -sl_pct or i == len(close) - 1:
                dt_idx = close.index[i]
                exit_date = dt_idx if isinstance(dt_idx, str) else dt_idx.strftime('%Y-%m-%d')
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": exit_date,
                    "entry_price": entry_price,
                    "exit_price": cl,
                    "pnl_pct": pnl * 100,
                    "result": "TP" if pnl >= tp_pct else ("SL" if pnl <= -sl_pct else "HOLD")
                })
                in_pos = False

    return trades


def backtest_from_db(symbol, rsi_low, rsi_high, tp_pct, sl_pct):
    """從本地 DB 回測（NANA/LEO）"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    c.execute('''
        SELECT date, close, rsi_14, macd_hist, atr_14, sma_20, sma_60, sma_120
        FROM daily_ohlcv
        WHERE symbol=? AND rsi_14 IS NOT NULL AND atr_14 IS NOT NULL
        AND date >= "2023-01-01"
        ORDER BY date
    ''', (symbol,))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 60:
        return None

    import pandas as pd
    df = pd.DataFrame(rows, columns=['date','close','rsi_14','macd_hist','atr_14','sma_20','sma_60','sma_120'])
    df.set_index('date', inplace=True)
    close = df['close']
    rsi = df['rsi_14']
    macd_hist = df['macd_hist']
    sma20 = df['sma_20']
    sma60 = df['sma_60']

    return backtest_from_df(close, rsi, macd_hist, sma20, sma60, rsi_low, rsi_high, tp_pct, sl_pct)


def backtest_from_yfinance(symbol, rsi_low, rsi_high, tp_pct, sl_pct):
    """從 yfinance 即時回測（MAGGY/SHERKY）"""
    try:
        tk = yf.Ticker(symbol)
        h = tk.history(period="2y")
        if len(h) < 60:
            return None
        close, rsi, macd_hist, sma20, sma60 = calc_indicators_from_df(h)
        return backtest_from_df(close, rsi, macd_hist, sma20, sma60, rsi_low, rsi_high, tp_pct, sl_pct)
    except Exception:
        return None


def score_team(team, cfg):
    """對整個 team 做回測"""
    mode = cfg.get("mode", "db")
    backtest_fn = backtest_from_yfinance if mode == "live" else backtest_from_db

    all_trades = []
    symbol_results = {}

    for sym in cfg["symbols"]:
        trades = backtest_fn(sym, cfg["rsi_entry"][0], cfg["rsi_entry"][1], cfg["tp_pct"], cfg["sl_pct"])
        if trades:
            symbol_results[sym] = trades
            all_trades.extend(trades)

    if not all_trades:
        return None

    wins = [t for t in all_trades if t["pnl_pct"] > 0]
    losses = [t for t in all_trades if t["pnl_pct"] <= 0]
    win_rate = len(wins) / len(all_trades) * 100
    avg_win = sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0
    avg_pnl = sum(t["pnl_pct"] for t in all_trades) / len(all_trades)

    sym_stats = {}
    for sym, trades in symbol_results.items():
        w = [t for t in trades if t["pnl_pct"] > 0]
        wr = len(w) / len(trades) * 100 if trades else 0
        avg = sum(t["pnl_pct"] for t in trades) / len(trades) if trades else 0
        sym_stats[sym] = {"trades": len(trades), "win_rate": round(wr, 1), "avg_pnl": round(avg, 2)}

    return {
        "team": team,
        "total_trades": len(all_trades),
        "win_rate": round(win_rate, 1),
        "avg_pnl": round(avg_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "wins": len(wins),
        "losses": len(losses),
        "symbols": sym_stats,
        "timestamp": datetime.now().isoformat(),
        "params": {
            "rsi_entry": cfg["rsi_entry"],
            "tp_pct": cfg["tp_pct"],
            "sl_pct": cfg["sl_pct"],
        }
    }


def print_report(results):
    print("=" * 65)
    print("  Tina Brain - 團隊學習與回測報告 v3")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)
    print()

    for res in results:
        if not res:
            continue
        t = res["team"]
        p = res["params"]
        print(f"[{t}] 回測結果（RSI {p['rsi_entry']} | TP {p['tp_pct']*100:.0f}% | SL {p['sl_pct']*100:.0f}%）")
        print(f"  總交易: {res['total_trades']} | 勝率: {res['win_rate']}% | 平均報酬: {res['avg_pnl']:+.2f}%")
        print(f"  平均獲利: {res['avg_win']:+.2f}% | 平均虧損: {res['avg_loss']:+.2f}%")

        best = sorted(res["symbols"].items(), key=lambda x: x[1]["win_rate"], reverse=True)[:5]
        print(f"  🏆 最佳: ", end="")
        for sym, s in best:
            if s["win_rate"] > 0:
                print(f"  {sym} {s['win_rate']}%({s['trades']}筆)  ", end="")
        print()

        low = [x for x in res["symbols"].items() if x[1]["win_rate"] < 60]
        if low:
            print(f"  ⚠️  低勝率: ", end="")
            for sym, s in low[:3]:
                print(f"  {sym} {s['win_rate']}%({s['trades']}筆)  ", end="")
            print()
        print()
        print("-" * 65)

    print()
    print("[Tina 大腦策略建議]")
    for res in results:
        if not res:
            continue
        t = res["team"]
        wr = res["win_rate"]
        avg = res["avg_pnl"]
        if wr >= 65 and avg > 0:
            status = "🟢 可用"
        elif wr >= 55:
            status = "🟡 觀察"
        else:
            status = "🔴 停用"
        print(f"  {t}: 勝率{wr}% 平均報酬{avg:+.2f}% → {status}")


def main():
    print()
    print("[Tina Brain] 團隊學習引擎 v3 啟動")
    print()

    all_results = []
    for team, cfg in TEAM_CONFIG.items():
        print(f"  Running {team} backtest ({len(cfg['symbols'])} symbols, {cfg['mode']})...", end=" ", flush=True)
        res = score_team(team, cfg)
        if res:
            print(f"OK — {res['total_trades']} trades, WR={res['win_rate']}%, Avg={res['avg_pnl']:+.2f}%")
        else:
            print("NO DATA")
        all_results.append(res)

    print()
    print_report([r for r in all_results if r])

    out_path = WORKSPACE / "data" / "team_learning_results.json"
    save_results([r for r in all_results if r], str(out_path))
    print(f"Results saved: {out_path}")


def save_results(results, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
