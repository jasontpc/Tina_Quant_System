with open('ray_logic_distiller.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def distill_failure_case(failure, all_failures_text):
    """使用 ray-deep-v1 將單筆失敗蒸餾成 If-Then 禁止規則"""
    prompt = f"""你是 {failure['master']} 交易大師的邏輯執行器。

以下是一個失敗案例：
- 標的：{failure.get('symbol','UNKNOWN')}
- 診斷：{failure.get('diagnosis','')}
- 信心：{failure.get('confidence', 0)}

請將此案例轉化為 1 條「If-Then 絕對禁止規則」，格式如下：
{{
  "rule": "If [具體條件] Then [禁止/執行動作]",
  "master": "{failure.get('master', 'UNKNOWN')}",
  "priority": 1,
  "case_id": "{failure.get('axiom_id','')}"
}}'''

new = '''def distill_failure_case(failure, all_failures_text):
    """使用 ray-deep-v1 將單筆失敗蒸餾成 If-Then 禁止規則"""
    master = failure.get('master') or 'SYSTEM'
    prompt = f"""你是 {master} 交易大師的邏輯執行器。

以下是一個失敗案例：
- 標的：{failure.get('symbol','UNKNOWN')}
- 診斷：{failure.get('diagnosis','')}
- 信心：{failure.get('confidence', 0)}

請將此案例轉化為 1 條「If-Then 絕對禁止規則」，格式如下：
{{
  "rule": "If [具體條件] Then [禁止/執行動作]",
  "master": "{master}",
  "priority": 1,
  "case_id": "{failure.get('axiom_id','')}"
}}'''

if old in content:
    content = content.replace(old, new)
    with open('ray_logic_distiller.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('Not found')