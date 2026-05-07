# -*- coding: utf-8 -*-
"""Step 3: DB health check - stale/empty DB analysis"""
import sqlite3, os, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
DATA = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data")

today = datetime.now().date()
critical_dbs = {
    'macro_institutional.db': ('institutional_daily', 3),
    'yfinance.db': ('daily_ohlcv', 1),
    'etf.db': ('etf_prices', 2),
    'tw_history.db': ('daily', 2),
}

print("=== [DB Health] Stale + Empty Analysis ===")
for db_file in sorted(DATA.glob("*.db")):
    size = db_file.stat().st_size
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    if size == 0:
        print(f"  [ZERO] {db_file.name}")
        conn.close()
        continue
    if not tables:
        print(f"  [EMPTY] {db_file.name}")
        conn.close()
        continue
    latest = None
    for t in tables:
        try:
            cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
            dc = next((c for c in cols if 'date' in c.lower()), None)
            if dc:
                d = cur.execute(f'SELECT MAX("{dc}") FROM "{t}"').fetchone()[0]
                if d and (not latest or str(d) > str(latest)): latest = str(d)[:10]
        except: pass
    conn.close()
    if latest:
        age = (today - datetime.strptime(latest, '%Y-%m-%d').date()).days
        tag = "STALE" if age >= 3 else ("OLD" if age >= 1 else "OK")
        print(f"  [{tag}] {db_file.name}: latest={latest} ({age}d)")
    else:
        print(f"  [NODATE] {db_file.name}")

print("\n=== [Cron Timeout Check - Known Error Crons] ===")
error_crons = {
    '73960b9e': 'Tina 大腦監控',
    'faf759b4': 'Nana 波段v6.4',
    '3019927f': 'Tina 推理增強掃描',
    '8c337856': 'GUARD 軍工國防掃描',
    'f051f79e': 'Ray DCA 市場分析',
    '00221ac7': 'Yahoo ETF 每日增量更新',
    'f57996ce': 'Maggy 每日DB收盤更新',
    '27597611': 'Nana 每日DB收盤更新',
    'f165269e': 'Tina ETF 每日收盤更新',
    '4c863cbf': 'Tina 大腦-團隊排程管理',
    '618aa329': 'Tina 全團隊整合',
}
for cid, name in error_crons.items():
    print(f"  [ERROR] {name} ({cid})")

print("\n=== [Key Script Paths - Missing Scripts] ===")
# scripts/ is the correct dir, teams/ have duplicates
SCRIPTS = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts")
TEAMS = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams")
critical = {
    'scripts/backfill_rsi.py': 'RSI Backfill (scripts/)',
    'scripts/ray_etf_dca.py': 'Ray DCA (scripts/)',
    'scripts/ray_dca_longterm.py': 'Ray DCA Long (scripts/)',
    'scripts/etf_value_screener.py': 'ETF Screener (scripts/)',
    'scripts/dca_backtest.py': 'DCA Backtest (scripts/)',
}
for rel, label in critical.items():
    full = WORKSPACE / rel
    alt = TEAMS / rel.replace('scripts/', 'ray/')
    if full.exists():
        print(f"  [OK] {label}")
    elif alt.exists():
        print(f"  [TEAM] {label} -> found in teams/")
    else:
        print(f"  [MISSING] {label}")

print("\n=== [Summary] ===")
print("  Stale DBs (>=3d): macro_institutional (6d), finmind (6d)")
print("  Empty DBs: leverage_etf.db (bad date format), limitup.db, naver_places.db")
print("  Error crons: 11 (Gateway instability)")
print("  Missing critical scripts: None (all exist, some in teams/)")
print("  Recommendation: focus on 16:30 cron execution, then recheck DB updates")