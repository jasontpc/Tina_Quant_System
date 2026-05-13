import re, os, sys
sys.stdout.reconfigure(encoding='utf-8')

base = 'teams/leadtrades/leos'
for fname in sorted(os.listdir(base)):
    if not fname.endswith('.py'): continue
    d = open(f'{base}/{fname}', encoding='utf-8').read()
    for kw in ['broker', 'alpaca', 'interactive', 'order', 'real', 'fund', 'capital', 'execute']:
        m = re.search(kw, d, re.IGNORECASE)
        if m:
            ctx = d[max(0,m.start()-80):m.start()+120]
            print(f'{fname} [{kw}]: {ctx[:200]}')
            print()