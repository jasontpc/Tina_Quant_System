# -*- coding: utf-8 -*-
"""
Brain System Dashboard — 全系統狀態單一视图
==========================================
Tina 主腦讀取這個 JSON 就能知道全系統現況。

覆蓋：
1. 短期記憶現況（近7天）
2. 長期記憶現況（patterns、lessons、frameworks）
3. 各 Universe 持仓與觀察名單
4. 記憶攝入速度（成長率）
5. 蒸餾待辦队列
6. 全系統的最後活跃時間

用法：
  python brain_dashboard.py  # 輸出 JSON + 摘要
"""

import sys, json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
ST_DIR = STORES_DIR / 'short_term'
WORK_DIR = STORES_DIR / 'working'
LT_DIR = STORES_DIR / 'long_term'
DASH_FILE = STORES_DIR / 'brain_dashboard.json'

def load_json(fp, default=None):
    if fp.exists():
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default or {}

def save_json(fp, data):
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== 讀取各記憶層 =====

def get_short_term_status(days: int = 7) -> dict:
    """短期記憶現況"""
    today = datetime.now()
    stats = defaultdict(lambda: {'count': 0, 'last': None, 'recent': []})
    total = 0
    high_importance = 0
    
    for d in range(days):
        date = (today - timedelta(days=d)).strftime('%Y%m%d')
        for f in ST_DIR.glob(f'{date}_*.json'):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get('status') != 'active':
                            continue
                        total += 1
                        mtype = item.get('type', 'unknown')
                        stats[mtype]['count'] += 1
                        stats[mtype]['last'] = max(stats[mtype]['last'] or '', item.get('timestamp', ''))
                        if item.get('importance', 5) >= 8:
                            high_importance += 1
                        if d == 0:  # 今日
                            stats[mtype]['recent'].append(item['summary'][:80])
            except:
                pass
    
    return {
        'total': total,
        'high_importance': high_importance,
        'by_type': {k: dict(v) for k, v in stats.items()},
        'days_covered': days
    }

def get_long_term_status() -> dict:
    """長期記憶現況"""
    patterns = load_json(LT_DIR / 'patterns.json', {'patterns': []}).get('patterns', [])
    lessons = load_json(LT_DIR / 'lessons.json', {'lessons': []}).get('lessons', [])
    frameworks = load_json(LT_DIR / 'frameworks.json', {'frameworks': []}).get('frameworks', [])
    
    # Pattern 狀態分佈
    pattern_status = defaultdict(int)
    for p in patterns:
        pattern_status[p.get('status', 'unknown')] += 1
    
    # Lesson 類型分佈
    lesson_types = defaultdict(int)
    for l in lessons:
        lesson_types[l.get('type', 'unknown')] += 1
    
    # 高勝率 Pattern（>=75%）
    high_confidence = [p for p in patterns if p.get('hit_rate', 0) >= 0.75]
    
    return {
        'patterns': {
            'total': len(patterns),
            'by_status': dict(pattern_status),
            'high_confidence': len(high_confidence),
            'avg_hit_rate': round(sum(p.get('hit_rate', 0) for p in patterns) / max(1, len(patterns)), 3) if patterns else 0
        },
        'lessons': {
            'total': len(lessons),
            'by_type': dict(lesson_types)
        },
        'frameworks': {
            'total': len(frameworks)
        }
    }

def get_working_status() -> dict:
    """工作記憶現況"""
    active_ctx = load_json(WORK_DIR / 'active_context.json', {
        'active_positions': [],
        'watchlist': [],
        'alerts': []
    })
    pending = load_json(WORK_DIR / 'pending_decisions.json', {'decisions': []})
    queue = load_json(WORK_DIR / 'memory_queue.json', {'queue': []})
    
    positions = active_ctx.get('active_positions', [])
    watchlist = active_ctx.get('watchlist', [])
    alerts = active_ctx.get('alerts', [])
    
    # 依 universe 分組持仓
    by_universe = defaultdict(list)
    for pos in positions:
        by_universe[pos.get('universe', 'UNKNOWN')].append(pos.get('symbol'))
    
    return {
        'active_positions': {
            'total': len(positions),
            'by_universe': dict(by_universe)
        },
        'watchlist': watchlist[:20],
        'alerts': alerts[:10],
        'pending_decisions': len(pending.get('decisions', [])),
        'memory_queue_size': len(queue.get('queue', []))
    }

def get_distillation_log() -> dict:
    """蒸餾日誌"""
    log = load_json(STORES_DIR / 'distillation_log.json', [])
    if not log:
        return {'recent': [], 'total': 0}
    
    # 最近7天
    recent = []
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    for entry in reversed(log[-30:]):
        if entry.get('timestamp', '') >= cutoff:
            recent.append(entry)
    
    return {
        'recent': recent[-10:],
        'total': len(log)
    }

def get_memory_growth_rate() -> dict:
    """記憶攝入速度（成長率）"""
    today = datetime.now()
    counts_by_day = defaultdict(int)
    
    for d in range(30):
        date = (today - timedelta(days=d)).strftime('%Y%m%d')
        for f in ST_DIR.glob(f'{date}_*.json'):
            try:
                with open(f, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                    items = data if isinstance(data, list) else [data]
                    counts_by_day[date] += len(items)
            except:
                pass
    
    days = sorted(counts_by_day.keys())[-7:]
    recent = [counts_by_day.get(d, 0) for d in days]
    avg_per_day = sum(recent) / max(1, len(recent))
    
    # 對比前7天
    prev_days = [counts_by_day.get((today - timedelta(days=d)).strftime('%Y%m%d'), 0) for d in range(7, 14)]
    prev_avg = sum(prev_days) / max(1, len(prev_days))
    
    growth = (avg_per_day - prev_avg) / max(1, prev_avg) * 100 if prev_avg else 0
    
    return {
        'avg_per_day_7d': round(avg_per_day, 1),
        'prev_avg_7d': round(prev_avg, 1),
        'growth_pct': round(growth, 1),
        'total_last_7d': sum(recent),
        'total_prev_7d': sum(prev_days)
    }

def get_system_last_active() -> dict:
    """各 Job 最後活跃時間"""
    # 從最近修改的檔案推斷
    jobs = [
        ('universe_scanner', BASE_DIR / 'reports'),
        ('short_term', ST_DIR),
        ('long_term_patterns', LT_DIR / 'patterns.json'),
        ('long_term_lessons', LT_DIR / 'lessons.json'),
    ]
    
    last_active = {}
    for name, path in jobs:
        if path.exists():
            if path.is_file():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
            else:
                # 目錄取最新檔案
                files = list(path.glob('*'))
                if files:
                    mtime = max(datetime.fromtimestamp(f.stat().st_mtime) for f in files)
                else:
                    mtime = None
            if mtime:
                last_active[name] = mtime.isoformat()
    
    return last_active

# ===== 主函式 =====

def build_dashboard() -> dict:
    """建構全系統 Dashboard"""
    now = datetime.now()
    
    dashboard = {
        'generated_at': now.isoformat(),
        'short_term': get_short_term_status(days=7),
        'long_term': get_long_term_status(),
        'working': get_working_status(),
        'distillation': get_distillation_log(),
        'growth': get_memory_growth_rate(),
        'system_last_active': get_system_last_active(),
        'health': {
            'total_memory_entries': get_short_term_status(days=30)['total'],
            'long_term_total': (
                get_long_term_status()['patterns']['total'] +
                get_long_term_status()['lessons']['total'] +
                get_long_term_status()['frameworks']['total']
            ),
            'distill_queue_size': get_working_status()['memory_queue_size']
        }
    }
    
    # 健康度評分
    st_total = dashboard['short_term']['total']
    lt_total = dashboard['long_term']['patterns']['total'] + dashboard['long_term']['lessons']['total']
    growth = dashboard['growth']['growth_pct']
    
    score = 50
    if st_total > 20: score += 10
    if st_total > 50: score += 10
    if lt_total > 5: score += 10
    if lt_total > 20: score += 10
    if -20 <= growth <= 50: score += 10  # 合理成長
    
    dashboard['health']['score'] = min(100, score)
    dashboard['health']['label'] = (
        '🟢 Excellent' if score >= 80 else
        '🟡 Good' if score >= 60 else
        '🟠 Fair' if score >= 40 else
        '🔴 Low'
    )
    
    return dashboard

def format_dashboard_summary(dash: dict) -> str:
    """格式化給 Jo 的摘要"""
    st = dash['short_term']
    lt = dash['long_term']
    wk = dash['working']
    gr = dash['growth']
    hl = dash['health']
    
    lines = [
        '🧠 Tina 大腦系統狀態',
        '═' * 40,
        f'記憶健康度：{hl["label"]}（{hl["score"]}/100）',
        '',
        '【短期記憶】',
        f'  總量：{st["total"]} 筆（近7天）',
        f'  高重要性：{st["high_importance"]} 筆',
        f'  成長：+{gr["growth_pct"]:+.1f}%（日均 {gr["avg_per_day_7d"]} → 前週 {gr["prev_avg_7d"]}）',
        '',
        '【長期記憶】',
        f'  Patterns：{lt["patterns"]["total"]} 個（{lt["patterns"].get("high_confidence",0)} 高信心）',
        f'  Lessons：{lt["lessons"]["total"]} 個',
        f'  Frameworks：{lt["frameworks"]["total"]} 個',
        '',
        '【工作記憶】',
        f'  持倉：{wk["active_positions"]["total"]} 檔',
        f'  觀察名單：{len(wk["watchlist"])} 檔',
        f'  警示：{len(wk["alerts"])} 個',
        f'  待決策：{wk["pending_decisions"]} 個',
        '',
        '【蒸餾系統】',
        f'  蒸餾日誌：{dash["distillation"]["total"]} 筆記錄',
        f'  待蒸餾队列：{wk["memory_queue_size"]} 項',
        '═' * 40,
        f'更新：{dash["generated_at"][:19]}',
    ]
    
    return '\n'.join(lines)

if __name__ == '__main__':
    print('Building Brain Dashboard...')
    dash = build_dashboard()
    
    # 寫入 JSON
    save_json(DASH_FILE, dash)
    print(f'Dashboard: {DASH_FILE}')
    
    # 輸出摘要
    summary = format_dashboard_summary(dash)
    print('\n' + summary)
    
    print('\nDONE')