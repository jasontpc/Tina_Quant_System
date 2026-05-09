# -*- coding: utf-8 -*-
"""
accumulated_wisdom.py — 累計智慧累積器
=====================================
PowerShell 腳本寫入的觀測、決定、Lesson，透過此腳本彙總為智慧精華。

功能：
1. 讀取近期短期記憶（7-14天）
2. 識別高價值 Pattern / Lesson
3. 直接寫入 long_term/patterns.json 或 lessons.json（繞過蒸餾流程）
4. 為 PowerShell 腳本提供「直接累積」的接口

用法：
  python accumulated_wisdom.py aggregate --days 14        # 彙總14天記憶
  python accumulated_wisdom.py check                      # 檢查智慧庫狀態
  python accumulated_wisdom.py promote --id st_xxx         # 手動晉升特定記憶
"""

import sys, json, re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
STORES_DIR = BASE_DIR / "stores"
ST_DIR = STORES_DIR / "short_term"
LT_DIR = STORES_DIR / "long_term"
LT_DIR.mkdir(parents=True, exist_ok=True)

PATTERNS_FILE = LT_DIR / "patterns.json"
LESSONS_FILE = LT_DIR / "lessons.json"
WISDOM_FILE = LT_DIR / "accumulated_wisdom.json"

# 預設值
def empty_patterns(): return {"patterns": [], "metadata": {"last_updated": None, "total": 0}}
def empty_lessons(): return {"lessons": [], "metadata": {"last_updated": None, "total": 0}}
def empty_wisdom(): return {"insights": [], "metadata": {"last_aggregated": None, "sources": []}}

def load_json(filepath, default_factory):
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default_factory()

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== 讀取短期記憶 =====

def get_short_term(days=7, mtype=None):
    results = []
    today = datetime.now()
    for d in range(days):
        date = (today - timedelta(days=d)).strftime('%Y%m%d')
        for f in ST_DIR.glob(f'{date}_*.json'):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('status') == 'active':
                            if mtype is None or item.get('type') == mtype:
                                results.append(item)
            except:
                pass
    return results

# ===== Pattern 識別 =====

def identify_patterns(memories):
    """從記憶中識別可累積的 Pattern"""
    # 按 source + type 群組
    groups = defaultdict(list)
    for m in memories:
        if m.get('type') == 'observation':
            key = f"{m.get('source')}:{m.get('tags', [])}"
            groups[key].append(m)

    patterns = []
    for key, items in groups.items():
        if len(items) >= 3:
            # 計算出現頻率
            tags = set()
            for item in items:
                tags.update(item.get('tags', []))
            tags = list(tags)[:5]

            patterns.append({
                'name': key[:60],
                'occurrences': len(items),
                'avg_importance': sum(i.get('importance', 5) for i in items) / len(items),
                'first_seen': items[0]['timestamp'][:10],
                'last_seen': items[-1]['timestamp'][:10],
                'tags': tags,
                'source': items[0].get('source'),
                'type': 'observed',
                'hit_rate': 0.0  # 待驗證
            })
    return patterns

# ===== Lesson 識別 =====

def identify_lessons(memories):
    """從記憶中識別可累積的 Lesson"""
    lessons = []
    for m in memories:
        if m.get('type') in ('lesson', 'decision') and m.get('importance', 0) >= 7:
            lessons.append({
                'id': m.get('id'),
                'date': m['timestamp'][:10],
                'summary': m.get('summary', '')[:80],
                'detail': m.get('detail', ''),
                'source': m.get('source', 'PS'),
                'type': m.get('type'),
                'importance': m.get('importance', 5),
                'tags': m.get('tags', [])
            })
    return lessons

# ===== 寫入智慧庫 =====

def promote_patterns(patterns, dry_run=False):
    """寫入 patterns.json"""
    if dry_run:
        print(f"[DRY RUN] Would promote {len(patterns)} patterns")
        return 0

    data = load_json(PATTERNS_FILE, empty_patterns)
    existing = {p['name'] for p in data.get('patterns', [])}
    new_count = 0

    for p in patterns:
        if p['name'] in existing:
            continue
        # 給 ID
        existing_ids = [x['id'] for x in data['patterns'] if x['id'].startswith('pat_')]
        next_id = 1
        if existing_ids:
            nums = [int(x.split('_')[1]) for x in existing_ids]
            next_id = max(nums) + 1

        new_pattern = {
            'id': f"pat_{next_id:04d}",
            'name': p['name'],
            'category': 'ps_accumulated',
            'universe': infer_universe(p['tags']),
            'first_observed': p['first_seen'],
            'last_observed': p['last_seen'],
            'occurrences': p['occurrences'],
            'hit_rate': p['hit_rate'],
            'avg_gain': 0.0,
            'conditions': p['tags'],
            'status': 'observed',
            'confidence': min(10, int(p['avg_importance'])),
            'source': 'PS/PowerShell'
        }
        data['patterns'].append(new_pattern)
        new_count += 1
        print(f"  [PROMOTE] Pattern: {p['name'][:50]}")

    data['metadata'] = {
        'last_updated': datetime.now().isoformat(),
        'total': len(data['patterns'])
    }
    save_json(PATTERNS_FILE, data)
    return new_count

def promote_lessons(lessons, dry_run=False):
    """寫入 lessons.json"""
    if dry_run:
        print(f"[DRY RUN] Would promote {len(lessons)} lessons")
        return 0

    data = load_json(LESSONS_FILE, empty_lessons)
    existing_ids = {l['id'] for l in data.get('lessons', [])}
    new_count = 0

    for l in lessons:
        if l['id'] in existing_ids:
            continue
        new_lesson = {
            'id': l['id'],
            'type': l['type'],
            'date': l['date'],
            'summary': l['summary'],
            'detail': l['detail'],
            'source': l['source'],
            'tags': l['tags'],
            'status': 'archived',
            'importance': l['importance']
        }
        data['lessons'].append(new_lesson)
        new_count += 1
        print(f"  [PROMOTE] Lesson: {l['summary'][:60]}")

    data['metadata'] = {
        'last_updated': datetime.now().isoformat(),
        'total': len(data['lessons'])
    }
    save_json(LESSONS_FILE, data)
    return new_count

def infer_universe(tags):
    for t in tags:
        if 'TW' in t or '台' in t: return 'TW'
        if 'US' in t or 'SP' in t: return 'US'
        if 'SOX' in t: return 'SOX'
    return 'MULTI'

# ===== 彙總（aggregate）=====

def aggregate(days=14, dry_run=False):
    """彙總近期記憶為智慧"""
    print(f"\n=== Accumulated Wisdom | days={days} ===")

    memories = get_short_term(days=days)
    print(f"Short-term memories: {len(memories)}")

    # 識別 Pattern
    patterns = identify_patterns(memories)
    print(f"Pattern candidates: {len(patterns)}")

    # 識別 Lesson
    lessons = identify_lessons(memories)
    print(f"Lesson candidates: {len(lessons)}")

    # 寫入
    new_patterns = promote_patterns(patterns, dry_run)
    new_lessons = promote_lessons(lessons, dry_run)

    # 更新 wisdom 追蹤檔
    if not dry_run:
        wisdom = load_json(WISDOM_FILE, empty_wisdom)
        wisdom['metadata']['last_aggregated'] = datetime.now().isoformat()
        wisdom['metadata']['sources'] = list(set(wisdom['metadata'].get('sources', []) + ['PS', 'macro', 'scanner']))
        wisdom['insights'].append({
            'timestamp': datetime.now().isoformat(),
            'days': days,
            'memories': len(memories),
            'patterns_promoted': new_patterns,
            'lessons_promoted': new_lessons
        })
        wisdom['insights'] = wisdom['insights'][-50:]  # 保留最近50筆
        save_json(WISDOM_FILE, wisdom)

    print(f"Promoted: {new_patterns} patterns, {new_lessons} lessons")
    return {'patterns': new_patterns, 'lessons': new_lessons}

# ===== 狀態檢查 =====

def check():
    """檢查智慧庫狀態"""
    patterns_data = load_json(PATTERNS_FILE, empty_patterns)
    lessons_data = load_json(LESSONS_FILE, empty_lessons)
    wisdom_data = load_json(WISDOM_FILE, empty_wisdom)

    print("\n=== Accumulated Wisdom Status ===")
    print(f"Patterns: {len(patterns_data.get('patterns', []))}")
    print(f"Lessons: {len(lessons_data.get('lessons', []))}")
    print(f"Wisdom log entries: {len(wisdom_data.get('insights', []))}")

    if patterns_data.get('metadata', {}).get('last_updated'):
        print(f"Last pattern update: {patterns_data['metadata']['last_updated']}")
    if lessons_data.get('metadata', {}).get('last_updated'):
        print(f"Last lesson update: {lessons_data['metadata']['last_updated']}")
    if wisdom_data.get('metadata', {}).get('last_aggregated'):
        print(f"Last aggregation: {wisdom_data['metadata']['last_aggregated']}")

    # 顯示最近 patterns
    patterns = patterns_data.get('patterns', [])
    if patterns:
        print("\nRecent Patterns:")
        for p in patterns[-5:]:
            print(f"  [{p.get('status','?')}] {p.get('name','?')[:50]} | hit={p.get('hit_rate',0):.0%} | occ={p.get('occurrences',0)}")

    # 顯示最近 lessons
    lessons = lessons_data.get('lessons', [])
    if lessons:
        print("\nRecent Lessons:")
        for l in lessons[-5:]:
            print(f"  [{l.get('date','?')}] {l.get('summary','?')[:60]}")

    print("\n=== Done ===")

# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Accumulated Wisdom Manager')
    sub = parser.add_subparsers()

    agg = sub.add_parser('aggregate', help='彙總近期記憶為智慧')
    agg.add_argument('--days', '-d', type=int, default=14)
    agg.add_argument('--dry-run', action='store_true')
    agg.set_defaults(func=lambda a: aggregate(a.days, a.dry_run))

    check_parser = sub.add_parser('check', help='檢查智慧庫狀態')
    check_parser.set_defaults(func=lambda a: check())

    promote = sub.add_parser('promote', help='手動晉升特定記憶')
    promote.add_argument('--id', required=True, help='記憶ID')
    promote.set_defaults(func=lambda a: print(f"Would promote {a.id}"))

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()