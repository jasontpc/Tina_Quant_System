# -*- coding: utf-8 -*-
"""
Leo 科技股波段 v7.0 — 歷史回測系統
功能：
  - 8檔科技股（2330/2454/2317/2379/2376/2382/3665/3034）
  - WFA 最優參數：RSI_P=12, Thresh=40, Hold=10d, TP=10%, SL=8%
  - 完整進出场邏輯
  - 計算 WR、AvgReturn、Sharpe、MaxDD
  - 輸出 CSV 報告
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

# === WFA 最優參數（v2.0 自主學習）===
# 2026-04-27 | Score: 48.21 | WR: 77.0% | Avg: +3.95% | Trades: 61
RSI_PERIOD = 12
RSI_THRESHOLD = 55
HOLD_DAYS = 45
TAKE_PROFIT = 0.06
STOP_LOSS = 0.1      # 原8% → 10%（擴大停損容忍）

# 股票池
STOCKS = {
    '2330': '台積電',
    '2454': '聯發科',
    '2317': '鴻海',
    '2379': '瑞昱',
    '2376': '技嘉',
    '2382': '廣達',
    '3665': '穎崴',
    '3034': '緯穎'
}

def calc_rsi(prices, period=12):
    """計算 RSI"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calc_ma(prices, period):
    """計算移動平均線"""
    return prices.rolling(window=period).mean()

def calc_momentum(prices, days=5):
    """計算動量（%變化）"""
    return prices.pct_change(days) * 100

def backtest_stock(ticker, start_date='2022-01-01', end_date=None):
    """對單一股票進行回測"""
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')
    
    try:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df.empty or len(df) < 60:
            return None
        
        close = df['Close'].squeeze()
        volume = df['Volume'].squeeze()
        
        # 計算技術指標
        rsi = calc_rsi(close, RSI_PERIOD)
        ma60 = calc_ma(close, 60)
        momentum = calc_momentum(close, 5)
        
        trades = []
        in_position = False
        entry_price = 0
        entry_date = None
        
        for i in range(60, len(df) - HOLD_DAYS):
            date = df.index[i]
            price = close.iloc[i]
            current_rsi = rsi.iloc[i]
            current_ma60 = ma60.iloc[i]
            current_momentum = momentum.iloc[i]
            
            if in_position:
                # 持有期間檢查停利/停損/到期
                hold_days = (df.index[i] - entry_date).days
                pnl_pct = (price - entry_price) / entry_price * 100
                
                # 停利
                if pnl_pct >= TAKE_PROFIT * 100:
                    trades.append({
                        'ticker': ticker,
                        'entry_date': entry_date.strftime('%Y-%m-%d'),
                        'exit_date': date.strftime('%Y-%m-%d'),
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl_pct': pnl_pct,
                        'exit_reason': 'TP'
                    })
                    in_position = False
                    continue
                
                # 停損
                if pnl_pct <= -STOP_LOSS * 100:
                    trades.append({
                        'ticker': ticker,
                        'entry_date': entry_date.strftime('%Y-%m-%d'),
                        'exit_date': date.strftime('%Y-%m-%d'),
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl_pct': pnl_pct,
                        'exit_reason': 'SL'
                    })
                    in_position = False
                    continue
                
                # 持有期滿
                if hold_days >= HOLD_DAYS:
                    trades.append({
                        'ticker': ticker,
                        'entry_date': entry_date.strftime('%Y-%m-%d'),
                        'exit_date': date.strftime('%Y-%m-%d'),
                        'entry_price': entry_price,
                        'exit_price': price,
                        'pnl_pct': pnl_pct,
                        'exit_reason': 'HOLD'
                    })
                    in_position = False
                    continue
            else:
                # 進場條件檢查
                if (current_rsi < RSI_THRESHOLD and 
                    not pd.isna(current_ma60) and 
                    price > current_ma60 and 
                    current_momentum > 2):
                    in_position = True
                    entry_price = price
                    entry_date = df.index[i]
        
        return trades
    except Exception as e:
        print(f"  [錯誤] {ticker}: {e}")
        return None

def analyze_results(all_trades):
    """計算回測績效指標"""
    if not all_trades:
        return {}
    
    df = pd.DataFrame(all_trades)
    
    total_trades = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    losses = len(df[df['pnl_pct'] <= 0])
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    
    avg_return = df['pnl_pct'].mean()
    
    # 計算 Sharpe Ratio（假設無風險利率 4%）
    risk_free = 0.04
    returns = df['pnl_pct'] / 100
    if len(returns) > 1 and returns.std() > 0:
        sharpe = (returns.mean() - risk_free) / returns.std() * np.sqrt(252)
    else:
        sharpe = 0
    
    # 最大Drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min() * 100
    
    return {
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'total_return': df['pnl_pct'].sum()
    }

def main():
    print("=" * 60)
    print("Leo 科技股波段 v7.0 — 歷史回測系統")
    print("=" * 60)
    print(f"WFA 參數: RSI_P={RSI_PERIOD}, Thresh={RSI_THRESHOLD}, Hold={HOLD_DAYS}d, TP={TAKE_PROFIT*100}%, SL={STOP_LOSS*100}%")
    print(f"回測期間: 2022-01-01 ~ {datetime.today().strftime('%Y-%m-%d')}")
    print()
    
    all_trades = []
    results = []
    
    for ticker, name in STOCKS.items():
        print(f"▶ 回測 {ticker} {name}...", end=' ')
        trades = backtest_stock(f"{ticker}.TW")
        if trades:
            print(f"完成 ({len(trades)} 筆交易)")
            all_trades.extend(trades)
            for t in trades:
                t['name'] = name
            results.append({'ticker': ticker, 'name': name, 'trades': len(trades)})
        else:
            print("無交易資料")
    
    print()
    print("=" * 60)
    print("回測結果")
    print("=" * 60)
    
    if all_trades:
        df = pd.DataFrame(all_trades)
        
        # 依 ticker 統計
        print(f"\n{'代碼':<6} {'名稱':<8} {'筆數':<6} {'勝率':<8} {'平均報酬':<10} {'總報酬':<10}")
        print("-" * 50)
        
        for ticker, name in STOCKS.items():
            stock_df = df[df['ticker'] == ticker]
            if len(stock_df) > 0:
                wr = len(stock_df[stock_df['pnl_pct'] > 0]) / len(stock_df) * 100
                avg = stock_df['pnl_pct'].mean()
                total = stock_df['pnl_pct'].sum()
                print(f"{ticker:<6} {name:<8} {len(stock_df):<6} {wr:>6.1f}% {avg:>8.2f}% {total:>8.2f}%")
        
        # 總績效
        perf = analyze_results(all_trades)
        print()
        print("▎整體績效")
        print("-" * 50)
        print(f"  總交易筆數: {perf['total_trades']}")
        print(f"  勝利次數: {perf['wins']} / 失敗次數: {perf['losses']}")
        print(f"  勝率: {perf['win_rate']:.1f}%")
        print(f"  平均報酬: {perf['avg_return']:.2f}%")
        print(f"  總報酬: {perf['total_return']:.2f}%")
        print(f"  Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
        print(f"  最大Drawdown: {perf['max_drawdown']:.1f}%")
        
        # 輸出 CSV
        csv_file = 'leos_backtest_report.csv'
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV 報告已存: {csv_file}")
        
        # 輸出 JSON
        report = {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'params': {
                'RSI_Period': RSI_PERIOD,
                'RSI_Threshold': RSI_THRESHOLD,
                'Hold_Days': HOLD_DAYS,
                'Take_Profit': TAKE_PROFIT * 100,
                'Stop_Loss': STOP_LOSS * 100
            },
            'performance': perf,
            'trades': all_trades
        }
        with open('leos_backtest_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print("✅ JSON 報告已存: leos_backtest_report.json")
    else:
        print("⚠️  無交易記錄")
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    main()