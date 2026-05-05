# -*- coding: utf-8 -*-
"""
ETF 獲利策略資料庫 + 歷史交易回測資料庫
功能：
  1. 建立策略資料庫（ETFPro Strategies DB）
  2. 建立歷史回測交易資料庫（Backtest Trades DB）
  3. 執行基礎回測並存入
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import sqlite3
import os
import json
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np

BASE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = os.path.join(BASE, "data")

# =====================================================================
# 1. 建立 ETF 獲利策略資料庫
# =====================================================================
PROFIT_DB = os.path.join(DATA_DIR, "etf_profit_strategies.db")

def init_profit_db():
    """初始化 ETF 獲利策略資料庫"""
    conn = sqlite3.connect(PROFIT_DB)
    cur = conn.cursor()
    
    # 策略主檔
    cur.execute('''CREATE TABLE IF NOT EXISTS strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_name TEXT NOT NULL,
        strategy_type TEXT,  -- RSI, MA, MACD, BOLLINGER, DCA, MOMENTUM
        description TEXT,
        parameters TEXT,  -- JSON 格式儲存參數
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # ETF 策略表現（每次回測結果）
    cur.execute('''CREATE TABLE IF NOT EXISTS etf_strategy_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy_id INTEGER,
        symbol TEXT NOT NULL,
        name TEXT,
        backtest_period TEXT,
        start_date TEXT,
        end_date TEXT,
        total_trades INTEGER,
        winning_trades INTEGER,
        losing_trades INTEGER,
        win_rate REAL,
        avg_return REAL,
        total_return REAL,
        best_trade REAL,
        worst_trade REAL,
        max_drawdown REAL,
        sharpe_ratio REAL,
        avg_holding_days REAL,
        take_profit REAL,
        stop_loss REAL,
        rsi_entry INTEGER,
        rsi_exit INTEGER,
        ma_short INTEGER,
        ma_long INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (strategy_id) REFERENCES strategies(id)
    )''')
    
    # 策略推薦（當前最佳策略）
    cur.execute('''CREATE TABLE IF NOT EXISTS strategy_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        name TEXT,
        market_regime TEXT,  -- BULL, BEAR, SIDEWAYS, OVERBOUGHT, OVERSOLD
        rsi_value REAL,
        recommended_strategy_id INTEGER,
        confidence_score REAL,
        expected_return REAL,
        risk_level TEXT,  -- LOW, MEDIUM, HIGH
        notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recommended_strategy_id) REFERENCES strategies(id)
    )''')
    
    conn.commit()
    conn.close()
    print(f"[OK] ETF Profit Strategies DB: {PROFIT_DB}")

# =====================================================================
# 2. 建立歷史回測交易資料庫
# =====================================================================
BACKTEST_DB = os.path.join(DATA_DIR, "etf_backtest_trades.db")

def init_backtest_db():
    """初始化歷史回測交易資料庫"""
    conn = sqlite3.connect(BACKTEST_DB)
    cur = conn.cursor()
    
    # 完整交易記錄
    cur.execute('''CREATE TABLE IF NOT EXISTS backtest_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        backtest_run_id TEXT,  -- 回測執行 ID
        strategy_id INTEGER,
        symbol TEXT NOT NULL,
        name TEXT,
        direction TEXT,  -- LONG, SHORT
        entry_date TEXT,
        entry_price REAL,
        exit_date TEXT,
        exit_price REAL,
        quantity INTEGER,
        position_value REAL,
        return_pct REAL,
        return_amount REAL,
        holding_days INTEGER,
        exit_reason TEXT,  -- TAKE_PROFIT, STOP_LOSS, TIME_EXIT, SIGNAL
        entry_rsi REAL,
        exit_rsi REAL,
        entry_ma_diff REAL,  -- MA20-MA60 差距
        profit_factor REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 回測執行記錄
    cur.execute('''CREATE TABLE IF NOT EXISTS backtest_runs (
        id TEXT PRIMARY KEY,
        strategy_id INTEGER,
        strategy_name TEXT,
        symbols TEXT,  -- JSON array
        start_date TEXT,
        end_date TEXT,
        total_trades INTEGER,
        winning_trades INTEGER,
        losing_trades INTEGER,
        win_rate REAL,
        total_return REAL,
        avg_return REAL,
        max_drawdown REAL,
        sharpe_ratio REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # 每日市場狀態
    cur.execute('''CREATE TABLE IF NOT EXISTS market_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE,
        symbol TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        rsi_14 REAL,
        rsi_28 REAL,
        ma20 REAL,
        ma60 REAL,
        ma120 REAL,
        vol_ma20 REAL,
        momentum_5d REAL,
        momentum_20d REAL,
        market_zone TEXT,  -- OVERBOUGHT, NEUTRAL, OVERSOLD
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print(f"[OK] ETF Backtest Trades DB: {BACKTEST_DB}")

# =====================================================================
# 3. 內建基礎策略
# =====================================================================
def insert_default_strategies():
    """插入內建策略"""
    conn = sqlite3.connect(PROFIT_DB)
    cur = conn.cursor()
    
    strategies = [
        ("RSI 逆勢策略", "RSI", "RSI<30 進場，RSI>70 出場，適用於均值回歸",
         json.dumps({"entry_rsi": 30, "exit_rsi": 70, "rsi_period": 14, "hold_max_days": 20})),
        ("RSI 順勢策略", "RSI_MOMENTUM", "RSI>50 進場上升趨勢，RSI<40 出場",
         json.dumps({"entry_rsi": 50, "exit_rsi": 40, "rsi_period": 14, "require_uptrend": True})),
        ("MA 黃金交叉", "MA_CROSS", "MA20 上穿 MA60 進場，下穿出場",
         json.dumps({"ma_short": 20, "ma_long": 60, "confirm_bars": 1})),
        ("MA 雙均線", "MA_DUAL", "價格站上 MA20 + MA60 多頭進場，跌破出場",
         json.dumps({"ma_short": 20, "ma_long": 60, "require_both_above": True})),
        ("DCA 定期定額", "DCA", "每月固定日期定額買入，長期持有",
         json.dumps({"dca_day": 1, "dca_amount": 10000, "hold_forever": True})),
        ("動量策略", "MOMENTUM", "近20日動能最強進場，動能轉負出局",
         json.dumps({"momentum_lookback": 20, "momentum_threshold": 0, "hold_days": 30})),
        ("布林帶策略", "BOLLINGER", "價格觸及布林下軌買進，上軌賣出",
         json.dumps({"bb_period": 20, "bb_std": 2, "entry_at": "lower", "exit_at": "upper"})),
        ("風險報酬策略", "RISK_REWARD", "TP:SL = 2:1，每次風險 2% 資金",
         json.dumps({"tp_sl_ratio": 2, "risk_per_trade": 0.02, "atr_multiplier": 1.5})),
    ]
    
    for name, stype, desc, params in strategies:
        cur.execute("SELECT COUNT(*) FROM strategies WHERE strategy_name=?", (name,))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO strategies (strategy_name, strategy_type, description, parameters) VALUES (?, ?, ?, ?)",
                       (name, stype, desc, params))
    
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM strategies")
    count = cur.fetchone()[0]
    conn.close()
    print(f"[OK] Inserted/verified {count} default strategies")

# =====================================================================
# 4. 執行 ETF 回測
# =====================================================================
def run_etf_backtest(symbol, name, start_date="2020-01-01", end_date="2026-04-30"):
    """對 ETF 執行多策略回測"""
    results = []
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        if df.empty or len(df) < 200:
            return results
        
        df = df.reset_index()
        df['Date'] = df['Date'].dt.tz_localize(None)
        closes = df['Close']
        
        # 計算指標
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        df['ma20'] = closes.rolling(20).mean()
        df['ma60'] = closes.rolling(60).mean()
        df['ma120'] = closes.rolling(120).mean()
        
        # === 策略 1: RSI 逆勢 (RSI < 30 買, RSI > 70 賣) ===
        trades = []
        position = None
        entry_price = 0
        entry_date = None
        entry_rsi = 0
        
        for i in range(120, len(df)):
            row = df.iloc[i]
            date = row['Date'].strftime('%Y-%m-%d')
            rsi = row['rsi']
            price = row['Close']
            
            if pd.isna(rsi):
                continue
            
            if position is None:
                if rsi < 30:
                    position = 'long'
                    entry_price = price
                    entry_date = date
                    entry_rsi = rsi
            else:
                ret = (price - entry_price) / entry_price * 100
                if rsi > 70 or ret > 15 or ret < -8 or i - df.index.get_loc(df.index[i]) > 30:
                    trades.append({
                        'symbol': symbol, 'name': name,
                        'entry_date': entry_date, 'entry_price': entry_price,
                        'exit_date': date, 'exit_price': price,
                        'return_pct': ret, 'holding_days': i - df.index.get_loc(df.index[i]),
                        'exit_reason': 'RSI_EXIT' if rsi > 70 else ('TAKE_PROFIT' if ret > 15 else 'STOP_LOSS' if ret < -8 else 'TIME_EXIT'),
                        'entry_rsi': entry_rsi, 'exit_rsi': rsi
                    })
                    position = None
        
        if trades:
            wins = [t for t in trades if t['return_pct'] > 0]
            losses = [t for t in trades if t['return_pct'] <= 0]
            results.append({
                'strategy': 'RSI 逆勢策略', 'strategy_id': 1,
                'symbol': symbol, 'name': name,
                'total_trades': len(trades), 'winning_trades': len(wins), 'losing_trades': len(losses),
                'win_rate': len(wins) / len(trades) * 100 if trades else 0,
                'avg_return': np.mean([t['return_pct'] for t in trades]) if trades else 0,
                'total_return': sum([t['return_pct'] for t in trades]),
                'best_trade': max([t['return_pct'] for t in trades]) if trades else 0,
                'worst_trade': min([t['return_pct'] for t in trades]) if trades else 0,
                'max_drawdown': min([t['return_pct'] for t in trades]) if trades else 0,
                'avg_holding_days': np.mean([t['holding_days'] for t in trades]) if trades else 0,
                'take_profit': 15, 'stop_loss': -8, 'rsi_entry': 30, 'rsi_exit': 70
            })
        
        # === 策略 2: MA 黃金交叉 ===
        trades2 = []
        position = None
        
        for i in range(120, len(df)):
            row = df.iloc[i]
            date_str = row['Date'].strftime('%Y-%m-%d')
            price = row['Close']
            ma20 = row['ma20']
            ma60 = row['ma60']
            prev_ma20 = df.iloc[i-1]['ma20'] if i > 0 else ma20
            prev_ma60 = df.iloc[i-1]['ma60'] if i > 0 else ma60
            
            if pd.isna(ma20) or pd.isna(ma60):
                continue
            
            if position is None:
                if prev_ma20 <= prev_ma60 and ma20 > ma60:
                    position = 'long'
                    entry_price = price
                    entry_date = date_str
                    entry_ma_diff = (ma20 - ma60) / ma60 * 100
            else:
                ret = (price - entry_price) / entry_price * 100
                if prev_ma20 >= prev_ma60 and ma20 < ma60:
                    trades2.append({
                        'symbol': symbol, 'name': name,
                        'entry_date': entry_date, 'entry_price': entry_price,
                        'exit_date': date_str, 'exit_price': price,
                        'return_pct': ret, 'holding_days': i - df.index.get_loc(df.index[i]),
                        'exit_reason': 'MA_DEATH_CROSS',
                        'entry_ma_diff': entry_ma_diff, 'exit_ma_diff': (ma20 - ma60) / ma60 * 100
                    })
                    position = None
        
        if trades2:
            wins = [t for t in trades2 if t['return_pct'] > 0]
            losses = [t for t in trades2 if t['return_pct'] <= 0]
            results.append({
                'strategy': 'MA 黃金交叉', 'strategy_id': 3,
                'symbol': symbol, 'name': name,
                'total_trades': len(trades2), 'winning_trades': len(wins), 'losing_trades': len(losses),
                'win_rate': len(wins) / len(trades2) * 100 if trades2 else 0,
                'avg_return': np.mean([t['return_pct'] for t in trades2]) if trades2 else 0,
                'total_return': sum([t['return_pct'] for t in trades2]),
                'best_trade': max([t['return_pct'] for t in trades2]) if trades2 else 0,
                'worst_trade': min([t['return_pct'] for t in trades2]) if trades2 else 0,
                'max_drawdown': min([t['return_pct'] for t in trades2]) if trades2 else 0,
                'avg_holding_days': np.mean([t['holding_days'] for t in trades2]) if trades2 else 0,
                'take_profit': 0, 'stop_loss': 0, 'ma_short': 20, 'ma_long': 60
            })
        
    except Exception as e:
        print(f"  [X] {symbol} backtest error: {e}")
    
    return results

# =====================================================================
# 主程式
# =====================================================================
print("=" * 60)
print("ETF 獲利策略資料庫 + 歷史交易回測資料庫 建置")
print("=" * 60)
print()

# 初始化資料庫
init_profit_db()
init_backtest_db()
insert_default_strategies()

print()

# ETF 清單（TW + US）
ETF_LIST = [
    # TW ETFs
    ("0050.TW", "元大台灣50"),
    ("0056.TW", "元大高股息"),
    ("00646.TW", "富邦S&P500"),
    ("00662.TW", "富邦NASDAQ100"),
    ("00713.TW", "元大高息低波"),
    ("00757.TW", "統一大FANG+"),
    ("00927.TW", "統一手創未來"),
    # US ETFs
    ("SPY", "S&P 500 ETF"),
    ("QQQ", "Nasdaq 100 ETF"),
    ("IWM", "Russell 2000 ETF"),
    ("VTI", "Vanguard Total ETF"),
    ("DIA", "Dow Jones ETF"),
    ("VGT", "Vanguard Tech ETF"),
    ("XLF", "Financial Select ETF"),
    ("XLE", "Energy Select ETF"),
    ("SMH", "Semi-Conductor ETF"),
]

print(f"=== 執行 ETF 回測（共 {len(ETF_LIST)} 檔）===")
print()

# 連接策略資料庫
conn = sqlite3.connect(PROFIT_DB)
cur = conn.cursor()

all_results = []
for symbol, name in ETF_LIST:
    print(f"  Processing {symbol} ({name})...")
    results = run_etf_backtest(symbol, name)
    
    for r in results:
        cur.execute('''INSERT INTO etf_strategy_performance 
            (strategy_id, symbol, name, backtest_period, start_date, end_date,
             total_trades, winning_trades, losing_trades, win_rate, avg_return,
             total_return, best_trade, worst_trade, max_drawdown, avg_holding_days,
             take_profit, stop_loss, rsi_entry, rsi_exit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (r['strategy_id'], r['symbol'], r['name'], '2020-2026',
             '2020-01-01', '2026-04-30',
             r['total_trades'], r['winning_trades'], r['losing_trades'],
             r['win_rate'], r['avg_return'], r['total_return'],
             r['best_trade'], r['worst_trade'], r['max_drawdown'],
             r['avg_holding_days'], r.get('take_profit', 0), r.get('stop_loss', 0),
             r.get('rsi_entry', 0), r.get('rsi_exit', 0))
        )
        all_results.append(r)
    
    if not results:
        print(f"    No results for {symbol}")

conn.commit()
conn.close()

print()
print("=== 回測結果摘要 ===")
if all_results:
    for r in all_results:
        print(f"  {r['symbol']} | {r['strategy']}: {r['total_trades']} trades, "
              f"WR={r['win_rate']:.1f}%, Avg={r['avg_return']:.2f}%, "
              f"Best={r['best_trade']:.1f}%, Worst={r['worst_trade']:.1f}%")

print()
print(f"=== 資料庫寫入完成 ===")
print(f"  策略資料庫: {PROFIT_DB}")
print(f"  回測資料庫: {BACKTEST_DB}")

# Verify
conn2 = sqlite3.connect(PROFIT_DB)
cur2 = conn2.cursor()
cur2.execute("SELECT COUNT(*) FROM etf_strategy_performance")
perf_count = cur2.fetchone()[0]
cur2.execute("SELECT strategy_name, COUNT(*) FROM etf_strategy_performance GROUP BY strategy_name")
print(f"  策略表現記錄: {perf_count} 筆")
for s, c in cur2.fetchall():
    print(f"    {s}: {c} records")
conn2.close()

print()
print("=== 建置完成 ===")