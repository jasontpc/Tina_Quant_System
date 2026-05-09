import os, re, json

base = 'C:/Users/USER/.openclaw/workspace/Tina_Quant_System'
os.chdir(base)

# Phase 1: Find all Python files and their imports/DBs
py_files = {}
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('__pycache__','.git','node_modules','archive','archive_json','streamlit_cloud_backup_20260509')]
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                # Find imports
                imports = re.findall(r'^import\s+(\w+)', content, re.MULTILINE)
                froms = re.findall(r'^from\s+(\w+)', content, re.MULTILINE)
                all_imports = imports + froms
                # Find database usages
                dbs = re.findall(r'(data/[a-zA-Z_]+\.db|stores/[a-zA-Z_/]+\.db)', content)
                py_files[path] = {
                    'imports': all_imports,
                    'dbs': list(set(dbs)),
                    'size': len(content)
                }
            except:
                pass

# Cross-team DB sharing
db_to_scripts = {}
for path, info in py_files.items():
    for db in info['dbs']:
        if db not in db_to_scripts:
            db_to_scripts[db] = []
        db_to_scripts[db].append(path)

print('=== CROSS-TEAM DB SHARING (>1 script) ===')
for db, scripts in sorted(db_to_scripts.items()):
    if len(scripts) > 1:
        print(f'\n{db} ({len(scripts)}):')
        for s in scripts[:8]:
            print(f'  {s}')

# Similar script name clusters
print('\n\n=== SIMILAR NAME CLUSTERS ===')
clusters = {}
for path in py_files.keys():
    base_name = os.path.basename(path, '.py').lower()
    for kw in ['tina_autonomous', 'tina_brain', 'tina_memory', 'tina_decision', 'tina_hunter',
               'nana_', 'leo_', 'ray_', 'macro_', 'scanner', 'analyzer', 'backtest', 'watchlist',
               'portfolio', 'position', 'tracker', 'margin', 'institutional', 'dca', 'etf']:
        if kw in base_name:
            if kw not in clusters:
                clusters[kw] = []
            clusters[kw].append(path)
            break

for kw, paths in sorted(clusters.items(), key=lambda x: -len(x[1])):
    if len(paths) > 2:
        print(f'\n{kw}: {len(paths)} scripts')
        for p in sorted(paths)[:12]:
            print(f'  {p}')

# Find duplicate/target patterns
print('\n\n=== DUPLICATE CANDIDATE GROUPS ===')
# Find scripts that import the same module
mod_to_scripts = {}
for path, info in py_files.items():
    for mod in info['imports']:
        if mod not in mod_to_scripts:
            mod_to_scripts[mod] = []
        mod_to_scripts[mod].append(path)

for mod, scripts in sorted(mod_to_scripts.items(), key=lambda x: -len(x[1])):
    if len(scripts) > 5 and mod not in ('os', 'sys', 'json', 'time', 'datetime', 'pandas', 'numpy', 're', 'requests', 'yfinance'):
        print(f'{mod}: {len(scripts)} scripts')
        for s in sorted(scripts):
            print(f'  {s}')

print('\n\nDone. Total scripts:', len(py_files))