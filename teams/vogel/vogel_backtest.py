# -*- coding: utf-8 -*-
"""
Vogel v3.0 - 多??台??交?系統
策略1: Bollinger Band 突破（已測試?策略2: RSI ?調?場
策略3: MACD 交?確?
策略4: 混?多?子確?"""
import sys, sqlite3, os, requests, json
from datetime import datetime, timedelta
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'
VOGEL_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\vogel'

TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
BASE = 'https://api.finmindtrade.com/api/v4/data'

# ========== STRATEGY PARAMETERS ==========
BB_PERIOD = 20
RSI_PERIOD = 14
ATR_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ========== RISK PARAMETERS ==========
STOP_ATR = 2.0
PROFIT_ATR = 3.0

def calc_ema(prices, period):
    """計? EMA """
    if len(prices) < period: return None
    ema = sum(prices[:period]) / period
    multiplier = 2 / (period + 1)
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calc_macd(closes, fast=12, slow=26, signal=9):
    """計? MACD """
    if len(closes) < slow: return None, None, None
    ema_fast = calc_ema(closes, fast)
    ema_slow = calc_ema(closes, slow)
    if ema_fast is None or ema_slow is None: return None, None, None
    macd_line = ema_fast - ema_slow
    # Signal line = EMA of MACD line
    macd_values = [ema_fast - calc_ema(closes[:slow], fast)]
    # Simplified: just return macd and signal as EMA of closes
    return macd_line, 0, 0

def load_all_data():
    """載入完整歷史??"""
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'vogel.db'))
    cur = conn.cursor()
    cur.execute('''
        SELECT date, open, high, low, close, volume, bb_upper, bb_middle, bb_lower, rsi, atr
        FROM futures_daily WHERE futures_id="TX" ORDER BY date ASC
    ''')
    rows = cur.fetchall()
    conn.close()
    
    data = []
    for r in rows:
        d = {
            'date': r[0], 'open': r[1], 'high': r[2], 'low': r[3],
            'close': r[4], 'volume': r[5],
            'bb_upper': r[6], 'bb_middle': r[7], 'bb_lower': r[8],
            'rsi': r[9], 'atr': r[10]
        }
        data.append(d)
    
    # Calculate MACD for each day
    closes = [d['close'] for d in data]
    for i in range(len(data)):
        if i >= MACD_SLOW:
            ema_fast = calc_ema(closes[:i+1], MACD_FAST)
            ema_slow = calc_ema(closes[:i+1], MACD_SLOW)
            if ema_fast and ema_slow:
                data[i]['macd'] = round(ema_fast - ema_slow, 2)
                
                # MACD signal line (EMA of MACD)
                macd_vals = [calc_ema(closes[max(0,j-26):j+1], MACD_FAST) - calc_ema(closes[max(0,j-26):j+1], MACD_SLOW) 
                            for j in range(max(0,i-8), i+1) if j >= MACD_SLOW]
                if macd_vals:
                    data[i]['macd_signal'] = round(sum(macd_vals)/len(macd_vals), 2)
                    data[i]['macd_hist'] = round(data[i]['macd'] - data[i]['macd_signal'], 2)
            else:
                data[i]['macd'] = data[i]['macd_signal'] = data[i]['macd_hist'] = None
        else:
            data[i]['macd'] = data[i]['macd_signal'] = data[i]['macd_hist'] = None
    
    return data

def get_rsi_zone(rsi):
    if rsi is None: return 'N/A'
    if rsi < 25: return 'DEEP_OVERSOLD'
    if rsi < 35: return 'OVERSOLD'
    if rsi < 45: return 'SOFT_OVERSOLD'
    if rsi < 55: return 'NEUTRAL_LOW'
    if rsi < 70: return 'NEUTRAL_HIGH'
    if rsi < 80: return 'OVERBOUGHT'
    return 'DEEP_OVERBOUGHT'

def run_strategy(name, data, entry_fn, params=None):
    """?用策略?測引?"""
    trades = []
    position = None
    params = params or {}
    
    for i, d in enumerate(data):
        if position is None:
            signal = entry_fn(d, i, data, params)
            if signal:
                atr = d.get('atr', 0) or 100
                position = {
                    'entry_date': d['date'],
                    'entry_price': d['close'],
                    'atr': atr,
                    'stop_loss': d['close'] - STOP_ATR * atr,
                    'take_profit': d['close'] + PROFIT_ATR * atr,
                    'strategy': name,
                    'signal_detail': signal,
                }
        else:
            held = (datetime.strptime(d['date'], '%Y-%m-%d') - 
                    datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            
            ep = position['entry_price']
            if ep <= 0: position = None; continue
            
            if d['close'] <= position['stop_loss']:
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': d['date'],
                    'entry_price': ep,
                    'exit_price': position['stop_loss'],
                    'pnl_pct': (position['stop_loss'] - ep) / ep * 100,
                    'result': 'STOP_LOSS',
                    'held_days': held,
                    'strategy': position['strategy'],
                    'signal_detail': position['signal_detail'],
                })
                position = None
            elif d['close'] >= position['take_profit']:
                trades.append({
                    'entry_date': position['entry_date'],
                    'exit_date': d['date'],
                    'entry_price': ep,
                    'exit_price': position['take_profit'],
                    'pnl_pct': (position['take_profit'] - ep) / ep * 100,
                    'result': 'TAKE_PROFIT',
                    'held_days': held,
                    'strategy': position['strategy'],
                    'signal_detail': position['signal_detail'],
                })
                position = None
    
    return trades

# ========== STRATEGY FUNCTIONS ==========

def strategy_bb_break(d, i, data, p):
    """策略1: BB突破?場（放寬?件?"""
    rsi = d.get('rsi')
    close = d['close']
    bb_l = d.get('bb_lower')
    bb_u = d.get('bb_upper')
    
    if bb_l is None or rsi is None: return None
    
    # Long: price at or below BB lower + RSI < 55
    if close <= bb_l and rsi < 55:
        return f'BB_Lower touch, RSI={rsi:.1f}'
    
    # Short: price at or above BB upper + RSI > 45 (for shorting)
    if close >= bb_u and rsi > 45:
        return f'BB_Upper touch, RSI={rsi:.1f}'
    
    return None

def strategy_rsi_reversal(d, i, data, p):
    """策略2: RSI ???場（更寬??進場點?"""
    rsi = d.get('rsi')
    close = d['close']
    bb_l = d.get('bb_lower')
    bb_m = d.get('bb_middle')
    
    if rsi is None or bb_l is None: return None
    
    # Long: RSI 從?????(cross above 30) or RSI < 35
    if i > 0:
        prev_rsi = data[i-1].get('rsi')
        if prev_rsi is not None:
            # RSI cross above 30 = potential bounce
            if prev_rsi < 30 and rsi >= 30:
                return f'RSI bounce from {prev_rsi:.1f} to {rsi:.1f}'
    
    # Long: RSI < 35 且價?在 BB 中???????
    if rsi < 35 and close >= bb_m * 0.98:
        return f'RSI={rsi:.1f} near BB middle support'
    
    return None

def strategy_macd_cross(d, i, data, p):
    """策略3: MACD 交?確?"""
    if i < MACD_SLOW + 5: return None
    
    macd = d.get('macd')
    macd_sig = d.get('macd_signal')
    macd_hist = d.get('macd_hist')
    rsi = d.get('rsi')
    
    if macd is None or macd_hist is None or rsi is None: return None
    
    # Previous bar MACD histogram
    prev_hist = data[i-1].get('macd_hist')
    if prev_hist is None: return None
    
    # Long: MACD histogram cross above 0 (bullish)
    if prev_hist <= 0 and macd_hist > 0 and rsi < 55:
        return f'MACD bullish cross, hist={macd_hist:.2f}'
    
    # Short: MACD histogram cross below 0 (bearish)
    if prev_hist >= 0 and macd_hist < 0 and rsi > 45:
        return f'MACD bearish cross, hist={macd_hist:.2f}'
    
    return None

def strategy_multi_factor(d, i, data, p):
    """策略4: 多?子確認??格?""
    rsi = d.get('rsi')
    close = d['close']
    bb_l = d.get('bb_lower')
    bb_m = d.get('bb_middle')
    bb_u = d.get('bb_upper')
    macd_hist = d.get('macd_hist')
    volume = d.get('volume', 0) or 0
    
    if rsi is None or bb_l is None or macd_hist is None: return None
    
    # Long: 3??確?
    long_factors = 0
    reasons = []
    
    if rsi < 45: long_factors += 1; reasons.append(f'RSI={rsi:.1f}')
    if close <= bb_l * 1.02: long_factors += 1; reasons.append('BB_lower')
    if macd_hist > 0: long_factors += 1; reasons.append('MACD_pos')
    
    # Require at least 2 factors
    if long_factors >= 2:
        return f'MultiFactor LONG x{long_factors}: ' + ','.join(reasons)
    
    # Short: 3??確?
    short_factors = 0
    reasons_s = []
    
    if rsi > 55: short_factors += 1; reasons_s.append(f'RSI={rsi:.1f}')
    if close >= bb_u * 0.98: short_factors += 1; reasons_s.append('BB_upper')
    if macd_hist < 0: short_factors += 1; reasons_s.append('MACD_neg')
    
    if short_factors >= 2:
        return f'MultiFactor SHORT x{short_factors}: ' + ','.join(reasons_s)
    
    return None

def analyze_results(strategy_name, trades, params=None):
    """????策略結?"""
    if not trades:
        print(f'\n[{strategy_name}] No trades generated')
        return
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    wr = len(wins) / len(trades) * 100
    
    avg_win = sum(t['pnl_pct'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in losses) / len(losses) if losses else 0
    
    total = sum(t['pnl_pct'] for t in trades)
    sl_count = len([t for t in trades if t['result'] == 'STOP_LOSS'])
    tp_count = len([t for t in trades if t['result'] == 'TAKE_PROFIT'])
    
    avg_held = sum(t['held_days'] for t in trades) / len(trades)
    
    print(f'\n[{strategy_name}]')
    print(f'  Trades: {len(trades)} | WR: {wr:.1f}% | Avg Held: {avg_held:.1f}d')
    print(f'  Wins: +{avg_win:.2f}% ({len(wins)}) | Losses: {avg_loss:.2f}% ({len(losses)})')
    if avg_loss != 0:
        print(f'  R:R = {abs(avg_win/avg_loss):.2f}x | Total: {total:+.1f}%')
    print(f'  SL: {sl_count} | TP: {tp_count}')
    
    return {
        'strategy': strategy_name,
        'trades': len(trades),
        'win_rate': wr,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total': total,
        'avg_held': avg_held,
    }

def run_full_backtest():
    """??完整?測"""
    print('=== Vogel v3.0 - Multi-Strategy Backtest ===\n')
    
    data = load_all_data()
    print(f'Loaded {len(data)} days of TX data')
    print(f'Range: {data[0]["date"]} to {data[-1]["date"]}')
    
    results = {}
    
    strategies = [
        ('BB_Break', strategy_bb_break),
        ('RSI_Reversal', strategy_rsi_reversal),
        ('MACD_Cross', strategy_macd_cross),
        ('Multi_Factor', strategy_multi_factor),
    ]
    
    for name, fn in strategies:
        trades = run_strategy(name, data, fn)
        result = analyze_results(name, trades)
        if result:
            results[name] = result
    
    # Combined strategy
    print('\n' + '='*50)
    all_trades = []
    for name, fn in strategies:
        trades = run_strategy(name, data, fn)
        all_trades.extend(trades)
    
    if all_trades:
        # Remove duplicates (same date/same direction)
        seen = {}
        unique = []
        for t in all_trades:
            key = (t['entry_date'], round(t['entry_price']))
            if key not in seen:
                seen[key] = True
                unique.append(t)
        
        result = analyze_results('COMBINED', unique)
        if result:
            results['COMBINED'] = result
    
    # Show best strategy
    print('\n=== Summary ===')
    if results:
        best = max(results.items(), key=lambda x: x[1]['win_rate'] * x[1]['total'] / 100)
        print(f'Best Strategy: {best[0]}')
        print(f'  Trades: {best[1]["trades"]}, WR: {best[1]["win_rate"]:.1f}%, Total: {best[1]["total"]:+.1f}%')
    
    # Show recent trades
    print('\n=== Recent 15 Trades (Combined) ===')
    if all_trades:
        for t in sorted(all_trades, key=lambda x: x['entry_date'], reverse=True)[:15]:
            pnl_str = f'{t["pnl_pct"]:+.2f}%'
            print(f'{t["entry_date"]} {t["strategy"][:12]:<12} {pnl_str:>8} {t["result"][:10]:<10} {t["signal_detail"][:40]}')
    
    return results, all_trades, data

def update_current_status(data, trades):
    """?新?????""
    if not data: return
    
    latest = data[-1]
    
    print('\n=== Current Market State ===')
    print(f'Date: {latest["date"]} | Close: {latest["close"]:,.0f}')
    print(f'RSI(14): {latest["rsi"]:.1f} ({get_rsi_zone(latest["rsi"])})')
    print(f'MACD: {latest.get("macd",0):.2f} | Signal: {latest.get("macd_signal",0):.2f} | Hist: {latest.get("macd_hist",0):.2f}')
    print(f'ATR(14): {latest["atr"]:,.0f}' if latest.get('atr') else 'ATR: N/A')
    print(f'BB: {latest["bb_upper"]:,.0f} / {latest["bb_middle"]:,.0f} / {latest["bb_lower"]:,.0f}')
    
    # Signal check for each strategy
    print('\n=== Signal Check ===')
    
    # BB Break
    if latest['close'] <= latest['bb_lower'] and latest['rsi'] < 55:
        print(f'  BB_Break: LONG SIGNAL - at BB lower, RSI={latest["rsi"]:.1f}')
    elif latest['close'] >= latest['bb_upper'] and latest['rsi'] > 45:
        print(f'  BB_Break: SHORT SIGNAL - at BB upper, RSI={latest["rsi"]:.1f}')
    else:
        print(f'  BB_Break: No signal')
    
    # RSI Reversal
    if i := len(data) > 1:
        prev_rsi = data[-2].get('rsi')
        if prev_rsi and prev_rsi < 30 and latest['rsi'] >= 30:
            print(f'  RSI_Reversal: LONG SIGNAL - RSI bounced from {prev_rsi:.1f}')
        else:
            print(f'  RSI_Reversal: No signal')
    
    # MACD Cross
    if latest.get('macd_hist') and data[-2].get('macd_hist'):
        if data[-2]['macd_hist'] <= 0 and latest['macd_hist'] > 0:
            print(f'  MACD_Cross: LONG - bullish cross')
        elif data[-2]['macd_hist'] >= 0 and latest['macd_hist'] < 0:
            print(f'  MACD_Cross: SHORT - bearish cross')
        else:
            print(f'  MACD_Cross: No signal')
    
    # Multi Factor
    long_f = 0
    if latest['rsi'] and latest['rsi'] < 45: long_f += 1
    if latest['close'] <= latest['bb_lower'] * 1.02: long_f += 1
    if latest.get('macd_hist', 0) > 0: long_f += 1
    if long_f >= 2:
        print(f'  Multi_Factor: LONG x{long_f}')
    else:
        print(f'  Multi_Factor: No signal')
    
    # Position sizing
    if latest.get('atr'):
        sl = latest['close'] - 2 * latest['atr']
        tp = latest['close'] + 3 * latest['atr']
        print(f'\nIf enter now (estimated):')
        print(f'  Entry: {latest["close"]:,.0f} | SL: {sl:,.0f} | TP: {tp:,.0f}')
        print(f'  Risk: {2*latest["atr"]:,.0f} pts ({2*latest["atr"]/latest["close"]*100:.2f}%)')

def save_trade_log(trades):
    """保?交???"""
    log_path = os.path.join(VOGEL_DIR, 'trade_log.json')
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)
    print(f'\nTrade log saved: {log_path} ({len(trades)} trades)')

def main():
    results, trades, data = run_full_backtest()
    update_current_status(data, trades)
    if trades:
        save_trade_log(trades)
    print('\n=== Vogel v3.0 Done ===')

if __name__ == '__main__':
    main()
