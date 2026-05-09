# -*- coding: utf-8 -*-
"""Maggy US Stock Backtest System - v1.0"""
import sys, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

# Backtest engine for US stocks
# Strategy: RSI Mean Reversion + Trend Following

def backtest_rsi_strategy(symbol, prices, rsi_values, trades, start_date, end_date, initial_capital=100000):
    """
    RSI Mean Reversion Strategy:
    - LONG when RSI < 30 (oversold)
    - EXIT when RSI > 55 or after 20 days
    - ATR stop loss
    """
    capital = initial_capital
    position = None
    results = []
    
    for i in range(len(prices)):
        date = prices[i]['date']
        close = prices[i]['close']
        rsi = rsi_values[i]
        atr = prices[i].get('atr', close * 0.02)
        
        if position:
            # Check exit
            held_days = (datetime.strptime(date, '%Y-%m-%d') - datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            
            if rsi > 55 or held_days >= 20:
                # Exit
                pnl = (close - position['entry_price']) * position['size']
                capital += pnl
                ret = (close - position['entry_price']) / position['entry_price'] * 100
                results.append({
                    'symbol': symbol,
                    'entry_date': position['entry_date'],
                    'exit_date': date,
                    'direction': 'LONG',
                    'entry_price': position['entry_price'],
                    'exit_price': close,
                    'return_pct': ret,
                    'pnl': pnl,
                    'hold_days': held_days,
                    'rsi_entry': position['rsi_entry'],
                    'rsi_exit': rsi,
                })
                position = None
        
        elif rsi < 30 and capital >= close * 100:
            # Entry
            size = capital * 0.1 / close  # 10% of capital
            position = {
                'entry_date': date,
                'entry_price': close,
                'size': size,
                'stop_loss': close - 1.5 * atr,
                'rsi_entry': rsi,
            }
    
    return results, capital

def backtest_ma_strategy(symbol, prices, sma_values, trades, initial_capital=100000):
    """
    MA Crossover Strategy:
    - LONG when price > SMA(20)
    - EXIT when price < SMA(20)
    """
    capital = initial_capital
    position = None
    results = []
    
    for i in range(len(prices)):
        if i < 20 or sma_values[i] is None:
            continue
            
        date = prices[i]['date']
        close = prices[i]['close']
        sma20 = sma_values[i]
        
        if position:
            # Check exit (price below SMA20)
            if close < sma20:
                pnl = (close - position['entry_price']) * position['size']
                capital += pnl
                ret = (close - position['entry_price']) / position['entry_price'] * 100
                held_days = (datetime.strptime(date, '%Y-%m-%d') - datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
                results.append({
                    'symbol': symbol,
                    'entry_date': position['entry_date'],
                    'exit_date': date,
                    'direction': 'LONG',
                    'entry_price': position['entry_price'],
                    'exit_price': close,
                    'return_pct': ret,
                    'pnl': pnl,
                    'hold_days': held_days,
                    'strategy': 'MA_Cross'
                })
                position = None
        elif close > sma20:
            size = capital * 0.1 / close
            position = {
                'entry_date': date,
                'entry_price': close,
                'size': size,
            }
    
    return results, capital

def calculate_stats(results):
    if not results:
        return {'trades': 0, 'win_rate': 0, 'avg_return': 0, 'total_return': 0}
    
    wins = [r for r in results if r['return_pct'] > 0]
    losses = [r for r in results if r['return_pct'] <= 0]
    
    return {
        'trades': len(results),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(results) * 100 if results else 0,
        'avg_return': sum(r['return_pct'] for r in results) / len(results),
        'avg_win': sum(r['return_pct'] for r in wins) / len(wins) if wins else 0,
        'avg_loss': sum(r['return_pct'] for r in losses) / len(losses) if losses else 0,
        'total_return': sum(r['return_pct'] for r in results),
        'max_gain': max(r['return_pct'] for r in results) if results else 0,
        'max_loss': min(r['return_pct'] for r in results) if results else 0,
    }

def main():
    print('=== Maggy 美股波段回測系統 v1.0 ===\n')
    
    # Example backtest for SPY
    # In real implementation, load from maggy.db
    print('Strategy 1: RSI Mean Reversion')
    print('  - LONG when RSI < 30')
    print('  - EXIT when RSI > 55 or 20 days')
    print()
    print('Strategy 2: MA Crossover')
    print('  - LONG when price > SMA(20)')
    print('  - EXIT when price < SMA(20)')
    print()
    print('等待資料庫建立完成後執行回測...')

if __name__ == '__main__':
    main()