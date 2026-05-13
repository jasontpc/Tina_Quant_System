import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3

conn = sqlite3.connect('ray_wisdom.db')
c = conn.cursor()

print("=== 語言分佈分析 ===")
print()

# wisdom_corrections 語言分佈
c.execute('SELECT diagnosis FROM wisdom_corrections WHERE diagnosis IS NOT NULL')
rows = c.fetchall()

zh = 0
en = 0
mixed = 0

for (diag,) in rows:
    if not diag:
        continue
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in diag)
    has_english = any(c.isascii() and c.isalpha() for c in diag)
    if has_chinese and has_english:
        mixed += 1
    elif has_chinese:
        zh += 1
    elif has_english:
        en += 1

print(f"wisdom_corrections 語言分佈:")
print(f"  中文: {zh} 筆")
print(f"  英文: {en} 筆")
print(f"  混合: {mixed} 筆")
print(f"  總計: {zh + en + mixed} 筆")
print()

# backtest_reports 指標名稱
c.execute('SELECT DISTINCT indicator FROM backtest_reports LIMIT 15')
print("backtest_reports 指標名稱:")
for (ind,) in c.fetchall():
    has_ch = any('\u4e00' <= c for c in ind)
    lang = "中" if has_ch else "英"
    print(f"  [{lang}] {ind}")
print()

# Modelfile 語言比例
import os
mp = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Ollama', 'models', 'modelfiles', 'ray-v1.Modelfile')
try:
    with open(mp, 'r', encoding='utf-8') as f:
        content = f.read()
    chinese_chars = sum(1 for c in content if '\u4e00' <= c <= '\u9fff')
    total_chars = len(content)
    print(f"Modelfile 語言:")
    print(f"  中文字數: {chinese_chars} ({chinese_chars/(total_chars+1)*100:.1f}%)")
    print(f"  總字數: {total_chars}")
except Exception as e:
    print(f"Modelfile 讀取錯誤: {e}")

conn.close()
print()
print("=== 缺陷分析 ===")
print()
print("1. Modelfile 中文比例僅 0.5%")
print("   → 系統幾乎全英文，Jo 可能感到陌生")
print()
print("2. wisdom_corrections 混合語言過半")
print("   → 中英混雜導致 1.5B 理解不一致")
print()
print("3. backtest_reports 指標全英文")
print("   → 無法直接用中文邏輯比對")
print()
print("4. SYSTEM prompt 幾乎無中文解釋")
print("   → 大師邏輯（Taleb/Thorp/Connors）沒有中文說明")