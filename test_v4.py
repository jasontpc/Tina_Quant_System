import json
data = json.load(open('stores/long_term/axioms_v4.0.json', 'r', encoding='utf-8'))
print(f'Loaded {len(data)} axioms')
for d in data:
    tc = d.get('thorp_calculus', {})
    print(f"  #{d['id']}: {d['when'][:30]}... conf={d['confidence']} thorp={d.get('thorp_aligned',False)} calc={'YES' if tc else 'NONE'}")