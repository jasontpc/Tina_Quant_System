"""
Progress Update Script
讀取/寫入 automation_progress.md
追蹤當前步驟和循環計數
"""

import os
import re
import datetime
from pathlib import Path

MEMORY_PATH = Path("C:/Users/USER/.openclaw/workspace/memory/automation_progress.md")

def read_progress():
    """讀取當前進度"""
    if not MEMORY_PATH.exists():
        return {
            "current_step": 1,
            "loop_count": 0,
            "last_updated": ""
        }
    
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    step_match = re.search(r"- 當前步驟:\s*(\d+)", content)
    loop_match = re.search(r"- 循環計數:\s*(\d+)", content)
    date_match = re.search(r"- 最後更新:\s*([\d\-: ]+)", content)
    
    return {
        "current_step": int(step_match.group(1)) if step_match else 1,
        "loop_count": int(loop_match.group(1)) if loop_match else 0,
        "last_updated": date_match.group(1).strip() if date_match else ""
    }

def write_progress(current_step, loop_count, step_history=None):
    """寫入進度"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    if step_history is None:
        step_history = []
    
    history_lines = []
    if step_history:
        history_lines.append("\n## 步驟歷史\n")
        for entry in step_history[-5:]:  # 只保留最近5筆
            history_lines.append(f"- Step {entry['step']}: {entry['action']} ({entry['time']})\n")
    
    content = f"""# Tina 自動化循環進度

## 目前狀態
- 當前步驟: {current_step}
- 循環計數: {loop_count}
- 最後更新: {now}

## 步驟歷史
（空，剛初始化）
"""
    
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        f.write(content)

def update_step(step, action):
    """更新單一步驟"""
    progress = read_progress()
    progress["current_step"] = step
    progress["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    write_progress(progress["current_step"], progress["loop_count"])

def increment_loop():
    """增加循環計數"""
    progress = read_progress()
    progress["loop_count"] += 1
    progress["current_step"] = 1
    progress["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    write_progress(progress["current_step"], progress["loop_count"])
    return progress["loop_count"]

if __name__ == "__main__":
    # 測試
    prog = read_progress()
    print(f"Current Step: {prog['current_step']}, Loop Count: {prog['loop_count']}")
    
    # 更新進度
    write_progress(5, prog["loop_count"])
    print("Progress updated")
