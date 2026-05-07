"""Patch leos_daily_review.py with P1+P2 fixes:
P1-2: Trailing stop when profit >= 5%
P1-3: Force reduce at day 10 if pnl < 5%
P1-4: US take profit = min($300, 15% target return)
P2-3: Fee estimation in PnL
"""
d = open('teams/leadtrades/leos/leos_daily_review.py', encoding='utf-8').read()
lines = d.split('\n')

# 1. Add new constants at top (after existing constants)
old_top = '''# 美股絕對停利/停損（每口$2000）
US_TAKE_PROFIT_AMOUNT = 300
US_STOP_LOSS_AMOUNT = 200'''

new_top = '''# 美股絕對停利/停損（每口$2000）
# P1-4: US停利改為「目標15% OR $300，取小者」（取小=更容易觸發）
US_TAKE_PROFIT_AMOUNT = 300
US_STOP_LOSS_AMOUNT = 200

# P1-2: 移動停利（進場+5%後停損→成本價）
TRAILING_PROFIT_PCT = 5.0

# P1-3: 持有10天未達目標強制減倉
FORCE_REDUCE_DAYS = 10
FORCE_REDUCE_PCT = 0.5

# P2-3: 手續費估算（0.4%）
FEE_RATE = 0.004'''

if old_top in d:
    d = d.replace(old_top, new_top, 1)
    print('Added P1/P2 constants')
else:
    print('ERROR: constants not found')

# 2. Find US exit logic and fix it (P1-4)
old_us = '''        # 美股：用絕對金額停利/停損
            if pnl_abs >= US_TAKE_PROFIT_AMOUNT:
                reason = 'take_profit_us'
            elif pnl_abs <= -US_STOP_LOSS_AMOUNT:
                reason = 'stop_loss_us'
            elif rsi > 85 and pnl_pct > 3:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}' '''

new_us = '''        # P1-4: US停利改為「目標15% OR $300，取小者」
            # $300對低價股太容易，對高價股太難 → 改用min($300, 15%return)
            target_15pct_abs = (entry * 0.15) * shares
            us_take_profit_threshold = min(US_TAKE_PROFIT_AMOUNT, target_15pct_abs)
            if pnl_abs >= us_take_profit_threshold:
                reason = 'take_profit_us_15pct_or_300'
            elif pnl_abs <= -US_STOP_LOSS_AMOUNT:
                reason = 'stop_loss_us'
            elif rsi > 85 and pnl_pct > 3:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}'

            # P1-2: 移動停利 — 進場+5%後停損→成本價
            if pnl_pct >= TRAILING_PROFIT_PCT and not t.get('trailing_stop_active'):
                t['trailing_stop'] = entry  # 成本價
                t['trailing_stop_active'] = True
                print(f'    [TRAILING STOP] {sym}: stop -> ${entry} (cost basis)')
            elif t.get('trailing_stop_active'):
                ts = t.get('trailing_stop', stop)
                if cur <= ts:
                    reason = 'trailing_stop_triggered' '''

if old_us in d:
    d = d.replace(old_us, new_us, 1)
    print('Fixed US exit logic (P1-4, P1-2 trailing)')
else:
    print('ERROR: US exit logic not found')

# 3. Find TW exit logic and add trailing stop support
old_tw = '''        # 台股：用百分比停利/停損
            if cur >= target:
                reason = 'take_profit_target'
            elif cur <= stop:
                reason = 'stop_loss'
            elif rsi > OVERBOUGHT_EXIT_RSI and pnl_pct > OVERBOUGHT_PROFIT_LOCK_PCT:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}' '''

new_tw = '''        # 台股：用百分比停利/停損 + P1-2移動停利
            if cur >= target:
                reason = 'take_profit_target'
            elif cur <= stop:
                reason = 'stop_loss'
            # P1-2: 移動停利 — 進場+5%後停損→成本價
            elif pnl_pct >= TRAILING_PROFIT_PCT and not t.get('trailing_stop_active'):
                t['trailing_stop'] = entry
                t['trailing_stop_active'] = True
                print(f'    [TRAILING STOP] {sym}: stop -> ${entry} (cost basis)')
            elif t.get('trailing_stop_active'):
                ts = t.get('trailing_stop', stop)
                if cur <= ts:
                    reason = 'trailing_stop_triggered'
            elif rsi > OVERBOUGHT_EXIT_RSI and pnl_pct > OVERBOUGHT_PROFIT_LOCK_PCT:
                reason = f'overbought_lock_profit_RSI{int(rsi)}_pnl{pnl_pct:.1f}' '''

if old_tw in d:
    d = d.replace(old_tw, new_tw, 1)
    print('Fixed TW exit logic (P1-2 trailing)')
else:
    print('ERROR: TW exit logic not found')

# 4. Add force-reduce at day 10 for TW positions (add before the generic reason check)
# This needs to be inserted after trailing stop check but before take_profit/stop_loss
# Find the section with "通用條件" and add force_reduce check before it
old_generic = '''        # 通用條件
        if pnl_pct > BIG_GAIN_TAKE_PROFIT_PCT:
            reason = f'big_gain_take_profit_{pnl_pct:.1f}'
        elif days_held > MAX_HOLD_DAYS:
            reason = f'max_hold_days_{days_held:.0f}' '''

new_generic = '''        # P1-3: 持有10天未達目標→強制減倉50%
        if reason is None and days_held >= FORCE_REDUCE_DAYS and pnl_pct < 5 and not t.get('reduced_once'):
            new_shares = int(shares * FORCE_REDUCE_PCT)
            if new_shares >= 1:
                t['shares'] = new_shares
                t['amount'] = round(new_shares * cur, 0)
                t['reduced_once'] = True
                t['exit_reason'] = f'force_reduce_day10_pnl{pnl_pct:.1f}pct'
                if t.get('trailing_stop_active'):
                    t['trailing_stop'] = max(entry, t.get('trailing_stop', entry))
                print(f'    [REDUCED] {sym}: {shares}->{new_shares} shares (day10, pnl={pnl_pct:+.1f}%)')
                reason = 'force_reduce'
                exits_to_run.append((t, 'force_reduce', cur, pnl_pct, pnl_abs))

        # 通用條件
        if reason is None and pnl_pct > BIG_GAIN_TAKE_PROFIT_PCT:
            reason = f'big_gain_take_profit_{pnl_pct:.1f}'
        elif reason is None and days_held > MAX_HOLD_DAYS:
            reason = f'max_hold_days_{days_held:.0f}' '''

if old_generic in d:
    d = d.replace(old_generic, new_generic, 1)
    print('Added force-reduce at day 10 (P1-3)')
else:
    print('ERROR: generic conditions not found')

# 5. Fix PnL calculation to include fee (P2-3)
# In the "Execute exits" section, add fee to pnl
old_exit_calc = '''        t['pnl'] = round(pnl_abs, 0)
        t['pnl_pct'] = round(pnl_pct, 2)'''

new_exit_calc = '''        # P2-3: 手續費估算（0.4%，進場+出場各一次）
        fee = round(entry * shares * FEE_RATE + cur * shares * FEE_RATE, 0)
        net_pnl = pnl_abs - fee
        t['pnl'] = round(net_pnl, 0)
        t['pnl_pct'] = round((cur - entry) / entry * 100 - FEE_RATE * 200, 2)  # 扣除來回0.8%費用
        t['fee'] = fee'''

if old_exit_calc in d:
    d = d.replace(old_exit_calc, new_exit_calc, 1)
    print('Added fee calculation (P2-3)')
else:
    print('ERROR: exit calc not found')

open('teams/leadtrades/leos/leos_daily_review.py', 'w', encoding='utf-8').write(d)

import subprocess
r = subprocess.run(['python', '-m', 'py_compile', 'teams/leadtrades/leos/leos_daily_review.py'],
                   capture_output=True, text=True,
                   cwd='C:\\Users\\USER\\.openclaw\\workspace\\Tina_Quant_System')
print(f'Syntax: {r.returncode}')
if r.returncode != 0:
    print('Error:', r.stderr[:300])
else:
    print('All patches applied successfully')