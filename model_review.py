import sqlite3, os, subprocess
from datetime import datetime

AGENT_DIR = r"C:\Users\USER\.openclaw\agents\ray"
DB = os.path.join(AGENT_DIR, "ray_wisdom.db")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=" * 60)
print("  7B 模型使用分析報告")
print("=" * 60)

# Check wisdom_corrections for usage
c.execute("SELECT COUNT(*) as cnt, MAX(created_at) as last FROM wisdom_corrections")
r = c.fetchone()
print(f"\nwisdom_corrections: {r[0]} 筆, 最新: {r[1]}")

# Check patterns.json
LONG_TERM = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term"
import json
for f in ['patterns.json', 'lessons.json']:
    fp = os.path.join(LONG_TERM, f)
    if os.path.exists(fp):
        data = json.load(open(fp, encoding='utf-8'))
        print(f"{f}: {len(str(data))} chars")

conn.close()

print("\n--- Ollama Models ---")
result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
print(result.stdout)

print("\n" + "=" * 60)
print("  7B 模型技能對比")
print("=" * 60)

models = [
    ("qwen2.5:7b",     "蒸餾/歸因/降級",  "14:00 歷史蒸餾 / 17:00 大師對齊 / ray_brain降級"),
    ("ray-deep-v1",    "失敗歸因蒸餾",    "14:05 失敗歸因 → 10大禁止規則"),
    ("ray-commander",  "情緒/宏觀",       "從未使用（預留 Phase2）"),
]

for name, role, usage in models:
    print(f"\n{name}")
    print(f"  角色: {role}")
    print(f"  使用時段: {usage}")

# Check ray_commander Modelfile
MODELS_DIR = os.environ.get("LOCALAPPDATA", "") + r"\Programs\Ollama\models"
ray_c_path = os.path.join(MODELS_DIR, "ray-commander")
if os.path.exists(ray_c_path):
    files = os.listdir(ray_c_path)
    print(f"\nray-commander 磁盤文件: {files}")

# Check ray-deep-v1 Modelfile
ray_d_path = os.path.join(MODELS_DIR, "ray-deep-v1")
if os.path.exists(ray_d_path):
    files = os.listdir(ray_d_path)
    print(f"ray-deep-v1 磁盤文件: {files}")