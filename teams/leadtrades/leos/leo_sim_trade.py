# -*- coding: utf-8 -*-
"""
Leo 模擬交易系統
功能：
  - 追蹤持倉（JSON）
  - 進場/停利/停損 邏輯
  - 每筆交易 P&L 記錄
  - 勝率統計
  - 結算報告
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import os

# === 參數 ===
RSI_PERIOD = 12
RSI_THRESHOLD = 40
HOLD_DAYS = 10
TAKE_PROFIT = 0.10
STOP_LOSS = 0.08

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

TRADE_FILE = 'leos_trades.json'

def load_trades():
    """載入交易記錄"""
    if os.path.exists(TRADE_FILE):
        with open(TRADE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'positions': [], 'closed_trades': [], 'stats': {}}

def save_trades(data):
    """儲存交易記錄"""
    with open(TRADE_FILE, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))

def calc_rsi(prices, period=12):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_ma(prices, period):
    return prices.rolling(window=period).mean()

def calc_momentum(prices, days=5):
    return prices.pct_change(days) * 100

def check_entry_conditions(ticker, df, idx):
    """檢查進場條件"""
    close = df['Close'].squeeze()
    rsi = calc_rsi(close, RSI_PERIOD)
    ma60 = calc_ma(close, 60)
    momentum = calc_momentum(close, 5)
    
    price = close.iloc[idx]
    current_rsi = rsi.iloc[idx]
    current_ma60 = ma60.iloc[idx]
    current_momentum = momentum.iloc[idx]
    
    if (current_rsi < RSI_THRESHOLD and 
        not pd.isna(current_ma60) and 
        price > current_ma60 and 
        current_momentum > 2):
        return True, price, current_rsi
    return False, price, current_rsi

def simulate_trade():
    """執行模擬交易"""
    print("=" * 60)
    print("Leo 科技股波段 v7.0 — 模擬交易系統")
    print("=" * 60)
    
    data = load_trades()
    positions = data.get('positions', [])
    closed_trades = data.get('closed_trades', [])
    
    print(f"\n📦 目前持倉: {len(positions)} 檔")
    for p in positions:
        print(f"   {p['ticker']} {p['name']} @ {p['entry_price']:.2f} (進場日: {p['entry_date']})")
    
    # 掃描進場機會
    print("\n🔍 掃描進場機會...")
    new_entries = []
    
    for ticker, name in STOCKS.items():
        # 檢查是否已持倉
        if any(p['ticker'] == ticker for p in positions):
            continue
        
        try:
            df = yf.download(f"{ticker}.TW", period='5d', progress=False)
            if df.empty or len(df) < 20:
                continue
            
            close = df['Close'].squeeze()
            rsi = calc_rsi(close, RSI_PERIOD)
            ma60 = calc_ma(close, 60)
            momentum = calc_momentum(close, 5)
            
            idx = -1
            price = close.iloc[idx]
            current_rsi = rsi.iloc[idx]
            current_ma60 = ma60.iloc[idx]
            current_momentum = momentum.iloc[idx]
            
            signal = ""
            score = 0
            
            # RSI 評分
            if current_rsi < 30:
                score += 30
                signal += "RSI超賣(+30) "
            elif current_rsi < 40:
                score += 20
                signal += "RSI偏低(+20) "
            elif current_rsi > 70:
                score -= 20
                signal += "RSI偏高(-20) "
            
            # MA60 多頭
            if not pd.isna(current_ma60) and price > current_ma60:
                score += 25
                signal += "MA60多頭(+25) "
            
            # 動量
            if current_momentum > 5:
                score += 20
                signal += "動量強(+20) "
            elif current_momentum > 2:
                score += 10
                signal += "動量正(+10) "
            
            # 進場條件
            if current_rsi < RSI_THRESHOLD and not pd.isna(current_ma60) and price > current_ma60 and current_momentum > 2:
                print(f"  ✅ {ticker} {name}: 價格={price:.2f}, RSI={current_rsi:.1f}, 評分={score}")
                print(f"     信號: {signal.strip()}")
                new_entries.append({
                    'ticker': ticker,
                    'name': name,
                    'entry_price': price,
                    'entry_date': datetime.now().strftime('%Y-%m-%d'),
                    'score': score,
                    'signal': signal.strip()
                })
        except Exception as e:
            print(f"  ⚠️ {ticker} {name}: {e}")
    
    # 檢查持倉停利/停損
    print("\n📊 檢查持倉狀態...")
    updated_positions = []
    
    for p in positions:
        ticker = p['ticker']
        try:
            df = yf.download(f"{ticker}.TW", period='5d', progress=False)
            if df.empty:
                updated_positions.append(p)
                continue
            
            close = df['Close'].squeeze()
            current_price = close.iloc[-1]
            entry_price = p['entry_price']
            
            pnl_pct = (current_price - entry_price) / entry_price * 100
            hold_days = (datetime.now() - datetime.strptime(p['entry_date'], '%Y-%m-%d')).days
            
            exit_reason = None
            if pnl_pct >= TAKE_PROFIT * 100:
                exit_reason = 'TP'
            elif pnl_pct <= -STOP_LOSS * 100:
                exit_reason = 'SL'
            elif hold_days >= HOLD_DAYS:
                exit_reason = 'HOLD'
            
            if exit_reason:
                print(f"  🔚 {ticker} {p['name']}: 平倉原因={exit_reason}, 報酬={pnl_pct:.2f}%")
                closed_trades.append({
                    'ticker': ticker,
                    'name': p['name'],
                    'entry_date': p['entry_date'],
                    'exit_date': datetime.now().strftime('%Y-%m-%d'),
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason
                })
            else:
                print(f"  📌 {ticker} {p['name']}: 持有中, 當前={current_price:.2f}, 報酬={pnl_pct:+.2f}%, 第{hold_days}天")
                p['current_price'] = current_price
                p['pnl_pct'] = pnl_pct
                p['hold_days'] = hold_days
                updated_positions.append(p)
        except Exception as e:
            print(f"  ⚠️ {ticker}: {e}")
            updated_positions.append(p)
    
    # 新增進場
    for ne in new_entries:
        print(f"\n  ➕ 進場: {ne['ticker']} {ne['name']} @ {ne['entry_price']:.2f}")
        updated_positions.append({
            'ticker': ne['ticker'],
            'name': ne['name'],
            'entry_price': ne['entry_price'],
            'entry_date': ne['entry_date'],
            'score': ne['score'],
            'signal': ne['signal']
        })
    
    # 統計
    if closed_trades:
        wins = [t for t in closed_trades if t['pnl_pct'] > 0]
        losses = [t for t in closed_trades if t['pnl_pct'] <= 0]
        wr = len(wins) / len(closed_trades) * 100
        avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
        total_pnl = sum(t['pnl_pct'] for t in closed_trades)
        
        print("\n" + "=" * 60)
        print("📈 結算報告")
        print("=" * 60)
        print(f"  總交易筆數: {len(closed_trades)}")
        print(f"  勝利: {len(wins)} / 失敗: {len(losses)}")
        print(f"  勝率: {wr:.1f}%")
        print(f"  平均獲利: {avg_win:.2f}%")
        print(f"  平均虧損: {avg_loss:.2f}%")
        print(f"  總報酬: {total_pnl:.2f}%")
        
        # 依股票統計
        print("\n▎各股票表現")
        print("-" * 40)
        for ticker, name in STOCKS.items():
            stock_trades = [t for t in closed_trades if t['ticker'] == ticker]
            if stock_trades:
                stock_wr = len([t for t in stock_trades if t['pnl_pct'] > 0]) / len(stock_trades) * 100
                stock_avg = np.mean([t['pnl_pct'] for t in stock_trades])
                print(f"  {ticker} {name}: {len(stock_trades)}筆, 勝率{stock_wr:.0f}%, 平均{stock_avg:+.2f}%")
        
        stats = {
            'total_trades': len(closed_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': wr,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl
        }
    else:
        stats = {}
    
    data = {
        'positions': updated_positions,
        'closed_trades': closed_trades,
        'stats': stats,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    save_trades(data)

    print(f"\n✅ 交易記錄已存: {TRADE_FILE}")
    print("=" * 60)

if __name__ == '__main__':
    simulate_trade()