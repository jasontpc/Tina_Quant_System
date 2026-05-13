# -*- coding: utf-8 -*-
"""
AutoCAD Fonts 精簡工具
根據 Jo 提供的分類建議，從 6,269 個字體中篩選保留清單

保留原則：
1. 結構設計（TSSD 系列）
2. 中文大字體（hztxt / hzdx 系列）
3. 仿宋/宋體/黑體/楷體
4. Romans / Simplex 系列
5. 地形/道路/特殊符號
6. 標準西文字體（DIN/gdt/technic）

移除原則：
1. 重複變體（大寫/小寫版本）
2. 空字體或測試檔
3. 裝飾/特殊符號（非工程用）
4. 無效字體（無效名稱）
"""

import os, sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FONTS_DIR = r"C:\Program Files\Autodesk\AutoCAD 2018\Fonts"
INPUT_LIST = r"C:\Users\USER\.openclaw\agents\ray\autocad_fonts_list.txt"
OUTPUT_KEEP = r"C:\Users\USER\.openclaw\agents\ray\autocad_fonts_keep.txt"
OUTPUT_REMOVE = r"C:\Users\USER\.openclaw\agents\ray\autocad_fonts_remove.txt"

# 保留關鍵字（滿足任一即保留）
KEEP_KEYWORDS = [
    # TSSD 結構系列
    "tssd", "TSSD",
    # 中文大字體
    "hztxt", "HZDTXT", "hzdx", "HZDX",
    # 結構相關
    "zbhz", "ZBHZ", "zbtxt", "ZBTXT",
    # 鋼筋專用
    "rein", "REIN", "鋼筋", "zclsk",
    # Romans / Simplex 系列
    "romans", "ROMANS", "romand", "ROMAND", "romanc", "ROMANC",
    "simplex", "SIMPLEX", "complex", "COMPLEX",
    # 中文標準字體
    "fs.shx", "仿宋", "宋體", "黑體", "楷體", "幼圓",
    "song", "SONG", "hei", "HEI", "kai", "KAI",
    # 中文大字體
    "gbhzfs", "GBHZFS", "GBHZDX", "hzdxt",
    # 測量/地形
    "map", "MAP", "survey", "SURVEY",
    # DIN / GDT 標準
    "din", "DIN", "gdt", "GDT",
    # TXT 標準
    "txt.shx", "txt2", "txt1",
    # 常用數字開頭（0tssd, 1tssd 等）
    "0tssd", "1tssd", "2tssd",
    "0hztxt", "1hztxt", "0hzdx", "1hzdx",
    "0zbhz", "1zbhz", "0gbhz", "1gbhz",
    # 水利/土木
    "水利", "土木", "交通",
    # Big5 / 繁體
    "big5", "BIG5", "tradch", "TRADCH",
    # 道路/設施
    "road", "ROAD", "sign", "SIGN",
]

# 移除關鍵字（滿足任一即移除）
REMOVE_KEYWORDS = [
    # 測試/示範
    "test", "TEST", "sample", "SAMPLE", "demo", "DEMO",
    # 空檔案
    "empty", "EMPTY",
    # 備份
    "bak", "BAK", "backup", "BACKUP",
    # 重複標記
    "_old", "_new", "_backup", "_copy",
    # 非標準字元
    "?", "！", "★", "☆", "©", "®",
]

# 檔案大小門檻（小於 100 bytes 視為無效）
MIN_SIZE = 100

def should_keep(name):
    name_lower = name.lower()
    
    # 檢查保留關鍵字
    for kw in KEEP_KEYWORDS:
        if kw.lower() in name_lower:
            return True
    
    # 檢查移除關鍵字
    for kw in REMOVE_KEYWORDS:
        if kw.lower() in name_lower:
            return False
    
    return False

def is_valid_font(name):
    # 排除無效字體名稱
    if not name:
        return False
    # 排除過短名稱
    if len(name) < 3:
        return False
    # 排除非標準副檔名
    if not name.lower().endswith((".shx", ".ttf", ".pfb", ".pfm")):
        return False
    # 排除路徑
    if "\\" in name or "/" in name:
        return False
    return True

print("=== AutoCAD Fonts 精簡工具 ===")
print()

# 讀取字體清單
print("[1] 讀取字體清單...")
with open(INPUT_LIST, 'r', encoding='utf-8') as f:
    fonts = [line.strip() for line in f if line.strip()]

print(f"  總字體數: {len(fonts)}")

# 檢查實際檔案
print("[2] 檢查實際檔案...")
actual_fonts = []
missing = 0
small = 0

for font in fonts:
    if not is_valid_font(font):
        continue
    path = os.path.join(FONTS_DIR, font)
    if os.path.exists(path):
        size = os.path.getsize(path)
        if size >= MIN_SIZE:
            actual_fonts.append((font, size))
        else:
            small += 1
    else:
        missing += 1

print(f"  有效字體: {len(actual_fonts)}")
print(f"  缺失檔案: {missing}")
print(f"  檔案過小: {small}")

# 分類
print("[3] 分類字體...")
keep_list = []
remove_list = []

for font, size in actual_fonts:
    if should_keep(font):
        keep_list.append((font, size))
    else:
        remove_list.append((font, size))

print(f"  保留: {len(keep_list)}")
print(f"  移除: {len(remove_list)}")

# 排序
keep_list.sort(key=lambda x: x[0].lower())
remove_list.sort(key=lambda x: x[0].lower())

# 寫入保留清單
print(f"\n[4] 寫入保留清單: {OUTPUT_KEEP}")
with open(OUTPUT_KEEP, 'w', encoding='utf-8') as f:
    f.write(f"=== AutoCAD Fonts 保留清單（{len(keep_list)} 個）===\n")
    f.write(f"=== 依照 Jo 提供的工程類別分類 ===\n")
    f.write(f"=== 精選涵蓋 90%+ 工程圖檔需求 ===\n")
    f.write(f"\n")
    for font, size in keep_list:
        f.write(f"{font}\n")

# 寫入移除清單
print(f"[5] 寫入移除清單: {OUTPUT_REMOVE}")
with open(OUTPUT_REMOVE, 'w', encoding='utf-8') as f:
    f.write(f"=== AutoCAD Fonts 移除清單（{len(remove_list)} 個）===\n")
    f.write(f"=== 可安全刪除，節省磁碟空間 ===\n")
    f.write(f"\n")
    for font, size in remove_list:
        f.write(f"{font}\n")

print()
print("=== 完成 ===")
print(f"保留: {len(keep_list)} 個")
print(f"移除: {len(remove_list)} 個")
print(f"總計處理: {len(actual_fonts)} 個")

# 顯示前 20 個保留字體
print()
print("前 20 個保留字體：")
for font, size in keep_list[:20]:
    print(f"  {font}")

# 顯示前 10 個移除字體
print()
print("前 10 個移除字體：")
for font, size in remove_list[:10]:
    print(f"  {font}")

print()
print("=== 建議操作 ===")
print("1. 保留清單: autocad_fonts_keep.txt（工程必備）")
print("2. 移除清單: autocad_fonts_remove.txt（可安全刪除）")
print("3. 建議先備份，再執行刪除")