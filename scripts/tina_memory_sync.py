# -*- coding: utf-8 -*-
"""
Tina MEMORY.md 每日同步腳本
每日晨間執行：更新 MEMORY.md 持倉、損益、Lesson 狀態
"""
import sys, os, json, sqlite3
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
MEMORY_FILE = Path(r'C:\Users\USER\.openclaw\workspace\MEMORY.md')
LEDGER_FILE = WORKSPACE / 'data' / 'experience_ledger.json'
TRADES_FILE = WORKSPACE / 'teams' / 'leadtrades' / 'leos' / 'leos_trades.json'
LESSONS_DIR = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'lessons'
XP_DB = WORKSPACE / 'data' / 'tina_xp.db'

def get_ledger_summary():
    """讀取經驗簿摘要"""
    if not LEDGER_FILE.exists():
        return {}
    with open(LEDGER_FILE, encoding='utf-8') as f:
        ledger = json.load(f)

    by_team = {}
    for e in ledger:
        team = e.get('team', 'unknown')
        if team not in by_team:
            by_team[team] = {'count': 0, 'symbols': set()}
        by_team[team]['count'] += 1
        by_team[team]['symbols'].add(e.get('symbol', ''))

    return {team: {'count': v['count'], 'symbols': list(v['symbols'])} for team, v in by_team.items()}


def get_open_positions():
    """讀取 Leo 開倉"""
    if not TRADES_FILE.exists():
        return []
    with open(TRADES_FILE, encoding='utf-8') as f:
        data = json.load(f)
    return [t for t in data.get('trades', []) if t.get('status') == 'open']


def get_lessons_count():
    """計算 lessons 數量"""
    wins_dir = LESSONS_DIR / 'wins'
    losses_dir = LESSONS_DIR / 'losses'
    wins_count = len(list(wins_dir.glob('*.md'))) if wins_dir.exists() else 0
    losses_count = len(list(losses_dir.glob('*.md'))) if losses_dir.exists() else 0
    return wins_count, losses_count


def get_xp_status():
    """讀取 XP 等級"""
    if not XP_DB.exists():
        return None, None
    try:
        conn = sqlite3.connect(str(XP_DB))
        c = conn.cursor()
        c.execute("SELECT xp_total FROM xp_log ORDER BY id DESC LIMIT 1")
        r = c.fetchone()
        xp = r[0] if r else 0
        conn.close()
        return xp, '見習'
    except:
        return None, None


def build_daily_update():
    """產出每日更新文字"""
    ledger = get_ledger_summary()
    open_pos = get_open_positions()
    wins, losses = get_lessons_count()
    xp, level = get_xp_status()

    lines = []
    lines.append(f'## 每日大腦更新 {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    lines.append('')
    lines.append('### 持倉狀態')
    if open_pos:
        for t in open_pos[:10]:
            sym = t.get('symbol', '')
            mkt = t.get('market', 'TW')
            entry = t.get('entry_price', 0)
            cur = t.get('current_price', entry)
            pnl_pct = (cur - entry) / entry * 100 if entry else 0
            shares = t.get('shares', 0)
            pnl_abs = (cur - entry) * shares if entry else 0
            lines.append(f'- {mkt}:{sym} — {shares}股 @ ${entry:.0f} → ${cur:.0f} ({pnl_pct:+.1f}%, {pnl_abs:+.0f})')
    else:
        lines.append('- 無開倉')
    lines.append('')
    lines.append('### 經驗簿狀態')
    for team, data in sorted(ledger.items(), key=lambda x: -x[1]['count']):
        syms = ', '.join(sorted(data['symbols'])[:8])
        lines.append(f'- {team}: {data["count"]} 筆記錄（{syms}...）')
    lines.append('')
    lines.append('### Lessons 沉積')
    lines.append(f'- wins/: {wins} 個 lesson')
    lines.append(f'- losses/: {losses} 個 lesson')
    if xp is not None:
        lines.append(f'- XP: {xp:,}（{level}）')
    lines.append('')
    lines.append('_每日同步完成_')
    return '\n'.join(lines)


def append_to_memory(content):
    """寫入 MEMORY.md（插入每日更新區段）"""
    if not MEMORY_FILE.exists():
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'[MEMORY] Created {MEMORY_FILE}')
        return

    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        existing = f.read()

    # 找 Last major update 位置，在其前插入
    marker = 'Last major update:'
    if marker in existing:
        parts = existing.split(marker, 1)
        updated = parts[0] + content + '\n---\n\n' + marker + parts[1]
    else:
        updated = content + '\n\n---\n\n' + existing

    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f'[MEMORY] Updated {MEMORY_FILE}')


def main():
    print(f'Tina MEMORY 每日同步 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print('='*60)

    content = build_daily_update()
    print()
    print(content)
    print()

    append_to_memory(content)
    print()
    print('[OK] MEMORY.md daily sync complete')


if __name__ == '__main__':
    main()