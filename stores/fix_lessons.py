import json, sys
path = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term\lessons.json'
data = json.load(open(path, encoding='utf-8'))
fixed = 0
for i, l in enumerate(data['lessons']):
    if 'id' not in l:
        l['id'] = f"legacy_{l.get('date','uk')}_{i:04d}"
        print(f"Added id: {l['id']} for {l.get('date')}")
        fixed += 1
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Fixed {fixed} entries")