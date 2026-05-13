import os, re

root = r"C:\Users\USER\.openclaw\agents\ray"
pattern = re.compile(r"ray-v1|ray-deep|qwen2\.5:3b|qwen3\.5:4b|qwen2\.5:7b|MODEL_FAST|MODEL_DEEP")

for fname in os.listdir(root):
    if not fname.endswith('.py'):
        continue
    fpath = os.path.join(root, fname)
    try:
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        hits = []
        for i, line in enumerate(lines, 1):
            if pattern.search(line):
                hits.append(f"  {i}: {line.rstrip()}")
        if hits:
            print(f"\n=== {fname} ===")
            for h in hits:
                print(h)
    except Exception as e:
        print(f"{fname}: error {e}")
