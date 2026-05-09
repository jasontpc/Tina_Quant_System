# -*- coding: utf-8 -*-
"""
Tina 記憶查詢系統
================
自動查詢 MEMORY.md + experience_ledger

功能：
1. 查詢特定標的的历史经验
2. 查詢最近決策
3. 查詢 lessons
4. 輸出結構化參考
"""

import sys, json, re
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace')
MEMORY_FILE = WORKSPACE / 'MEMORY.md'
LEDGER_FILE = WORKSPACE / 'Tina_Quant_System' / 'data' / 'experience_ledger.json'
DECISION_LOG = WORKSPACE / 'memory' / 'decision_log.md'
LESSONS_DIR = WORKSPACE / 'memory' / 'lessons'

def query_ledger(symbol: str = None) -> dict:
    """查詢 experience_ledger"""
    if not LEDGER_FILE.exists():
        return {"error": "Ledger not found"}
    
    with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
        ledger = json.load(f)
    
    # Ledger 是 list 或 dict
    if isinstance(ledger, list):
        entries = ledger
    elif isinstance(ledger, dict):
        entries = ledger.get("entries", ledger)
    else:
        entries = []
    
    if symbol:
        # 查詢特定標的
        results = []
        for entry in entries:
            entry_str = str(entry)
            if symbol.upper() in entry_str.upper():
                results.append(entry)
        return {"symbol": symbol, "count": len(results), "entries": results}
    
    return {"total": len(entries), "ledger": entries}

def query_decision_log(symbol: str = None, limit: int = 5) -> list:
    """查詢最近決策"""
    if not DECISION_LOG.exists():
        return []
    
    with open(DECISION_LOG, 'r', encoding='utf-8') as f:
        content = f.read()
    
    decisions = []
    # 解析決策區塊
    blocks = content.split('## 決策日誌')
    for block in blocks[-limit-1:-1] if len(blocks) > limit else blocks[1:]:
        if symbol and symbol.upper() not in block.upper():
            continue
        decisions.append(block.strip()[:500])  # 只取前500字
    
    return decisions

def query_lessons(symbol: str = None) -> dict:
    """查詢 lessons"""
    wins = []
    losses = []
    
    wins_dir = LESSONS_DIR / 'wins'
    losses_dir = LESSONS_DIR / 'losses'
    
    if wins_dir.exists():
        for f in wins_dir.glob('*.md'):
            if symbol and symbol.upper() not in f.read_text(encoding='utf-8').upper():
                continue
            wins.append({"file": f.name, "preview": f.read_text(encoding='utf-8')[:200]})
    
    if losses_dir.exists():
        for f in losses_dir.glob('*.md'):
            if symbol and symbol.upper() not in f.read_text(encoding='utf-8').upper():
                continue
            losses.append({"file": f.name, "preview": f.read_text(encoding='utf-8')[:200]})
    
    return {"wins": wins[:3], "losses": losses[:3], "total_wins": len(wins), "total_losses": len(losses)}

def query_memory(symbol: str = None) -> dict:
    """查詢 MEMORY.md 持仓和经验"""
    if not MEMORY_FILE.exists():
        return {"error": "MEMORY not found"}
    
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取持仓记录
    positions = []
    if '，持倉記錄' in content or '，持倉' in content:
        # 簡單的持仓提取
        lines = content.split('\n')
        for line in lines:
            if '|' in line and any(s in line for s in ['2382', '00713', 'META', 'MSFT', '00981A']):
                positions.append(line.strip())
    
    # 提取最近的 lessons
    lessons_summary = []
    if 'Lessons' in content or '持倉記錄' in content:
        lessons_summary = content[-2000:].split('\n')[-20:]  # 最近20行
    
    return {
        "positions": positions[-10:] if positions else [],
        "recent_lines": lessons_summary
    }

def full_query(symbol: str = None) -> dict:
    """完整查詢"""
    print('='*60)
    print(f'Tina 記憶查詢 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    if symbol:
        print(f'查詢標的：{symbol}')
    print('='*60)
    print()
    
    # 1. MEMORY 查詢
    print('[1/4] MEMORY.md 查詢')
    print('-'*40)
    mem = query_memory(symbol)
    if "error" not in mem:
        print(f'  持仓記錄：{len(mem.get("positions", []))} 筆')
        for p in mem.get("positions", [])[:5]:
            print(f'    {p}')
    print()
    
    # 2. Ledger 查詢
    print('[2/4] Experience Ledger 查詢')
    print('-'*40)
    ledger = query_ledger(symbol)
    if "error" not in ledger:
        print(f'  總經驗：{ledger.get("total", 0)} 筆')
        if symbol:
            print(f'  {symbol} 相關：{ledger.get("count", 0)} 筆')
    print()
    
    # 3. Decision Log 查詢
    print('[3/4] 決策日誌 查詢')
    print('-'*40)
    decisions = query_decision_log(symbol, limit=3)
    print(f'  最近決策：{len(decisions)} 筆')
    for d in decisions:
        print(f'    {d[:100]}...')
    print()
    
    # 4. Lessons 查詢
    print('[4/4] Lessons 查詢')
    print('-'*40)
    lessons = query_lessons(symbol)
    print(f'  勝利經驗：{lessons.get("total_wins", 0)} 筆')
    print(f'  失敗教訓：{lessons.get("total_losses", 0)} 筆')
    
    print()
    print('='*60)
    
    return {
        "memory": mem,
        "ledger": ledger,
        "decisions": decisions,
        "lessons": lessons
    }

if __name__ == '__main__':
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    result = full_query(symbol)
