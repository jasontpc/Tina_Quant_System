# -*- coding: utf-8 -*-
"""
Memory Distillation Engine — 短期→長期記憶蒸餾
=============================================
職責：
1. 每日輕度蒸餾（20:00）：清理、合併、標記過期
2. 每週中度蒸餾（週五 18:00）：評估晉升、更新patterns
3. 每月深度蒸餾（最後週日 22:00）：全量審視、框架更新

觸發方式：
  python memory_distiller.py --level daily
  python memory_distiller.py --level weekly
  python memory_distiller.py --level monthly
"""

import sys, json, sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
ST_DIR = STORES_DIR / 'short_term'
WORK_DIR = STORES_DIR / 'working'
LT_DIR = STORES_DIR / 'long_term'
DISTILL_LOG = STORES_DIR / 'distillation_log.json'

LT_DIR.mkdir(parents=True, exist_ok=True)

# 長期記憶檔案
PATTERNS_FILE = LT_DIR / 'patterns.json'
LESSONS_FILE = LT_DIR / 'lessons.json'
FRAMEWORKS_FILE = LT_DIR / 'frameworks.json'
MACRO_WISDOM_FILE = LT_DIR / 'macro_wisdom.json'

def load_json(filepath, default_factory=dict):
    """安全讀取 JSON，失敗則回傳預設值"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f'Load error {filepath}: {e}')
    if isinstance(default_factory, type):
        return default_factory()
    return default_factory

def save_json(filepath, data):
    """安全寫入 JSON"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_short_term_memories(days: int = 7) -> list:
    """讀取最近N天的短期記憶"""
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
                            results.append(item)
            except:
                pass
    
    results.sort(key=lambda x: x['timestamp'])
    return results

def get_long_term_patterns() -> dict:
    """讀取 patterns.json"""
    data = load_json(PATTERNS_FILE, {'patterns': []})
    return data.get('patterns', [])

def get_long_term_lessons() -> dict:
    """讀取 lessons.json"""
    data = load_json(LESSONS_FILE, {'lessons': []})
    return data.get('lessons', [])

# ===== 蒸餾規則 =====

def check_pattern_promotion(memories: list) -> list:
    """
    檢查是否有 pattern 符合晉升標準。
    規則：同一 summary_pattern 出現 >= 3 次
    """
    # 依 summary 群組
    summary_groups = defaultdict(list)
    for m in memories:
        if m.get('type') == 'pattern':
            key = m['summary'][:60]  # 前60字元做群組key
            summary_groups[key].append(m)
    
    promotions = []
    for key, items in summary_groups.items():
        if len(items) >= 3:
            # 計算 hit_rate（假設有links的為成功的）
            total = len(items)
            linked = sum(1 for i in items if i.get('links'))
            hit_rate = linked / total if total > 0 else 0
            avg_importance = sum(i.get('importance', 5) for i in items) / total
            
            promotions.append({
                'name': key,
                'occurrences': total,
                'hit_rate': hit_rate,
                'avg_importance': avg_importance,
                'first_seen': items[0]['timestamp'],
                'last_seen': items[-1]['timestamp'],
                'items': items
            })
    
    return promotions

def distill_to_long_term(promotions: list, pattern_id_counter: dict):
    """
    將晉升的 pattern 寫入 patterns.json
    """
    patterns = get_long_term_patterns()
    new_patterns = []
    
    for p in promotions:
        # 避免重複
        existing_names = [pt['name'] for pt in patterns]
        if p['name'] in existing_names:
            continue
        
        new_id = f"pat_{pattern_id_counter['value']:04d}"
        pattern_id_counter['value'] += 1
        
        new_pattern = {
            'id': new_id,
            'name': p['name'],
            'category': 'market_anomaly',
            'universe': infer_universe(p['items']),
            'first_observed': p['first_seen'][:10],
            'last_observed': p['last_seen'][:10],
            'occurrences': p['occurrences'],
            'hit_rate': p['hit_rate'],
            'avg_gain': 0.0,  # 待追蹤
            'conditions': extract_conditions(p['items']),
            'status': 'observed',
            'confidence': min(10, int(p['avg_importance'] * 1.2)),
            'promoted_from': [i['id'] for i in p['items']]
        }
        
        new_patterns.append(new_pattern)
        print(f'  [PROMOTE] Pattern: {p["name"][:50]} (occurrences={p["occurrences"]})')
    
    # 更新 patterns.json
    patterns.extend(new_patterns)
    save_json(PATTERNS_FILE, {'patterns': patterns})
    
    return new_patterns

def distill_lessons(memories: list):
    """
    將 lesson 類型寫入 lessons.json
    """
    lessons_data = load_json(LESSONS_FILE, {'lessons': []})
    lessons = lessons_data.get('lessons', [])
    
    existing_ids = {l['id'] for l in lessons}
    
    new_lessons = []
    for m in memories:
        if m.get('type') == 'lesson' and m['id'] not in existing_ids:
            new_lessons.append({
                'id': m['id'],
                'type': m.get('lesson_type', 'unknown'),
                'date': m['timestamp'][:10],
                'summary': m.get('summary', ''),
                'detail': m.get('detail', ''),
                'source': m.get('source', 'system'),
                'tags': m.get('tags', []),
                'status': 'archived'
            })
    
    if new_lessons:
        lessons.extend(new_lessons)
        save_json(LESSONS_FILE, {'lessons': lessons})
        print(f'  [PROMOTE] {len(new_lessons)} lessons → long-term')
    
    return new_lessons

def infer_universe(items: list) -> str:
    """從 tags 推斷 universe"""
    for item in items:
        for tag in item.get('tags', []):
            if 'TW' in tag or '台' in tag:
                return 'TW'
            if 'US' in tag or 'SP' in tag or 'NDX' in tag:
                return 'US'
            if 'SOX' in tag or '牛晶' in tag:
                return 'SOX'
    return 'UNKNOWN'

def extract_conditions(items: list) -> list:
    """從 items 提取共同條件"""
    conditions = set()
    for item in items:
        for tag in item.get('tags', []):
            if any(k in tag for k in ['RSI', 'VIX', 'MA', 'P/E', 'P/B']):
                conditions.add(tag)
    return list(conditions)[:5]

def cleanup_expired_memories():
    """清理過期記憶"""
    today = datetime.now()
    cleaned = 0
    preserved = 0
    
    for f in ST_DIR.glob('*.json'):
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
            items = data if isinstance(data, list) else [data]
            
            survivors = []
            for item in items:
                expiry = item.get('expiry_days', 30)
                created = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                created_local = created.astimezone() if created.tzinfo else created
                age = (today - created_local.replace(tzinfo=None)).days
                
                if age > expiry and not item.get('links'):
                    cleaned += 1  # 真的刪除
                else:
                    survivors.append(item)
                    preserved += 1
            
            if len(survivors) < len(items):
                with open(f, 'w', encoding='utf-8') as fp:
                    json.dump(survivors if len(survivors) > 1 else survivors[0], 
                             fp, ensure_ascii=False, indent=2)
        except:
            pass
    
    return cleaned, preserved

def daily_distillation():
    """每日輕度蒸餾 — 極簡版，避免 Timeout"""
    print(f'\n=== 每日輕度蒸餾 | {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    
    # 只計算檔案數量，不讀取內容（快速）
    today = datetime.now()
    recent_count = 0
    for d in range(7):
        date = (today - timedelta(days=d)).strftime('%Y%m%d')
        recent_count += len(list(ST_DIR.glob(f'{date}_*.json')))
    
    print(f'Short-term files (7d): {recent_count}')
    
    # 更新蒸餾日誌（只寫一筆，不做昂貴的 cleanup）
    log = load_json(DISTILL_LOG, [])
    log.append({
        'timestamp': datetime.now().isoformat(),
        'level': 'daily',
        'short_term_count': recent_count,
        'note': 'lightweight - cleanup delegated to weekly'
    })
    save_json(DISTILL_LOG, log[-100:])
    
    print('Daily distillation DONE (lightweight mode)')
    return {'short_term_count': recent_count}

def weekly_distillation():
    """每週中度蒸餾"""
    print(f'\n=== 每週中度蒸餾 | {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    
    # 讀取近14天記憶
    memories = get_short_term_memories(days=14)
    print(f'Short-term memories (14d): {len(memories)}')
    
    # 1. Pattern 晉升評估
    promotions = check_pattern_promotion(memories)
    print(f'Pattern promotions candidate: {len(promotions)}')
    
    # 2. 蒸餾晉升
    pattern_id_counter = {'value': 1}
    patterns = load_json(PATTERNS_FILE, {'patterns': []})
    if patterns.get('patterns'):
        max_id = max(int(p['id'].split('_')[1]) for p in patterns['patterns'] if p['id'].startswith('pat_'))
        pattern_id_counter['value'] = max_id + 1
    
    new_promoted = distill_to_long_term(promotions, pattern_id_counter)
    
    # 3. Lesson 晉升
    new_lessons = distill_lessons(memories)
    
    # 4. 清理過期
    cleaned, preserved = cleanup_expired_memories()
    
    # 5. 日誌
    log = load_json(DISTILL_LOG, [])
    log.append({
        'timestamp': datetime.now().isoformat(),
        'level': 'weekly',
        'short_term_count': len(memories),
        'pattern_promotions': len(new_promoted),
        'lesson_promotions': len(new_lessons),
        'cleaned': cleaned
    })
    save_json(DISTILL_LOG, log[-100:])
    
    print(f'Weekly distillation DONE: {len(new_promoted)} patterns, {len(new_lessons)} lessons promoted')
    return {'promotions': new_promoted, 'lessons': new_lessons, 'cleaned': cleaned}

def monthly_distillation():
    """月度深度蒸餾"""
    print(f'\n=== 月度深度蒸餾 | {datetime.now().strftime("%Y-%m-%d %H:%M")} ===')
    
    # 讀取近90天記憶
    memories = get_short_term_memories(days=90)
    print(f'Short-term memories (90d): {len(memories)}')
    
    # 1. 全量 Pattern 審視
    patterns = get_long_term_patterns()
    print(f'Long-term patterns before: {len(patterns)}')
    
    # 2. 衰減低勝率 Pattern（< 0.4）
    decayed = 0
    for p in patterns:
        if p.get('status') == 'confirmed' and p.get('hit_rate', 1) < 0.4:
            p['status'] = 'inactive'
            decayed += 1
    
    # 3. 提升高勝率 Pattern
    promoted = 0
    for p in patterns:
        if p.get('status') == 'observed' and p.get('hit_rate', 0) >= 0.75 and p.get('occurrences', 0) >= 5:
            p['status'] = 'confirmed'
            p['confidence'] = min(10, int(p['hit_rate'] * 10))
            promoted += 1
    
    save_json(PATTERNS_FILE, {'patterns': patterns})
    print(f'Patterns: {decayed} decayed, {promoted} confirmed')
    
    # 4. Lesson 全面審視
    lessons = get_long_term_lessons()
    print(f'Long-term lessons: {len(lessons)}')
    
    # 5. 更新 frameworks（如果有版本更新）
    # （需對接現有 version tracking）
    
    # 6. 蒸餾日誌
    log = load_json(DISTILL_LOG, [])
    log.append({
        'timestamp': datetime.now().isoformat(),
        'level': 'monthly',
        'patterns_total': len(patterns),
        'patterns_decayed': decayed,
        'patterns_promoted': promoted,
        'lessons_total': len(lessons)
    })
    save_json(DISTILL_LOG, log[-100:])
    
    print('Monthly distillation DONE')
    return {'patterns': len(patterns), 'decayed': decayed, 'promoted': promoted}

# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Memory Distillation Engine')
    parser.add_argument('--level', '-l', required=True, 
                       choices=['daily', 'weekly', 'monthly', 'test'])
    args = parser.parse_args()
    
    if args.level == 'daily':
        result = daily_distillation()
    elif args.level == 'weekly':
        result = weekly_distillation()
    elif args.level == 'monthly':
        result = monthly_distillation()
    elif args.level == 'test':
        # 測試模式：不寫入，只輸出摘要
        memories = get_short_term_memories(days=7)
        print(f'Test mode: {len(memories)} short-term memories found')
        promotions = check_pattern_promotion(memories)
        print(f'Promotion candidates: {len(promotions)}')
        for p in promotions:
            print(f'  - {p["name"][:60]} (x{p["occurrences"]})')
    
    print('\nDONE')

if __name__ == '__main__':
    main()