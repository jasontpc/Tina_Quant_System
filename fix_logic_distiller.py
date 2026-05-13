import re

with open('ray_logic_distiller.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function
idx = content.find('def distill_batch')
if idx == -1:
    print('Function not found')
    exit(1)

# Find the next function definition (def main or def distill_failure_case)
idx2 = content.find('\ndef distill_failure_case', idx + 1)
if idx2 == -1:
    idx2 = content.find('\ndef main', idx + 1)

func_text = content[idx:idx2]

# Build new function
NEW_FUNC = '''
def distill_batch(all_failures_text):
    """使用 ray-deep-v1 批量蒸餾 10 條禁止規則"""
    prompt = """你是 Ray 系統的 7B 總參謀長，任務是將失敗案例蒸餾成 4B 必須遵守的「絕對禁止規則」。

## 五大大師框架（你必須引用這些概念）：

【Taleb — 反脆弱 / 肥尾 / 啞鈴 / 尾部對沖】
  - 核心：系統在極端波動下反而變強；常態分布低估極端事件機率
  - 啞鈴：避開中等風險，資金压在「極安全」+「極高槓桿」兩端
  - 尾部對沖：不追求精準預測，確保極端情況不會摧毁系統

【Thorp — 凱利公式 / 二元結局 / 優勢開發 / 紀律】
  - 核心：f* = (bp - q)/b，根據勝率與盈虧比決定下注比例
  - 二元結局：結果只有贏或輸，沒有中間地帶
  - 紀律：每筆交易獨立服從統計紀律，不情緒化

【Simons — Regime Switch / 統計異常 / 趨勢追蹤】
【Connors — 均值回歸 / RSI2 / 彈簧理論】
【Dalio — 多樣化 / 相關性 / 風險分散】

## 失敗案例摘要：
""" + all_failures_text[:3000] + """

## 任務：
分析失敗案例，找出 5 個最常見的失敗模式，對應五位大師的防禦邏輯，生成 10 條「If-Then 禁止規則」。

## 輸出格式（純 JSON 陣列）：
[
  {
    "rule": "If [具體條件] Then [禁止動作]",
    "master": "大師名（必須是 Taleb/Thorp/Simons/Connors/Dalio 之一）",
    "priority": 1-3（1=最高立即執行，2=標準，3=謹慎參考）",
    "taleb_aligned": true/false,
    "taleb_reason": "（taleb_aligned=true必填）明確說明使用了肥尾/啞鈴/尾部對沖/反脆弱哪個概念",
    "thorp_aligned": true/false,
    "thorp_reason": "（thorp_aligned=true必填）明確說明使用了凱利/勝率/二元結局/紀律哪個概念"
  }
]

## 框架強制引用：
  每條規則的 rule 必須從以下 8 個關鍵詞中至少引用 1 個，否則視為框架未對齊：
  Taleb陣營：肥尾、啞鈴、尾部對沖、反脆弱
  Thorp陣營：凱利、勝率、二元結局、紀律

## 嚴格校驗：
  1. rule 必須有具體數值（不能是「波動大」而要是「RSI>75」）
  2. taleb_aligned=true 時，taleb_reason 必須提到「肥尾/啞鈴/尾部對沖/反脆弱」之一
  3. thorp_aligned=true 時，thorp_reason 必須提到「凱利/勝率/二元結局/紀律」之一
  4. 只輸出 JSON，嚴禁其他文字。
"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL_DEEP,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2, "top_p": 0.85, "num_predict": 600}
        }, timeout=120)
        raw = resp.json().get("message", {}).get("content", "")
        if raw:
            try:
                return json.loads(raw)
            except:
                match = re.search(r'\[[\s\S]+\]', raw)
                if match:
                    return json.loads(match.group())
    except Exception as e:
        print(f"  [ERROR] batch distillation failed: {e}")
    return []

'''

new_content = content[:idx] + NEW_FUNC.strip() + content[idx2:]
with open('ray_logic_distiller.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('Done')