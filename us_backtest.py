# -*- coding: utf-8 -*-
"""美股模擬交易回測系統"""
import sys, sqlite3, yfinance
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
SIM_DB = f'{DATA_DIR}\\us_sim_trades.db'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def backtest_strategy(symbol, entry_rsi=35, exit_rsi=60, max_hold=20):
    """RSI均值回歸策略回測"""
    try:
        t = yfinance.Ticker(symbol)
        hist = t.history(period='3y')
        if len(hist) < 500:
            return None
        
        closes = hist['Close'].tolist()
        dates = hist.index.strftime('%Y-%m-%d').tolist()
        
        trades = []
        in_position = False
        entry_price = 0
        entry_date = ''
        entry_rsi_val = 0
        hold_days = 0
        
        for i in range(50, len(closes)):
            rsi = calc_rsi(closes[:i+1])
            close = closes[i]
            date = dates[i]
            
            if not in_position:
                if rsi < entry_rsi:
                    in_position = True
                    entry_price = close
                    entry_date = date
                    entry_rsi_val = rsi
                    hold_days = 0
            else:
                hold_days += 1
                # Exit conditions
                exit_reason = ''
                should_exit = False
                
                if rsi > exit_rsi:
                    should_exit = True
                    exit_reason = 'RSI_EXIT'
                elif hold_days >= max_hold:
                    should_exit = True
                    exit_reason = 'MAX_HOLD'
                elif close < entry_price * 0.92:
                    should_exit = True
                    exit_reason = 'STOP_LOSS'
                
                if should_exit:
                    ret_pct = (close - entry_price) / entry_price * 100
                    trades.append({
                        'symbol': symbol,
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'exit_date': date,
                        'exit_price': close,
                        'holding_days': hold_days,
                        'return_pct': ret_pct,
                        'entry_rsi': entry_rsi_val,
                        'exit_rsi': rsi,
                        'exit_reason': exit_reason
                    })
                    in_position = False
        
        return trades
        
    except Exception as e:
        return None

def run_backtest():
    """運行完整回測"""
    print('╔══════════════════════════════════════════════════════════════╗')
    print('║     美股模擬交易回測系統                            ║')
    print('╚══════════════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    conn = sqlite3.connect(SIM_DB)
    cur = conn.cursor()
    
    # Stock pool
    STOCKS = [
        'HON', 'INFY', 'IBM', 'NOW', 'SNOW', 'ASML', 'NET', 'AMAT',
        'PLTR', 'DT', 'AI', 'PATH', 'CRWD', 'COIN', 'UPST', 'KLAC',
        'AVGO', 'ORCL', 'TXN', 'QCOM', 'TEAM', 'DOCU', 'OKTA',
        'SCHW', 'COF', 'SLB', 'EOG', 'CAT', 'DE', 'BA', 'HON',
        'UNH', 'ABBV', 'MRK', 'LLY', 'TMO', 'DHR', 'AMGN',
        'NFLX', 'CRM', 'PYPL', 'UBER', 'LYFT', 'SPOT',
        'AMD', 'INTC', 'NVDA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA',
    ]
    
    # Parameters to test
    params_list = [
        {'entry': 30, 'exit': 55, 'hold': 15, 'name': 'RSI_Rev_Low'},
        {'entry': 35, 'exit': 60, 'hold': 20, 'name': 'RSI_Rev_Mid'},
        {'entry': 40, 'exit': 65, 'hold': 25, 'name': 'RSI_Rev_High'},
        {'entry': 25, 'exit': 50, 'hold': 10, 'name': 'RSI_Aggressive'},
    ]
    
    results = {}
    
    for params in params_list:
        name = params['name']
        print(f'=== {name} ===')
        
        all_trades = []
        stock_results = {}
        
        for sym in STOCKS:
            trades = backtest_strategy(sym, params['entry'], params['exit'], params['hold'])
            if trades:
                stock_results[sym] = trades
                all_trades.extend(trades)
        
        if all_trades:
            wins = [t for t in all_trades if t['return_pct'] > 0]
            losses = [t for t in all_trades if t['return_pct'] <= 0]
            win_rate = len(wins) / len(all_trades) * 100 if all_trades else 0
            avg_ret = sum(t['return_pct'] for t in all_trades) / len(all_trades)
            total_ret = sum(t['return_pct'] for t in all_trades)
            avg_hold = sum(t['holding_days'] for t in all_trades) / len(all_trades)
            
            results[name] = {
                'params': params,
                'total_trades': len(all_trades),
                'win_rate': win_rate,
                'avg_return': avg_ret,
                'total_return': total_ret,
                'avg_holding_days': avg_hold,
                'best_trade': max(t['return_pct'] for t in all_trades),
                'worst_trade': min(t['return_pct'] for t in all_trades),
                'stocks': len(stock_results)
            }
            
            print(f'  交易: {len(all_trades)}筆, 勝率: {win_rate:.1f}%, 均報酬: {avg_ret:+.2f}%, 持倉: {avg_hold:.1f}天')
            
            # Save trades to DB
            for t in all_trades:
                cur.execute('INSERT INTO sim_trades (symbol, entry_date, entry_price, exit_date, exit_price, holding_days, return_pct, entry_rsi, exit_rsi, exit_reason, strategy, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "CLOSED")',
                    (t['symbol'], t['entry_date'], t['entry_price'], t['exit_date'], t['exit_price'], t['holding_days'], t['return_pct'], t['entry_rsi'], t['exit_rsi'], t['exit_reason'], name))
            conn.commit()
    
    # Summary
    print('\n\n=== 回測結果總結 ===\n')
    
    print('策略      交易數  勝率    均報酬   持倉  股票數')
    print('-' * 55)
    
    best_strategy = None
    best_score = 0
    
    for name, data in sorted(results.items(), key=lambda x: x[1]['win_rate'], reverse=True):
        score = data['win_rate'] * 0.4 + data['avg_return'] * 0.3 + (100 / (data['avg_holding_days'] + 1)) * 0.3
        if score > best_score:
            best_score = score
            best_strategy = name
        
        print(f"{name:<12} {data['total_trades']:>5}  {data['win_rate']:>5.1f}% {data['avg_return']:>+8.2f}% {data['avg_holding_days']:>6.1f} {data['stocks']:>6}")
    
    print(f'\n🏆 最佳策略: {best_strategy}')
    
    # Save best strategy
    with open(f'{DATA_DIR}\\us_backtest_best.json', 'w', encoding='utf-8') as f:
        json.dump({'best_strategy': best_strategy, 'results': results}, f, ensure_ascii=False, indent=2)
    
    conn.close()

def main():
    import json
    run_backtest()

if __name__ == '__main__':
    main()