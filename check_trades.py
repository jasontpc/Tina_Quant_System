# -*- coding: utf-8 -*-
import json, sys
sys.stdout.reconfigure(encoding='utf-8')

# Check trade logs
logs = {
    'Nana Sim': 'teams/nana/nana_sim_trades.json',
    'Nana Auto': 'teams/nana/autonomous_trades.json',
    'Vogel v8': 'teams/vogel/vogel_trade_log_v8.json',
}

for name, path in logs.items():
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f'\n=== {name} ===')
        if isinstance(data, list):
            print(f'Trades: {len(data)}')
            if data:
                print(f'Latest: {data[-1].get("date", data[-1].get("entry_date", "?"))}')
        elif isinstance(data, dict):
            print(f'Keys: {list(data.keys())}')
            trades = data.get('trades', [])
            print(f'Trades: {len(trades)}')
            if trades:
                last = trades[-1]
                print(f'Last trade: {last.get("date") or last.get("entry_date")} {last.get("symbol") or last.get("direction")} ret={last.get("return_pct") or last.get("return")}')
            print(f'Stats: {data.get("stats")}')
    except Exception as e:
        print(f'{name}: error {e}')