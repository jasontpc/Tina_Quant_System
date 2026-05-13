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

MASTER_FRAMEWORKS = {
    'Taleb': {
        'keywords': '反脆弱、肥尾、啞鈴、尾部對沖',
        'taleb_aligned': True, 'thorp_aligned': False,
        'taleb_reason': '使用肥尾/啞鈴/尾部對沖/反脆弱',
        'thorp_reason': ''
    },
    'Thorp': {
        'keywords': '凱利公式、二元結局、優勢開發、紀律',
        'taleb_aligned': False, 'thorp_aligned': True,
        'taleb_reason': '',
        'thorp_reason': '使用凱利/勝率/二元結局/紀律'
    },
    'Simons': {
        'keywords': 'Regime Switch、統計異常、趨勢追蹤',
        'taleb_aligned': False, 'thorp_aligned': False,
        'taleb_reason': '', 'thorp_reason': ''
    },
    'Connors': {
        'keywords': '均值回歸、RSI2、彈簧理論',
        'taleb_aligned': False, 'thorp_aligned': False,
        'taleb_reason': '', 'thorp_reason': ''
    },
    'Dalio': {
        'keywords': '多樣化、相關性、風險分散',
        'taleb_aligned': False, 'thorp_aligned': False,
        'taleb_reason': '', 'thorp_reason': ''
    }
}

def call_deep(model, prompt, timeout=240):
    resp = requests.post(OLLAMA_URL, json={
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'stream': False,
        'options': {'temperature': 0.25, 'top_p': 0.85, 'num_predict': 2000}
    }, timeout=timeout)
    return resp.json().get('message', {}).get('content', '')

def parse_rules(raw):
    """Incremental parse: try full JSON first, then partial objects"""
    # Try full parse
    try:
        return json.loads(raw), True
    except:
        pass
    # Try extract from markdown
    match = re.search(r'\[[\s\S]+\]', raw)
    if match:
        try:
            return json.loads(match.group()), True
        except:
            pass
    # Incremental: find individual rule objects
    partial = []
    # Pattern: {"rule": "...", "master": "...", ...}
    rule_matches = re.findall(r'\{[^{}]*?"rule"[^{}]+\}', raw)
    for rm in rule_matches:
        try:
            obj = json.loads(rm)
            if 'rule' in obj and 'master' in obj:
                partial.append(obj)
        except:
            pass
    if partial:
        return partial, False
    return [], False

def distill_master(master, framework, all_failures_text, max_retries=3):
    fw = framework
    prompt = f"""你是 {master} 交易大師的邏輯執行器。

## {master} 框架關鍵詞：
{fw['keywords']}

## 失敗案例：
{all_failures_text}

## 任務：
根據失敗案例，生成 2 條「If-Then 禁止規則」，必須符合 {master} 框架。

## 輸出格式（純 JSON 陣列，嚴格 2 條）：
[
  {{
    "rule": "If [具體數值條件] Then [禁止動作]",
    "master": "{master}",
    "priority": 1,
    "taleb_aligned": {"true" if fw['taleb_aligned'] else "false"},
    "taleb_reason": "{fw['taleb_reason']}",
    "thorp_aligned": {"true" if fw['thorp_aligned'] else "false"},
    "thorp_reason": "{fw['thorp_reason']}"
  }},
  {{
    "rule": "If [具體數值條件] Then [禁止動作]",
    "master": "{master}",
    "priority": 1,
    "taleb_aligned": {"true" if fw['taleb_aligned'] else "false"},
    "taleb_reason": "{fw['taleb_reason']}",
    "thorp_aligned": {"true" if fw['thorp_aligned'] else "false"},
    "thorp_reason": "{fw['thorp_reason']}"
  }}
]

## 嚴格要求：
1. rule 必須有具體數值（如 RSI>75，而非「RSI過高」）
2. 每條規則的 when 條件必須引用框架關鍵詞之一
3. 只輸出 JSON 陣列，不要其他文字

只輸出 JSON。"""

    for attempt in range(max_retries):
        print(f'  [{master}] Attempt {attempt+1}/{max_retries}...')
        raw = call_deep(MODEL_DEEP, prompt)
        print(f'  [{master}] Raw length: {len(raw)}')
        rules, complete = parse_rules(raw)
        if rules:
            print(f'  [{master}] ✅ {len(rules)} rules (complete={complete})')
            return rules, complete
        print(f'  [{master}] ❌ Parse failed, raw preview: {raw[:100]}')
        time.sleep(2)
    return [], False

# Run
all_rules = []
master_complete = {}

for master, framework in MASTER_FRAMEWORKS.items():
    print(f'\n[{master}] Starting...')
    rules, complete = distill_master(master, framework, all_failures_text)
    if rules:
        all_rules.extend(rules)
        master_complete[master] = complete
    time.sleep(3)

# Dedup
seen = set()
unique = []
for r in all_rules:
    key = r.get('rule', '')[:80]
    if key and key not in seen:
        seen.add(key)
        unique.append(r)

rules = unique[:10]

# Save
output = {
    'schema': 'ray_forbidden_rules_v1',
    'version': '1.1',
    'generated': '2026-05-13',
    'count': len(rules),
    'rules': rules
}
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\n=== Done ===')
print(f'Saved: {OUT_PATH} ({len(rules)} rules)')
for r in rules:
    print(f"  [{r.get('master','?')}] P{r.get('priority','?')}: {r.get('rule','')[:60]}")