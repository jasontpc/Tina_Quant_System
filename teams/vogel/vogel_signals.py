# -*- coding: utf-8 -*-
"""
Vogel v2.0 - 台指期策略信號系統
第一個策略：Bollinger Band 突破 + RSI 共振
"""
import sys, sqlite3, os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
VOGEL_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\vogel'

def load_data():
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'vogel.db'))
    cur = conn.cursor()
    cur.execute('''
        SELECT date, close, bb_upper, bb_middle, bb_lower, rsi, atr, volume, open_interest
        FROM futures_daily WHERE futures_id="TX" ORDER BY date ASC
    ''')
    rows = cur.fetchall()
    conn.close()
    return [{
        'date': r[0], 'close': r[1], 'bb_upper': r[2], 'bb_middle': r[3],
        'bb_lower': r[4], 'rsi': r[5], 'atr': r[6], 'volume': r[7], 'oi': r[8]
    } for r in rows]

def backtest_signals(data):
    """測試策略表現"""
    trades = []
    position = None
    
    ENTRY_RSI_MAX = 45
    ENTRY_RSI_MIN = 25
    STOP_ATR = 2.0
    PROFIT_ATR = 3.0
    
    for i, d in enumerate(data):
        if position is None:
            # 進場條件：價格接觸 BB Lower 且 RSI < 45（超賣）
            if (d['bb_lower'] and d['close'] <= d['bb_lower'] and 
                d['rsi'] and d['rsi'] < ENTRY_RSI_MAX and d['rsi'] > ENTRY_RSI_MIN):
                position = {
                    'entry_date': d['date'],
                    'entry_price': d['close'],
                    'atr': d['atr'],
                    'stop_loss': d['close'] - STOP_ATR * d['atr'],
                    'take_profit': d['close'] + PROFIT_ATR * d['atr'],
                }
        
        else:
            entry_price = position['entry_price']
            held = (datetime.strptime(d['date'], '%Y-%m-%d') - 
                    datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            
            if d['close'] <= position['stop_loss']:
                if entry_price > 0:
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': d['date'],
                        'entry_price': entry_price,
                        'exit_price': position['stop_loss'],
                        'pnl_pct': (position['stop_loss'] - entry_price) / entry_price * 100,
                        'result': 'STOP_LOSS',
                        'held_days': held
                    })
                position = None
            
            elif d['close'] >= position['take_profit']:
                if entry_price > 0:
                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': d['date'],
                        'entry_price': entry_price,
                        'exit_price': position['take_profit'],
                        'pnl_pct': (position['take_profit'] - entry_price) / entry_price * 100,
                        'result': 'TAKE_PROFIT',
                        'held_days': held
                    })
                position = None
    
    return trades

def analyze_trades(trades):
    if not trades: return
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    win_rate = len(wins) / len(trades) * 100
    
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0
    
    print(f'\n=== Backtest Results ===')
    print(f'Total Trades: {len(trades)}')
    print(f'Win Rate: {win_rate:.1f}%')
    print(f'Wins: {len(wins)}, Losses: {len(losses)}')
    print(f'Avg Win: +{avg_win:.2f}%')
    print(f'Avg Loss: {avg_loss:.2f}%')
    if avg_loss != 0:
        print(f'Avg Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}')
    
    total_return = sum(t['pnl_pct'] for t in trades)
    print(f'Cumulative Return: {total_return:.1f}%')
    
    sl = [t for t in trades if t['result'] == 'STOP_LOSS']
    tp = [t for t in trades if t['result'] == 'TAKE_PROFIT']
    print(f'\nStop Loss: {len(sl)} ({len(sl)/len(trades)*100:.0f}%)')
    print(f'Take Profit: {len(tp)} ({len(tp)/len(trades)*100:.0f}%)')
    
    print(f'\n=== Trade Log (last 10) ===')
    print(f'{"Entry Date":<12} {"Exit Date":<12} {"Entry":>8} {"Exit":>8} {"P&L%":>7} {"Result":<12} {"Days":>4}')
    for t in trades[-10:]:
        pnl_str = f'{t["pnl_pct"]:+.2f}%'
        print(f'{t["entry_date"]:<12} {t["exit_date"]:<12} {t["entry_price"]:>8.0f} {t["exit_price"]:>8.0f} {pnl_str:>7} {t["result"]:<12} {t["held_days"]:>4}')

def current_signals(data, trades):
    if not data: return
    
    latest = data[-1]
    
    print(f'\n=== Current Market State ===')
    print(f'Date: {latest["date"]}')
    print(f'Close: {latest["close"]:,.0f}')
    print(f'RSI(14): {latest["rsi"]:.1f}' if latest["rsi"] else 'RSI: N/A')
    print(f'ATR(14): {latest["atr"]:.0f}' if latest["atr"] else 'ATR: N/A')
    print(f'BB Upper: {latest["bb_upper"]:,.0f}' if latest["bb_upper"] else 'BB_U: N/A')
    print(f'BB Middle: {latest["bb_middle"]:,.0f}' if latest["bb_middle"] else 'BB_M: N/A')
    print(f'BB Lower: {latest["bb_lower"]:,.0f}' if latest["bb_lower"] else 'BB_L: N/A')
    
    if latest['close'] < latest['bb_lower']:
        zone = 'BB_LOWER_ZONE (Potential Long Entry)'
    elif latest['close'] > latest['bb_upper']:
        zone = 'BB_UPPER_ZONE (Potential Short)'
    elif latest['close'] > latest['bb_middle']:
        zone = 'BULL_ZONE (Above middle)'
    else:
        zone = 'BEAR_ZONE (Below middle)'
    
    rsi_zone = 'N/A'
    if latest['rsi']:
        if latest['rsi'] > 70: rsi_zone = 'OVERBOUGHT'
        elif latest['rsi'] < 30: rsi_zone = 'OVERSOLD'
        else: rsi_zone = 'NEUTRAL'
    
    print(f'\nZone: {zone}')
    print(f'RSI Zone: {rsi_zone}')
    
    signal = 'NO_SIGNAL'
    if latest['rsi'] and latest['rsi'] < 45 and latest['close'] <= latest['bb_lower']:
        signal = 'LONG_SIGNAL - Price at BB Lower + RSI < 45'
    elif latest['rsi'] and latest['rsi'] > 70 and latest['close'] >= latest['bb_upper']:
        signal = 'SHORT_SIGNAL - Price at BB Upper + RSI > 70'
    elif latest['rsi'] and latest['rsi'] > 80:
        signal = 'WATCH - RSI Overbought, wait for pullback'
    elif latest['rsi'] and latest['rsi'] < 30:
        signal = 'WATCH - RSI Oversold, wait for bounce'
    
    print(f'Signal: {signal}')
    
    if latest['atr']:
        sl = latest['close'] - 2 * latest['atr']
        tp = latest['close'] + 3 * latest['atr']
        print(f'\nIf entry now:')
        print(f'  Entry: ~{latest["close"]:,.0f}')
        print(f'  Stop Loss: ~{sl:,.0f} (-{2*latest["atr"]:,.0f})')
        print(f'  Take Profit: ~{tp:,.0f} (+{3*latest["atr"]:,.0f})')
    
    recent_wins = [t for t in trades if t['result'] == 'TAKE_PROFIT']
    recent_losses = [t for t in trades if t['result'] == 'STOP_LOSS']
    print(f'\nRecent: {len(recent_wins)} TP / {len(recent_losses)} SL')

def main():
    print('=== Vogel v2.0 - Strategy Signal System ===\n')
    
    data = load_data()
    print(f'Loaded {len(data)} days of TX data')
    
    trades = backtest_signals(data)
    analyze_trades(trades)
    current_signals(data, trades)
    
    print('\n=== Vogel v2.0 Complete ===')

if __name__ == '__main__':
    main()