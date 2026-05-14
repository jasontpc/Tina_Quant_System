import json
with open(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\leos_backtest_report.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print('Leo Report:')
p = data['performance']
print(f'  total_trades: {p["total_trades"]}')
print(f'  wins: {p["wins"]}')
print(f'  losses: {p["losses"]}')
print(f'  win_rate: {p["win_rate"]*100:.1f}%')
print(f'  avg_return: {p["avg_return"]:.2f}%')

# Count unique tickers in Leo trades
tickers = set(t['ticker'] for t in data['trades'])
print(f'  Leo tickers: {len(tickers)} unique')
print(f'  tickers: {sorted(tickers)}')