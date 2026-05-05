import json
with open('data/team_watch_list.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

print("Keys:", list(d.keys()))
# Find the structure
for k, v in d.items():
    if isinstance(v, list) and len(v) > 0:
        print(f"\n{k}: list of {len(v)} items")
        if isinstance(v[0], dict):
            print(f"  First item keys: {list(v[0].keys())}")
            if 'id' in v[0]:
                print(f"  First id: {v[0]['id']}")

# Find GUARD
for k, v in d.items():
    if isinstance(v, list):
        for item in v:
            if isinstance(item, dict) and item.get('id') == 'GUARD':
                print(f"\nFound GUARD in '{k}': priority={item.get('priority')}")
                item['priority'] = 'secondary'
                print(f"  Updated to: secondary")

with open('data/team_watch_list.json', 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print("\nDone")