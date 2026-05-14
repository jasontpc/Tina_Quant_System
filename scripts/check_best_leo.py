import json

p = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\leo\matrix_results\best_leo_params.json'
with open(p) as f:
    raw = f.read()
print('Raw first 200 chars:', repr(raw[:200]))
data = json.loads(raw)
print(json.dumps(data, ensure_ascii=False, indent=2))