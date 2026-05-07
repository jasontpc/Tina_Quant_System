import json, os

print('=== Tina Quant System Assessment ===')
print()

# 1. Streamlit app
app_size = os.path.getsize('streamlit_tw_stock.py')
print(f'streamlit_tw_stock.py: {app_size:,} bytes')

# Count lines
lines = open('streamlit_tw_stock.py', encoding='utf-8').readlines()
print(f'Total lines: {len(lines)}')

# 2. Leo paper trades
t = json.load(open('teams/leadtrades/leos/leos_trades.json', encoding='utf-8'))
print(f'Leo paper trades: {len(t["trades"])} positions')
print(f'Status: stats={t["stats"]}')

# 3. Team structure
teams = {}
for team_name in os.listdir('teams'):
    team_path = os.path.join('teams', team_name)
    if os.path.isdir(team_path):
        py_files = []
        for root, dirs, files in os.walk(team_path):
            py_files.extend([os.path.join(root, f) for f in files if f.endswith('.py')])
        teams[team_name] = len(py_files)

print()
print('=== Team Structure ===')
for team, count in teams.items():
    print(f'{team}: {count} scripts')

# 4. Key files
key_files = [
    'teams/nana/nana_v68.py',
    'teams/leo/scripts/leo_improved.py', 
    'teams/ray/scripts/ray_etf_dca.py',
    'streamlit_tw_stock.py',
]
print()
print('=== Key Files ===')
for f in key_files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        lnum = len(open(f, encoding='utf-8').readlines())
        print(f'{f}: {size:,} bytes, {lnum} lines')
    else:
        print(f'{f}: NOT FOUND')