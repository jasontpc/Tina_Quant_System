"""
Tina Brain Evolution Report Generator
=====================================
Proactive trigger conditions:
1. System idle > 2 hours
2. Experience log has > 3 unsummarized records
"""

import os
import sys
from datetime import datetime, timedelta

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
sys.path.insert(0, WORKSPACE)

from scripts.tina_memory_manager import (
    get_recent_reflections,
    get_recent_context,
    get_stock_experience,
    save_proactive_action,
    get_pending_proactive,
    mark_proactive_delivered
)

def generate_evolution_report():
    """Generate brain evolution report"""
    
    print('='*60)
    print('Tina Brain Evolution Report')
    print('='*60)
    print()
    
    # Get recent 48h reflections
    reflections = get_recent_reflections(hours=48)
    
    # Get recent 24h dialogs
    recent = get_recent_context(hours=24)
    
    print(f'Stats:')
    print(f'  - Reflections: {len(reflections)}')
    print(f'  - Dialogs: {len(recent)}')
    print()
    
    if len(reflections) < 3:
        print('[SKIP] Less than 3 reflections, skip')
        return None
    
    # Build report
    report = []
    report.append('Tina Brain Evolution Report')
    report.append('='*30)
    report.append(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    report.append('')
    report.append('Lessons learned in 48h:')
    report.append('')
    
    # Group by stock
    stock_lessons = {}
    system_lessons = []
    
    for ref in reflections:
        ts, sid, rtext, new_rule, mood = ref
        if sid:
            if sid not in stock_lessons:
                stock_lessons[sid] = []
            stock_lessons[sid].append({
                'text': rtext,
                'rule': new_rule,
                'mood': mood
            })
        else:
            system_lessons.append({
                'text': rtext,
                'rule': new_rule
            })
    
    # Stock lessons
    if stock_lessons:
        report.append('Stock Analysis:')
        for stock_id, lessons in stock_lessons.items():
            report.append(f'  {stock_id}:')
            for lesson in lessons:
                report.append(f'    - {lesson["text"]}')
                if lesson['rule']:
                    report.append(f'      Rule: {lesson["rule"]}')
            report.append('')
    
    # System lessons
    if system_lessons:
        report.append('System Optimization:')
        for lesson in system_lessons:
            report.append(f'  - {lesson["text"]}')
            if lesson['rule']:
                report.append(f'    Rule: {lesson["rule"]}')
        report.append('')
    
    # Recent dialogs
    if recent:
        report.append('Recent Dialogs:')
        stocks_mentioned = set([r[3] for r in recent if r[3]])
        if stocks_mentioned:
            report.append(f'  Stocks discussed: {", ".join(stocks_mentioned)}')
        
        actions = set([r[4] for r in recent if r[4]])
        if actions:
            report.append(f'  Actions taken: {", ".join(actions)}')
        report.append('')
    
    # Summary
    report.append('-'*30)
    report.append(f'Stats: {len(reflections)} reflections / {len(recent)} dialogs')
    report.append('')
    report.append('Master, here is what I learned in 48h.')
    report.append('Available for report anytime.')
    report.append('')
    report.append('Tina v3.12 evolving...')
    
    full_report = '\n'.join(report)
    
    # Save as pending action
    action_id = save_proactive_action('brain_evolution_report', full_report)
    
    print('[OK] Report generated')
    print(f'    Action ID: {action_id}')
    print()
    print(full_report)
    
    return full_report

# Proactive check
def check_and_generate():
    """Check and generate report"""
    
    # Check pending
    pending = get_pending_proactive()
    
    if pending:
        print(f'[INFO] {len(pending)} pending actions')
        for p in pending:
            print(f'  - ID:{p[0]} {p[2]}: {p[3][:50]}...')
        return pending
    
    # Check trigger conditions
    reflections = get_recent_reflections(hours=48)
    
    if len(reflections) >= 3:
        print('[TRIGGER] Reflections >= 3, generating report')
        return generate_evolution_report()
    else:
        print(f'[SKIP] Only {len(reflections)} reflections (need >= 3)')
        return None

if __name__ == '__main__':
    check_and_generate()