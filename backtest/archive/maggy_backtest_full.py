# -*- coding: utf-8 -*-
"""Run Historical Backtest for Maggy US Stock Strategy"""
import sys, sqlite3, json, yfinance
from datetime import datetime, timedelta
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
SIM_DB = f'{DATA_DIR}\\maggy_sim_trades.db'
HIST_DB = f'{DATA_DIR}\\us_history.db'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def run_historical_backtest():
    """Run historical backtest on all US stocks"""
    print('╔══════════════════════════════════════════════════════╗')
    print('║     Maggy 歷史回測系統 — 交易驗證                  ║')
    print('╚══════════════════════════════════════════════════════╝')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    
    # Load history database
    conn = sqlite3.connect(HIST_DB)
    cur = conn.cursor()
    cur.execute("SELECT symbol, name FROM stock_summary ORDER BY symbol")
    stocks = cur.fetchall()
    conn.close()
    
    # Strategy params
    ENTRY_RSI = 35
    EXIT_RSI = 65
    MAX_HOLD = 20
    
    all_trades = []
    
    print(f'策略: RSI<{ENTRY_RSI} 進場, RSI>{EXIT_RSI} 出場, 最多{MAX_HOLD}天')
    print(f'回測股票: {len(stocks)}檔\n')
    
    for sym, name in stocks:
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='5y')
            
            if len(hist) < 200:
                continue
            
            closes = hist['Close'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            position = None
            trades = []
            
            for i in range(60, len(closes)):
                rsi = calc_rsi(closes[:i+1], 14)
                close = closes[i]
                date = dates[i]
                
                if position:
                    held = i - position['idx']
                    
                    # Exit conditions
                    exit_reason = None
                    if rsi > EXIT_RSI:
                        exit_reason = f'RSI>{EXIT_RSI}'
                    elif held >= MAX_HOLD:
                        exit_reason = f'max_hold={MAX_HOLD}'
                    
                    if exit_reason:
                        ret = (close - position['price']) / position['price'] * 100
                        trades.append({
                            'symbol': sym,
                            'name': name,
                            'entry_date': position['date'],
                            'entry_price': position['price'],
                            'exit_date': date,
                            'exit_price': close,
                            'holding_days': held,
                            'return_pct': ret,
                            'entry_rsi': position['entry_rsi'],
                            'exit_rsi': rsi,
                            'exit_reason': exit_reason,
                        })
                        position = None
                
                # Entry
                elif rsi < ENTRY_RSI:
                    position = {'date': date, 'price': close, 'idx': i, 'entry_rsi': rsi}
            
            all_trades.extend(trades)
            
        except Exception as e:
            pass
    
    # Analyze results
    print(f'=== 回測結果（{len(all_trades)}筆交易）===\n')
    
    if all_trades:
        wins = [t for t in all_trades if t['return_pct'] > 0]
        losses = [t for t in all_trades if t['return_pct'] <= 0]
        rets = [t['return_pct'] for t in all_trades]
        
        win_rate = len(wins) / len(all_trades) * 100
        avg_ret = sum(rets) / len(rets)
        total_ret = sum(rets)
        avg_hold = sum(t['holding_days'] for t in all_trades) / len(all_trades)
        
        print(f'總交易: {len(all_trades)}筆')
        print(f'勝率: {win_rate:.1f}%')
        print(f'平均報酬: {avg_ret:+.2f}%')
        print(f'總報酬: {total_ret:+.1f}%')
        print(f'平均持倉: {avg_hold:.1f}天')
        print(f'最佳交易: {max(rets):+.2f}%')
        print(f'最差交易: {min(rets):+.2f}%')
        
        # Top winners
        print('\n=== 最佳交易 TOP 10 ===')
        sorted_trades = sorted(all_trades, key=lambda x: x['return_pct'], reverse=True)
        print(f'{"股票":<8} {"進場日":<12} {"進場价":>8} {"離場日":<12} {"離場价":>8} {"報酬":>8} {"天數":>5}')
        print('-' * 65)
        for t in sorted_trades[:10]:
            print(f'{t["symbol"]:<8} {t["entry_date"][:10]:<12} {t["entry_price"]:>8.0f} {t["exit_date"][:10]:<12} {t["exit_price"]:>8.0f} {t["return_pct"]:>+7.2f}% {t["holding_days"]:>5}天')
        
        # By stock
        print('\n=== 股票表現排行 ===')
        stock_perf = {}
        for t in all_trades:
            sym = t['symbol']
            if sym not in stock_perf:
                stock_perf[sym] = {'trades': [], 'wins': 0, 'total': 0}
            stock_perf[sym]['trades'].append(t)
            if t['return_pct'] > 0:
                stock_perf[sym]['wins'] += 1
            stock_perf[sym]['total'] += t['return_pct']
        
        stock_summary = [(sym, d['wins'], len(d['trades']), d['total'], d['wins']/len(d['trades'])*100) for sym, d in stock_perf.items()]
        stock_summary.sort(key=lambda x: x[3], reverse=True)
        
        print(f'{"股票":<8} {"交易":>5} {"勝率":>7} {"總報酬":>9}')
        print('-' * 35)
        for sym, wins, total, ret, wr in stock_summary[:20]:
            print(f'{sym:<8} {total:>5} {wr:>6.1f}% {ret:>+8.1f}%')
        
        # Save to DB
        print('\n=== 儲存至資料庫 ===')
        sim_conn = sqlite3.connect(SIM_DB)
        sim_cur = sim_conn.cursor()
        
        for t in all_trades:
            sim_cur.execute('''INSERT INTO sim_trades 
                (symbol, entry_date, entry_price, exit_date, exit_price, holding_days, 
                return_pct, entry_rsi, exit_rsi, exit_reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'CLOSED')''',
                (t['symbol'], t['entry_date'], t['entry_price'], t['exit_date'],
                 t['exit_price'], t['holding_days'], t['return_pct'],
                 t['entry_rsi'], t['exit_rsi'], t['exit_reason']))
        
        sim_conn.commit()
        
        # Update summary
        for sym, data in stock_perf.items():
            wins = data['wins']
            total = len(data['trades'])
            ret = data['total']
            wr = wins / total * 100 if total > 0 else 0
            avg_hold = sum(t['holding_days'] for t in data['trades']) / len(data['trades'])
            best = max(t['return_pct'] for t in data['trades'])
            worst = min(t['return_pct'] for t in data['trades'])
            
            sim_cur.execute('''INSERT OR REPLACE INTO trade_summary
                (symbol, total_trades, winning_trades, losing_trades, win_rate,
                avg_return, total_return, avg_holding_days, best_trade, worst_trade, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (sym, total, wins, total-wins, wr, ret/total if total > 0 else 0,
                 ret, avg_hold, best, worst, datetime.now().isoformat()))
        
        sim_conn.commit()
        sim_conn.close()
        
        print(f'✅ 已儲存 {len(all_trades)} 筆交易至 {SIM_DB}')
        
        # Return for immediate trade signals
        return sorted_trades
    
    return []

def get_current_signals():
    """Get current trading signals"""
    print('\n\n=== 當前進場信號 ===\n')
    
    # Get live RSI
    stocks_to_check = ['XOM', 'JNJ', 'XLE', 'EOG', 'NFLX', 'COIN', 'INTC', 'TSLA']
    
    signals = []
    for sym in stocks_to_check:
        try:
            t = yfinance.Ticker(sym)
            hist = t.history(period='60d')
            if len(hist) < 30:
                continue
            closes = hist['Close'].tolist()
            rsi = calc_rsi(closes)
            price = closes[-1]
            
            if rsi < 35:
                signals.append({'symbol': sym, 'price': price, 'rsi': rsi, 'signal': 'BUY'})
            elif rsi > 65:
                signals.append({'symbol': sym, 'price': price, 'rsi': rsi, 'signal': 'SELL'})
            else:
                signals.append({'symbol': sym, 'price': price, 'rsi': rsi, 'signal': 'HOLD'})
        except:
            pass
    
    for s in signals:
        icon = '🟢' if s['signal'] == 'BUY' else ('🔴' if s['signal'] == 'SELL' else '⚪')
        print(f'{icon} {s["symbol"]}: ${s["price"]:.0f} RSI={s["rsi"]:.1f} → {s["signal"]}')
    
    return signals

if __name__ == '__main__':
    trades = run_historical_backtest()
    get_current_signals()