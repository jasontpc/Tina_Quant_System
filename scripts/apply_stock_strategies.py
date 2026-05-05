import json
from pathlib import Path

# Load data
with open('data/optimized_stock_strategies.json', 'r', encoding='utf-8') as f:
    opt = json.load(f)

with open('data/team_watch_list.json', 'r', encoding='utf-8') as f:
    teams_data = json.load(f)

teams = teams_data['teams']

# Strategy params mapping
STRAT_PARAMS = {
    'MEAN_REVERSION': {
        'rsi_min': 30, 'rsi_max': 50, 'macd_positive': False, 'ma_bull': False,
        'sl_atr': 1.5, 'tp_atr': 3.0, 'strategy_type': 'MEAN_REVERSION'
    },
    'STRONG_UPTREND': {
        'rsi_min': 40, 'rsi_max': 70, 'macd_positive': True, 'ma_bull': True,
        'sl_atr': 2.0, 'tp_atr': 4.0, 'strategy_type': 'STRONG_UPTREND'
    },
    'MIXED': {
        'rsi_min': 30, 'rsi_max': 55, 'macd_positive': True, 'ma_bull': False,
        'sl_atr': 1.5, 'tp_atr': 3.0, 'strategy_type': 'MIXED'
    },
    'RANGE_BOUND': {
        'rsi_min': 25, 'rsi_max': 60, 'macd_positive': False, 'ma_bull': False,
        'sl_atr': 1.0, 'tp_atr': 2.0, 'strategy_type': 'RANGE_BOUND'
    }
}

# Map stocks to best strategy from optimizer
STOCK_STRATEGY = {}
for sym, info in opt.items():
    if info.get('best_strategy') and info.get('trades', 0) > 0:
        STOCK_STRATEGY[sym] = info['best_strategy']

print('Stock -> Strategy mapping (29 stocks):')
for sym, strat in sorted(STOCK_STRATEGY.items()):
    print('  %s: %s' % (sym, strat))

print()
print('Updating teams with individual stock params...')

# Apply individual stock params to each team
updated_count = 0
for team_name, team_data in teams.items():
    watch_list = team_data.get('watch_list', [])
    if isinstance(watch_list, list):
        new_watch_list = []
        for stock in watch_list:
            if isinstance(stock, str):
                sym = stock
            elif isinstance(stock, dict):
                sym = stock.get('symbol') or stock.get('stock') or stock
            else:
                sym = str(stock)
            
            if sym in STOCK_STRATEGY:
                strat = STOCK_STRATEGY[sym]
                params = STRAT_PARAMS.get(strat, STRAT_PARAMS['MIXED']).copy()
                new_stock = {
                    'symbol': sym,
                    'strategy': strat,
                    'params': params
                }
                new_watch_list.append(new_stock)
                print('  %s: %s -> %s' % (team_name, sym, strat))
                updated_count += 1
            else:
                new_watch_list.append(stock)
        
        team_data['watch_list'] = new_watch_list

teams_data['teams'] = teams
teams_data['updated'] = '2026-05-03'
teams_data['note'] = 'Individual stock strategies applied from optimized_stock_strategies.json'

with open('data/team_watch_list.json', 'w', encoding='utf-8') as f:
    json.dump(teams_data, f, indent=2, ensure_ascii=False)

print()
print('OK - Updated %d stocks with individual strategies' % updated_count)
print('File: data/team_watch_list.json')