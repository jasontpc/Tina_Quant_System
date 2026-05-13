import os

for fname in sorted(os.listdir('teams/leadtrades/leos')):
    if not fname.endswith('.py'): continue
    d = open(f'teams/leadtrades/leos/{fname}', encoding='utf-8').read()
    for line in d.split('\n'):
        if 'push' in line.lower() and len(line.strip()) < 200:
            print(f'{fname}: {line.strip()[:120]}')