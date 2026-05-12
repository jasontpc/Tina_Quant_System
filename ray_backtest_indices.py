# -*- coding: utf-8 -*-
"""
ray_backtest_indices.py
回測：S&P 500 / Nasdaq 100 / SOX 30
"""
import sys, sqlite3, json, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np

DB = 'ray_wisdom.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

today = time.strftime("%Y-%m-%d")

# 三大指數
INDICES = {
    "SPX": "^GSPC",      # S&P 500
    "NDX": "^NDX",       # Nasdaq 100
    "SOX": "^SOX",       # Philadelphia Semiconductor Index
}

print("=== 三大指數回測 ===")
print(f"日期: {today}")
print()

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_sharpe(returns):
    if len(returns) < 5:
        return 0
    mean_ret = returns.mean()
    std_ret = returns.std()
    if std_ret == 0:
        return 0
    return mean_ret / std_ret * np.sqrt(252)

def calc_mdd(equity_curve):
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    return abs(drawdown.min()) * 100

def backtest_index(symbol, ticker, name, start="2024-01-01"):
    try:
        data = yf.download(ticker, start=start, progress=False)
        if data.empty:
            print(f"❌ {name}: 無資料")
            return None
        
        close = data['Close'].dropna().squeeze()
        returns = close.pct_change().dropna()
        
        # Momentum 策略
        mom_5 = close.pct_change(5).dropna()
        mom_20 = close.pct_change(20).dropna()
        
        # RSI
        rsi = calc_rsi(close)
        
        # 均線
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        
        # 信號
        signals = ((mom_5 > 0) & (mom_20 > 0.02) & (close > ma20) & (rsi < 70))
        
        # 回測
        equity = (1 + returns).cumprod()
        strategy_returns = returns[signals.shift(1).fillna(False)]
        strategy_equity = (1 + strategy_returns).cumprod()
        
        if len(strategy_returns) < 10:
            print(f"⚠️  {name}: 信號不足")
            return None
        
        sharpe = calc_sharpe(strategy_returns)
        mdd = calc_mdd(strategy_equity)
        total_return = (strategy_equity.iloc[-1] - 1) * 100
        win_rate = (strategy_returns > 0).sum() / len(strategy_returns) * 100
        num_trades = len(strategy_returns)
        
        print(f"✅ {name} ({symbol})")
        print(f"   Sharpe: {sharpe:.2f} | MDD: {mdd:.2f}% | Win: {win_rate:.1f}%")
        print(f"   Return: {total_return:.2f}% | Trades: {num_trades}")
        print()
        
        return {
            "symbol": symbol,
            "name": name,
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(mdd, 2),
            "total_return": round(total_return, 2),
            "win_rate": round(win_rate, 1),
            "num_trades": num_trades
        }
    except Exception as e:
        print(f"❌ {name}: {e}")
        return None

results = []
for symbol, ticker in INDICES.items():
    name = {"SPX": "S&P 500", "NDX": "Nasdaq 100", "SOX": "SOX 30"}[symbol]
    result = backtest_index(symbol, ticker, name)
    if result:
        results.append(result)
        # 寫入 DB
        c.execute(f'''INSERT INTO backtest_reports
            (timestamp, strategy_name, symbol, indicator, params, sharpe_ratio, max_drawdown, total_return, win_rate, avg_return, num_trades, passed, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (today, f"MOMENTUM_COMBO_{symbol}", symbol, "MOMENTUM",
             json.dumps({"mom5": 0, "mom20": 0.02, "ma20": True, "rsi_max": 70}),
             result["sharpe_ratio"], result["max_drawdown"], result["total_return"],
             result["win_rate"], result["total_return"] / max(result["num_trades"], 1),
             result["num_trades"],
             1 if result["sharpe_ratio"] >= 1.0 else 0,
             f"{symbol} {name} 回測"))

conn.commit()

print("=== 回測寫入完成 ===")
print(f"寫入 {len(results)} 筆到 backtest_reports")

# 顯示 DB 內的指數策略
c.execute("SELECT symbol, strategy_name, sharpe_ratio, max_drawdown, win_rate, num_trades FROM backtest_reports WHERE symbol IN ('SPX','NDX','SOX') ORDER BY sharpe_ratio DESC")
idx_rows = c.fetchall()
if idx_rows:
    print()
    print("📋 DB 內指數策略:")
    for r in idx_rows:
        print(f"   {r[0]} | {r[1]} | Sharpe:{r[2]:.2f} MDD:{r[3]:.2f}% Win:{r[4]:.1f}% Trades:{r[5]}")

conn.close()