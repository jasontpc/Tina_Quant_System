d = open('teams/leadtrades/leos/leos_daily_review.py', encoding='utf-8').read()
idx = d.find("t['pnl'] = round(pnl_abs, 0)")
print(repr(d[idx-100:idx+200]))
