import sqlite3, sys, requests, json, re, time, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = 'ray_wisdom.db'
MODEL_DEEP = 'ray-deep-v1'
OLLAMA_URL = 'http://localhost:11434/api/chat'
WISDOM_STORE = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
OUT_PATH = os.path.join(WISDOM_STORE, 'ray_forbidden_rules.json')
os.makedirs(WISDOM_STORE, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('''SELECT axiom_id, symbol, diagnosis, confidence
             FROM wisdom_corrections WHERE confidence < 0.7
             ORDER BY confidence ASC LIMIT 20''')
failures = [dict(row) for row in c.fetchall()]
conn.close()

lines = []
for f in failures:
    sym = f.get('symbol', '?') or '?'
    diag = f.get('diagnosis', '')[:100]
    lines.append(f'- [{sym}] {diag}')
all_failures_text = '\n'.join(lines)

def call_deep(prompt, timeout=240):
    resp = requests.post(OLLAMA_URL, json={
        'model': MODEL_DEEP,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False,
        'options': {'temperature': 0.25, 'top_p': 0.85, 'num_predict': 1500}
    }, timeout=timeout)
    return resp.json().get('message', {}).get('content', '')

def parse(raw):
    for try_ex in [json.loads, lambda x: json.loads(re.search(r'\[[\s\S]+\]', x).group())]:
        try:
            return try_ex(raw)
        except:
            pass
    return []

# Each master gets 2 rules
all_rules = []
master_targets = ['Taleb', 'Thorp', 'Simons', 'Connors', 'Dalio']

for master in master_targets:
    prompt = f"""你是 {master} 交易大師的邏輯執行器。

## {master} 框架關鍵詞：
""" + ({
    'Taleb': '反脆弱、肥尾、啞鈴、尾部對沖',
    'Thorp': '凱利公式、二元結局、優勢開發、紀律',
    'Simons': 'Regime Switch、統計異常、趨勢追蹤',
    'Connors': '均值回歸、RSI2、彈簧理論',
    'Dalio': '多樣化、相關性、風險分散'
}[master]) + """

## 失敗案例：
""" + all_failures_text + """

## 任務：
根據以上失敗案例，生成 2 條「If-Then 禁止規則」，必須符合 {master} 框架。

## 輸出格式（純 JSON 陣列）：
[
  {{
    "rule": "If [具體條件] Then [禁止動作]",
    "master": "{master}",
    "priority": 1,
    "taleb_aligned": {"true" if master == "Taleb" else "false"},
    "taleb_reason": "（taleb_aligned=true必填）使用肥尾/啞鈴/尾部對沖/反脆弱",
    "thorp_aligned": {"true" if master == "Thorp" else "false"},
    "thorp_reason": "（thorp_aligned=true必填）使用凱利/勝率/二元結局/紀律"
  }},
  {{...第2條...}}
]

## 嚴格要求：
1. rule 必須有具體數值（例如 RSI>75 而非「RSI過高」）
2. 每條規則的 when 條件必須引用框架關鍵詞
3. 只輸出 JSON，不要其他文字

只輸出 JSON。"""
    print(f'[{master}] Calling ray-deep-v1...')
    raw = call_deep(prompt)
    print(f'  Raw length: {len(raw)}')
    rules = parse(raw)
    if rules:
        print(f'  ✅ {len(rules)} rules')
        all_rules.extend(rules)
    else:
        print(f'  ❌ Parse failed, raw: {raw[:200]}')
    time.sleep(3)

print()
print(f'Total rules: {len(all_rules)}')

# Deduplicate
seen = set()
unique = []
for r in all_rules:
    key = r.get('rule', '')[:80]
    if key and key not in seen:
        seen.add(key)
        unique.append(r)

rules = unique[:10]

# Save
output = {'schema': 'ray_forbidden_rules_v1', 'version': '1.0', 'generated': '2026-05-13', 'count': len(rules), 'rules': rules}
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'Saved: {OUT_PATH}')
for r in rules:
    print(f"  [{r.get('master','?')}] P{r.get('priority','?')}: {r.get('rule','')[:70]}")