# -*- coding: utf-8 -*-
"""
Short-Term Memory Writer
=======================
快速寫入短期記憶的標準工具。

用法：
  from short_term_writer import write_memory
  write_memory('observation', 'Macro job發現TWII單日跌-2.3%', tags=['TWII', 'macro'])

  python short_term_writer.py --type observation --summary "..." --tags TWII,macro --importance 7
"""

import sys, json, sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
ST_DIR = STORES_DIR / 'short_term'
WORK_DIR = STORES_DIR / 'working'
LT_DIR = STORES_DIR / 'long_term'

ST_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)
LT_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_TYPES = ['observation', 'decision', 'news', 'pattern', 'lesson', 'metric', 'framework_change']
MEMORY_COUNTER_FILE = STORES_DIR / 'memory_counter.json'

def get_next_id() -> str:
    """產生序號ID"""
    today = datetime.now().strftime('%Y%m%d')
    counter = {'date': today, 'seq': 0}
    
    if MEMORY_COUNTER_FILE.exists():
        with open(MEMORY_COUNTER_FILE, 'r', encoding='utf-8') as f:
            counter = json.load(f)
    
    if counter.get('date') != today:
        counter = {'date': today, 'seq': 0}
    
    counter['seq'] += 1
    with open(MEMORY_COUNTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(counter, f, ensure_ascii=False, indent=2)
    
    return f"st_{today}_{counter['seq']:03d}"

def write_memory(
    mtype: str,
    summary: str,
    detail: str = '',
    source: str = 'system',
    tags: List[str] = None,
    importance: int = 5,
    links: List[str] = None,
    expiry_days: int = 30,
    status: str = 'active',
    **kwargs
) -> str:
    """寫入短期記憶"""
    if mtype not in MEMORY_TYPES:
        raise ValueError(f'Unknown type: {mtype}')
    
    memory = {
        'id': get_next_id(),
        'type': mtype,
        'source': source,
        'timestamp': datetime.now().isoformat(),
        'expiry_days': expiry_days,
        'tags': tags or [],
        'summary': summary,
        'detail': detail,
        'importance': importance,
        'links': links or [],
        'status': status,
        **kwargs
    }
    
    filepath = ST_DIR / f"{datetime.now().strftime('%Y%m%d')}_{mtype}_{source}.json"
    
    # 讀取當日已有記憶（如果存在的話）
    existing = []
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            existing = data if isinstance(data, list) else [data]
    
    existing.append(memory)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f'[Short-Term Write] {memory["id"]} | {mtype} | {summary[:50]}')
    return memory['id']

def read_today_memories(mtype: str = None) -> list:
    """讀取今日所有記憶，或依類型過濾"""
    today = datetime.now().strftime('%Y%m%d')
    results = []
    
    for f in ST_DIR.glob(f'{today}_*.json'):
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
            items = data if isinstance(data, list) else [data]
            for item in items:
                if mtype is None or item.get('type') == mtype:
                    results.append(item)
    
    results.sort(key=lambda x: x['timestamp'])
    return results

def read_recent_memories(days: int = 7, mtype: str = None) -> list:
    """讀取最近N天的記憶"""
    results = []
    today = datetime.now()
    
    for d in range(days):
        date = (today - timedelta(days=d)).strftime('%Y%m%d')
        for f in ST_DIR.glob(f'{date}_*.json'):
            with open(f, 'r', encoding='utf-8') as fp:
                try:
                    data = json.load(fp)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if mtype is None or item.get('type') == mtype:
                            results.append(item)
                except:
                    pass
    
    results.sort(key=lambda x: x['timestamp'], reverse=True)
    return results

def get_short_term_summary() -> dict:
    """取得短期記憶現況摘要"""
    today = datetime.now().strftime('%Y%m%d')
    stats = defaultdict(int)
    total = 0
    active = 0
    
    for f in ST_DIR.glob('*.json'):
        with open(f, 'r', encoding='utf-8') as fp:
            try:
                data = json.load(fp)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    total += 1
                    stats[item.get('type', 'unknown')] += 1
                    if item.get('status') == 'active':
                        active += 1
            except:
                pass
    
    # 本週新
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
    week_count = 0
    for f in ST_DIR.glob('*.json'):
        if f.stem >= week_ago:
            week_count += 1
    
    return {
        'total': total,
        'active': active,
        'this_week': week_count,
        'by_type': dict(stats)
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Short-Term Memory Writer')
    parser.add_argument('--type', '-t', required=True, choices=MEMORY_TYPES)
    parser.add_argument('--summary', '-s', required=True)
    parser.add_argument('--detail', '-d', default='')
    parser.add_argument('--source', default='system')
    parser.add_argument('--tags', '-g', default='')
    parser.add_argument('--importance', '-i', type=int, default=5)
    parser.add_argument('--links', '-l', default='')
    parser.add_argument('--expiry', '-e', type=int, default=30)
    parser.add_argument('--status', default='active')
    args = parser.parse_args()
    
    tags = [t.strip() for t in args.tags.split(',')] if args.tags else []
    links = [ln.strip() for ln in args.links.split(',')] if args.links else []
    
    mid = write_memory(
        mtype=args.type,
        summary=args.summary,
        detail=args.detail,
        source=args.source,
        tags=tags,
        importance=args.importance,
        links=links,
        expiry_days=args.expiry,
        status=args.status
    )
    print(f'Done: {mid}')