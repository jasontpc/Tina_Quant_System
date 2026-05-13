import os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

root = r"C:\Users\USER\.openclaw\agents"
pattern = re.compile(r"streamlit|use_container_width|st\.st", re.IGNORECASE)
results = []

for agent_dir in os.listdir(root):
    agent_path = os.path.join(root, agent_dir)
    if not os.path.isdir(agent_path):
        continue
    for fname in os.listdir(agent_path):
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(agent_path, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            hits = []
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    hits.append(f"  {i}: {line.rstrip()}")
            if hits:
                results.append(f"\n=== [{agent_dir}] {fname} ===")
                results.extend(hits)
        except Exception as e:
            pass

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if results:
    print('\n'.join(results))
else:
    print('No streamlit files found')
