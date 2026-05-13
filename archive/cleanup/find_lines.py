"""Patch leos_daily_review.py remaining P1+P2 fixes — line-based."""
d = open('teams/leadtrades/leos/leos_daily_review.py', encoding='utf-8').read()
lines = d.split('\n')

# Find line numbers for key sections
for i, line in enumerate(lines):
    if '美股：用絕對金額停利/停損' in line:
        print(f'US exit at line {i+1}')
    if 'elif pnl_abs <= -US_STOP_LOSS_AMOUNT:' in line:
        print(f'US stop at line {i+1}')
    if 'elif rsi > 85 and pnl_pct > 3:' in line:
        print(f'US RSI at line {i+1}')
    if '台股：用百分比停利/停損' in line:
        print(f'TW exit at line {i+1}')
    if 'if cur >= target:' in line:
        print(f'TW take profit at line {i+1}')
    if '# 通用條件' in line:
        print(f'Generic at line {i+1}')
    if 'elif days_held > MAX_HOLD_DAYS:' in line:
        print(f'Max hold at line {i+1}')
    if "t['pnl'] = round(pnl_abs, 0)" in line:
        print(f'Pnl calc at line {i+1}')
