#!/usr/bin/env python3
"""
Tina 自動化迴圈進度追蹤器
"""

import os
import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path("C:/Users/USER/.openclaw/workspace/memory")
PROGRESS_FILE = MEMORY_DIR / "automation_progress.md"

def read_progress():
    if PROGRESS_FILE.exists():
        return PROGRESS_FILE.read_text(encoding='utf-8')
    return None

def parse_progress(text):
    """解析進度檔"""
    result = {
        'current_step': 1,
        'cycle_count': 0,
        'last_updated': None,
        'steps': {}
    }
    
    for line in text.split('\n'):
        if '當前步驟:' in line:
            try:
                result['current_step'] = int(line.split(':')[1].strip())
            except:
                pass
        elif '循環計數:' in line:
            try:
                result['cycle_count'] = int(line.split(':')[1].strip())
            except:
                pass
        elif '最後更新:' in line or '最後更新:' in line:
            result['last_updated'] = line.split(':')[1].strip()
    
    return result

def show_progress():
    text = read_progress()
    if not text:
        print("❌ 進度檔案不存在")
        return
    
    info = parse_progress(text)
    
    print("\n📊 Tina 自動化迴圈進度")
    print("=" * 50)
    print(f"   當前步驟: {info['current_step']}/10")
    print(f"   循環計數: {info['cycle_count']}")
    print(f"   最後更新: {info['last_updated']}")
    print("=" * 50)
    
    # 顯示步驟狀態
    step_names = {
        1: "分析失敗原因",
        2: "安裝缺少技能",
        3: "擴充資料",
        4: "優化評分",
        5: "回測股票池",
        6: "分級策略",
        7: "動態調整",
        8: "權重優化",
        9: "系統檢討",
        10: "執行改善"
    }
    
    for i in range(1, 11):
        status = "✅" if i < info['current_step'] else ("🔄" if i == info['current_step'] else "⏳")
        print(f"   {status} Step {i}: {step_names[i]}")
    
    print()

if __name__ == "__main__":
    show_progress()