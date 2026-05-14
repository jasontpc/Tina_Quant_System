# Taiwan ETF Backtest — Find optimal entry/exit params
import yfinance as yf
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np

def calc_rsi(closes, period=14):
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

ETFS = [
    ('0050', 'YuanDa Taiwan50'),
    ('0056', 'YuanDa HighDiv'),
    ('00713', 'YuanDa HiDivLowVol'),
    ('00646', 'Fubon S&P500'),
    ('00662', 'Fubon Nasdaq100'),
    ('00757', 'TongYi FANG+'),
    ('00927', 'TongYi Inno'),
    ('00878', 'Cathay SustHiDiv'),
    ('00929', 'FH TaiwanTechDiv'),
    ('00891', 'CTBC Semi'),
    ('00892', 'Fubon Taiwan5G+'),
]

def backtest_etf(sym, entry_rsi, exit_rsi, max_hold, stop_loss):
    try:
        df = yf.Ticker(f'{sym}.TW').history(period='5y', interval='1d', auto_adjust=True, timeout=5)
        if df is None or len(df) < 200: return None
        closes = df['Close']
        rsi_vals = calc_rsi(closes)
        
        trades = []
        in_pos = False
        entry_price = 0.0
        entry_idx = 0
        
        for i in range(50, len(closes)):
            rsi_cur = float(rsi_vals.iloc[i])
            price = float(closes.iloc[i])
            hold_days = i - entry_idx if in_pos else 0
            
            if not in_pos:
                if rsi_cur < entry_rsi:
                    in_pos = True
                    entry_price = price
                    entry_idx = i
            else:
                pnl = (price - entry_price) / entry_price * 100
                if (rsi_cur > exit_rsi or 
                    hold_days >= max_hold or 
                    pnl <= stop_loss):
                    trades.append({'pnl': pnl, 'days': hold_days})
                    in_pos = False
        
        if not trades: return None
        wins = [t for t in trades if t['pnl'] > 0]
        return {
            'symbol': sym,
            'entry_rsi': entry_rsi, 'exit_rsi': exit_rsi,
            'max_hold': max_hold, 'stop_loss': stop_loss,
            'total': len(trades),
            'wins': len(wins),
            'win_rate': len(wins) / len(trades) * 100,
            'avg_pnl': sum(t['pnl'] for t in trades) / len(trades),
        }
    except: return None

print("ETF Backtest — Testing Multiple RSI Parameter Sets")
print("=" * 60)

# Test param combinations
param_sets = [
    (55, 70, 30, -5),   # original-like
    (60, 75, 30, -5),   # looser entry
    (50, 70, 30, -5),   # stricter entry
    (55, 80, 30, -5),   # looser exit
    (60, 80, 30, -5),   # both loose
    (55, 70, 60, -5),   # longer hold
    (55, 75, 60, -5),   # mid
    (50, 65, 30, -5),   # original closer
    (60, 70, 60, -5),   # recommended below
]

results_by_params = []
total_etfs = len(ETFS)

for params in param_sets:
    entry_rsi, exit_rsi, max_hold, stop_loss = params
    all_results = []
    for sym, name in ETFS:
        r = backtest_etf(sym, *params)
        if r: all_results.append(r)
    
    if not all_results: continue
    total_trades = sum(r['total'] for r in all_results)
    total_wins = sum(r['wins'] for r in all_results)
    avg_pnl = sum(r['avg_pnl'] * r['total'] for r in all_results) / total_trades if total_trades > 0 else 0
    wr = total_wins / total_trades * 100 if total_trades > 0 else 0
    
    results_by_params.append({
        'entry_rsi': entry_rsi, 'exit_rsi': exit_rsi,
        'max_hold': max_hold, 'stop_loss': stop_loss,
        'etfs_tested': len(all_results),
        'total_trades': total_trades,
        'win_rate': round(wr, 1),
        'avg_pnl': round(avg_pnl, 2),
    })
    print(f"Entry<{entry_rsi} Exit>{exit_rsi} Hold<={max_hold}d SL{-stop_loss}% | "
          f"Trades:{total_trades} WR:{wr:.1f}% Avg:{avg_pnl:+.2f}%")

# Sort by win_rate desc
results_by_params.sort(key=lambda x: (-x['win_rate'], x['avg_pnl']), reverse=True)

print()
print("=" * 60)
print("TOP 3 PARAMETER SETS (by Win Rate):")
print("=" * 60)
for i, r in enumerate(results_by_params[:3], 1):
    print(f"{i}. Entry RSI<{r['entry_rsi']} Exit RSI>{r['exit_rsi']} Hold<={r['max_hold']}d SL{r['stop_loss']}%")
    print(f"   Win Rate: {r['win_rate']}% | Avg PnL: {r['avg_pnl']:+.2f}% | Trades: {r['total_trades']}")

# Best param
best = results_by_params[0]
print()
print(f"=== RECOMMENDED ETF TRINITY PARAMS ===")
print(f"  Entry RSI: < {best['entry_rsi']}  (stock was 30-35, ETF should be higher)")
print(f"  Exit RSI:  > {best['exit_rsi']}   (stock was 65, ETF needs more room)")
print(f"  Max Hold:  {best['max_hold']} days (ETF mean-reverts slower)")
print(f"  Stop Loss: {best['stop_loss']}%")

path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\etf_backtest_results.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump({
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'etfs': [s for s,_ in ETFS],
        'best_params': best,
        'all_results': results_by_params,
    }, f, ensure_ascii=False, indent=2)
print(f'\nSaved: {path}')