# -*- coding: utf-8 -*-
"""
AutoCAD Fonts 移除腳本
根據 remove 清單，將字體移至備份資料夾後刪除
"""

import os, sys, shutil, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FONTS_DIR = r"C:\Program Files\Autodesk\AutoCAD 2018\Fonts"
REMOVE_LIST = r"C:\Users\USER\.openclaw\agents\ray\autocad_fonts_remove.txt"
BACKUP_DIR = r"C:\Users\USER\.openclaw\agents\ray\fonts_backup"
LOG_FILE = r"C:\Users\USER\.openclaw\agents\ray\fonts_removed_log.txt"

def remove_fonts():
    print("=== AutoCAD Fonts 移除腳本 ===")
    print()
    
    # 讀取移除清單
    if not os.path.exists(REMOVE_LIST):
        print(f"ERROR: {REMOVE_LIST} not found")
        return
    
    with open(REMOVE_LIST, 'r', encoding='utf-8') as f:
        fonts_to_remove = [line.strip() for line in f if line.strip() and not line.startswith("#") and line.strip()]

    print(f"要移除的字體: {len(fonts_to_remove)} 個")
    print(f"備份資料夾: {BACKUP_DIR}")
    print()
    
    # 建立備份資料夾
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # 讀取已存在的備份（避免重複移動）
    existing_backup = set(os.listdir(BACKUP_DIR)) if os.path.exists(BACKUP_DIR) else set()
    
    removed = 0
    skipped = 0
    errors = 0
    
    with open(LOG_FILE, 'w', encoding='utf-8') as log:
        log.write(f"=== AutoCAD Fonts 移除日誌 ===\n")
        log.write(f"時間: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"總計: {len(fonts_to_remove)} 個\n\n")
        
        for font in fonts_to_remove:
            font_path = os.path.join(FONTS_DIR, font)
            backup_path = os.path.join(BACKUP_DIR, font)
            
            if not os.path.exists(font_path):
                skipped += 1
                log.write(f"SKIP: {font} (not found)\n")
                continue
            
            try:
                # 移動到備份資料夾
                shutil.move(font_path, backup_path)
                removed += 1
                log.write(f"OK: {font}\n")
                if removed % 100 == 0:
                    print(f"  已移除: {removed}")
            except Exception as e:
                errors += 1
                log.write(f"ERROR: {font} - {e}\n")
        
        log.write(f"\n=== 結果 ===\n")
        log.write(f"移除成功: {removed}\n")
        log.write(f"跳過: {skipped}\n")
        log.write(f"錯誤: {errors}\n")
    
    print()
    print("=== 完成 ===")
    print(f"移除成功: {removed}")
    print(f"跳過: {skipped}")
    print(f"錯誤: {errors}")
    print(f"日誌: {LOG_FILE}")
    print()
    print(f"備份位置: {BACKUP_DIR}")
    print("建議：確認 AutoCAD 正常運作後，再刪除備份資料夾")

if __name__ == "__main__":
    print("確認要移除字體？（需要管理員權限）")
    print("輸入 'yes' 繼續：")
    confirm = input().strip().lower()
    if confirm == 'yes':
        remove_fonts()
    else:
        print("取消")