# -*- coding: utf-8 -*-
"""
Brain Memory CLI — 輕量命令行工具
================================
功能：
1. Job 執行後寫入短期記憶
2. 讀取長期記憶脈絡
3. 建構 Dashboard

用法：
  # 寫入觀測
  python stores/brain_memory_cli.py write --type observation --summary "..." --source my_job --tags tag1,tag2 --importance 7

  # 讀取脈絡
  python stores/brain_memory_cli.py read --type patterns --universe TW

  # 建構 Dashboard
  python stores/brain_memory_cli.py dashboard

  # Job 執行後自動寫入（封裝 BrainAwareExecutor）
  python stores/brain_memory_cli.py complete --job my_job --universe TW --signals "[{\"symbol\":\"2330\",\"action\":\"buy\"}]"
"""

import sys, json, argparse
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
sys.path.insert(0, str(BASE_DIR / 'stores'))

from brain_aware_executor import BrainAwareExecutor
from short_term_writer import write_memory, get_short_term_summary
from memory_distiller import get_short_term_memories, get_long_term_patterns, get_long_term_lessons
from brain_dashboard import build_dashboard, format_dashboard_summary

def cmd_write(args):
    """寫入短期記憶"""
    tags = args.tags.split(',') if args.tags else []
    mid = write_memory(
        mtype=args.type,
        summary=args.summary,
        detail=args.detail or '',
        source=args.source or 'cli',
        tags=tags,
        importance=args.importance or 5,
        links=[],
        expiry_days=args.expiry or 30
    )
    print(f'Written: {mid}')

def cmd_read(args):
    """讀取長期記憶"""
    if args.type == 'patterns':
        patterns = get_long_term_patterns()
        universe = args.universe
        if universe:
            patterns = [p for p in patterns if p.get('universe') in (universe, 'MULTI')]
        print(f'Patterns: {len(patterns)}')
        for p in patterns[:10]:
            status = p.get('status', '?')
            hr = p.get('hit_rate', 0)
            name = p.get('name', '?')[:50]
            print(f'  [{status}] {name} | hit={hr:.0%}')
    elif args.type == 'lessons':
        lessons = get_long_term_lessons()
        print(f'Lessons: {len(lessons)}')
        for l in lessons[:5]:
            date = l.get('date', '?')
            summary = l.get('summary', '?')[:60]
            print(f'  {date}: {summary}')
    elif args.type == 'summary':
        summary = get_short_term_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        memories = get_short_term_memories(days=args.days or 7)
        print(f'Short-term memories: {len(memories)}')
        for m in memories[-10:]:
            print(f"  {m['timestamp'][:19]} [{m['type']}] {m['summary'][:70]}")

def cmd_complete(args):
    """Job 執行完畢，封裝 BrainAwareExecutor"""
    import ast, json as _json
    
    job_type_map = {
        'nana': 'nana', 'leo': 'leo',
        'macro': 'macro', 'scanner': 'scanner',
        'db': 'db', 'etf': 'etf', 'learner': 'learner'
    }
    
    brain = BrainAwareExecutor(
        job_name=args.job,
        universe=args.universe or 'MULTI',
        job_type=job_type_map.get(args.job, 'scanner')
    )
    
    # 執行前脈絡
    ctx = brain.before_execute()
    
    # 解析 signals
    signals = []
    if args.signals:
        try:
            signals = json.loads(args.signals)
        except:
            signals = []
    
    # 解析 metrics
    metrics = {}
    if args.metrics:
        try:
            metrics = json.loads(args.metrics)
        except:
            metrics = {}
    
    # 執行後寫入
    if signals or metrics or args.summary:
        brain.after_execute(
            success=True,
            summary=args.summary or f'{args.job} 執行完成',
            signals=signals,
            metrics=metrics,
            output_file=args.output
        )
        print(f'Memory written for {args.job}')
    else:
        print(f'No memory to write (add --signals or --metrics or --summary)')

def cmd_dashboard(args):
    """建構並顯示 Dashboard"""
    dash = build_dashboard()
    
    if args.save:
        from brain_dashboard import DASH_FILE
        print(f'Dashboard saved: {DASH_FILE}')
    
    summary = format_dashboard_summary(dash)
    print(summary)

def main():
    parser = argparse.ArgumentParser(description='Tina Brain Memory CLI')
    sub = parser.add_subparsers()
    
    write = sub.add_parser('write', help='寫入短期記憶')
    write.add_argument('--type', '-t', required=True, 
                       choices=['observation', 'decision', 'metric', 'lesson', 'pattern', 'framework_change'])
    write.add_argument('--summary', '-s', required=True)
    write.add_argument('--detail', '-d', default='')
    write.add_argument('--source', default='cli')
    write.add_argument('--tags', '-g', default='')
    write.add_argument('--importance', '-i', type=int, default=5)
    write.add_argument('--expiry', '-e', type=int, default=30)
    write.set_defaults(func=cmd_write)
    
    read = sub.add_parser('read', help='讀取長期記憶')
    read.add_argument('--type', '-t', required=True, choices=['patterns', 'lessons', 'summary', 'memories'])
    read.add_argument('--universe', '-u', default='')
    read.add_argument('--days', '-d', type=int, default=7)
    read.set_defaults(func=cmd_read)
    
    complete = sub.add_parser('complete', help='Job 完成後寫入記憶')
    complete.add_argument('--job', '-j', required=True, help='Job 名稱')
    complete.add_argument('--universe', '-u', default='MULTI')
    complete.add_argument('--signals', default='')
    complete.add_argument('--metrics', '-m', default='')
    complete.add_argument('--summary', default='')
    complete.add_argument('--output', '-o', default='')
    complete.set_defaults(func=cmd_complete)
    
    dash = sub.add_parser('dashboard', help='顯示 Brain Dashboard')
    dash.add_argument('--save', '-s', action='store_true')
    dash.set_defaults(func=cmd_dashboard)
    
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()