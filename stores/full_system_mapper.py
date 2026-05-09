# -*- coding: utf-8 -*-
"""
Full System Script-DB-Memory Map
=================================
全系統所有腳本、資料庫、記憶系統的完整對應圖。

目標：每個腳本 × 操作的 DB × 寫入的記憶類型 都有完整記錄。
可用於：
1. 系統影響分析（改一個腳本影響哪些記憶）
2. 蒸餾時知道每筆記憶來自哪個腳本
3. 系統健康度評估（哪些 DB 缺少 Script 維護）

更新：python full_system_mapper.py
"""

import sqlite3, json, os, subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
STORES_DIR = BASE_DIR / 'stores'
SCRIPT_DIR = BASE_DIR  # scripts/, teams/, stores/

# ===== 完整腳本元資料（手動維護）=====
SCRIPT_METADATA = {
    # === Cron Jobs 活躍腳本 ===
    'daily_db_update.py': {
        'cron': '30 16 * * 1-5',
        'type': 'db',
        'universe': 'MULTI',
        'description': '每日收盤 DB 更新（yfinance + tw_history）',
        'dbs_write': ['yfinance.db', 'tw_history.db'],
        'memory_type': 'metric',
        'memory_tags': ['db', 'update', 'daily'],
        'brain_aware': False,
    },
    'etf_daily_update.py': {
        'cron': '35 16 * * 1-5',
        'type': 'etf',
        'universe': 'MULTI',
        'description': 'ETF 每日收盤更新',
        'dbs_write': ['etf.db', 'sherry_etf.db'],
        'memory_type': 'metric',
        'memory_tags': ['etf', 'update'],
        'brain_aware': False,
    },
    'tina_auto_learner.py': {
        'cron': '0 17 * * 1-5',
        'type': 'learner',
        'universe': 'MULTI',
        'description': '自動學習擴充 DB',
        'dbs_write': ['yfinance.db', 'tw_stock_registry.db'],
        'memory_type': 'lesson',
        'memory_tags': ['learn', 'expand'],
        'brain_aware': False,
    },
    'nana_v68.py': {
        'cron': '0 8,10,13,15,17 * * 1-5',
        'type': 'nana',
        'universe': 'TW',
        'description': 'Nana 波段掃描（v6.8）',
        'dbs_read': ['yfinance.db', 'tw_history.db'],
        'dbs_write': [],
        'output': 'logs/nana_v68_{date}.json',
        'memory_type': 'decision',
        'memory_tags': ['nana', 'band', 'TW'],
        'brain_aware': False,
    },
    'leos_v65.py': {
        'cron': '0 8,11,14,17,21 * * 1-5',
        'type': 'leo',
        'universe': 'TW',
        'description': 'Leo 科技股波段（v6.5）',
        'dbs_read': ['yfinance.db', 'us_history.db'],
        'dbs_write': ['sherry_sim_trades.db'],
        'output': 'logs/leos_v65_{date}.json',
        'memory_type': 'decision',
        'memory_tags': ['leo', 'tech', 'TW'],
        'brain_aware': False,
    },
    'universe_scanner.py': {
        'cron': 'Sun 10:00 (TW500), Mon (SP500), etc',
        'type': 'scanner',
        'universe': 'MULTI',
        'description': 'Universe 多策略掃描（價值/成長/動能）',
        'dbs_read': ['yfinance.db'],
        'dbs_write': [],
        'output': 'reports/{universe}/{date}_{strategy}.json',
        'memory_type': 'decision',
        'memory_tags': ['scanner', 'universe'],
        'brain_aware': True,  # ✅ 已整合
    },
    'macro_data_fetcher.py': {
        'cron': '07:30 (morning), 14:00 (afternoon)',
        'type': 'macro',
        'universe': 'MULTI',
        'description': 'Macro 數據抓取（yfinance + Tavily）',
        'dbs_read': ['yfinance.db'],
        'dbs_write': [],
        'output': 'reports/macro/{date}_{type}.json',
        'memory_type': 'observation',
        'memory_tags': ['macro', 'TWII', 'VIX'],
        'brain_aware': False,
    },
    'memory_distiller.py': {
        'cron': 'daily 20:00 / weekly Fri 18:00 / monthly last Sun 22:00',
        'type': 'distill',
        'universe': 'MEMORY',
        'description': '記憶蒸餾引擎',
        'dbs_read': [],
        'dbs_write': ['stores/long_term/patterns.json', 'stores/long_term/lessons.json'],
        'memory_type': 'pattern',
        'memory_tags': ['distill', 'memory'],
        'brain_aware': False,
    },
    'brain_dashboard.py': {
        'cron': None,
        'type': 'dashboard',
        'universe': 'MEMORY',
        'description': '全系統 Brain Dashboard',
        'dbs_read': ['all_dbs'],
        'dbs_write': ['stores/brain_dashboard.json'],
        'memory_type': 'metric',
        'memory_tags': ['dashboard', 'system'],
        'brain_aware': False,
    },

    # === 一次性腳本（無 Cron，但可能被手動執行）===
    'update_us_history.py': {
        'cron': None,
        'type': 'db_build',
        'universe': 'US',
        'description': '建立美股歷史資料庫',
        'dbs_write': ['us_history.db'],
        'memory_type': 'lesson',
        'memory_tags': ['db', 'build', 'us'],
        'brain_aware': False,
    },
    'build_tw_history.py': {
        'cron': None,
        'type': 'db_build',
        'universe': 'TW',
        'description': '建立台股歷史資料庫',
        'dbs_write': ['tw_history.db'],
        'memory_type': 'lesson',
        'memory_tags': ['db', 'build', 'tw'],
        'brain_aware': False,
    },
    'build_us_fundamental.py': {
        'cron': None,
        'type': 'fundamental',
        'universe': 'US',
        'description': '建立美股基本面資料庫',
        'dbs_write': ['us_history.db', 'yfinance.db'],
        'memory_type': 'metric',
        'memory_tags': ['fundamental', 'us'],
        'brain_aware': False,
    },
    'build_rsi_db.py': {
        'cron': None,
        'type': 'technical',
        'universe': 'TW',
        'description': '建立 RSI 驗證資料庫',
        'dbs_write': ['data/rsi_verification.db'],
        'memory_type': 'metric',
        'memory_tags': ['rsi', 'technical', 'tw'],
        'brain_aware': False,
    },
    'master_backtest.py': {
        'cron': None,
        'type': 'backtest',
        'universe': 'MULTI',
        'description': '主回測系統',
        'dbs_write': ['master_backtest.db'],
        'memory_type': 'metric',
        'memory_tags': ['backtest', 'system'],
        'brain_aware': False,
    },
    'us_backtest.py': {
        'cron': None,
        'type': 'backtest',
        'universe': 'US',
        'description': '美股回測系統',
        'dbs_write': ['us_sim_trades.db'],
        'memory_type': 'metric',
        'memory_tags': ['backtest', 'us'],
        'brain_aware': False,
    },
    'daily_premarket.py': {
        'cron': '0 7 * * 1-5',  # 可能在用
        'type': 'morning',
        'universe': 'MULTI',
        'description': '晨間市場快報',
        'dbs_read': ['yfinance.db', 'tw_history.db'],
        'dbs_write': [],
        'memory_type': 'observation',
        'memory_tags': ['morning', 'premarket'],
        'brain_aware': False,
    },
    'risk_check.py': {
        'cron': None,
        'type': 'risk',
        'universe': 'MULTI',
        'description': '風險檢查',
        'dbs_read': ['sherry_sim_trades.db', 'us_sim_trades.db'],
        'dbs_write': [],
        'memory_type': 'lesson',
        'memory_tags': ['risk', 'check'],
        'brain_aware': False,
    },
    'global_market.py': {
        'cron': None,
        'type': 'macro',
        'universe': 'MULTI',
        'description': '全球市場數據',
        'dbs_read': ['yfinance.db', 'macro_institutional.db'],
        'dbs_write': [],
        'memory_type': 'observation',
        'memory_tags': ['global', 'macro', 'market'],
        'brain_aware': False,
    },
    'institutional_flow.py': {
        'cron': None,
        'type': 'institutional',
        'universe': 'TW',
        'description': '法人流向追蹤',
        'dbs_write': ['macro_institutional.db'],
        'memory_type': 'observation',
        'memory_tags': ['institutional', 'tw'],
        'brain_aware': False,
    },
    'finmind_tw.py': {
        'cron': None,
        'type': 'db',
        'universe': 'TW',
        'description': 'FinMind 台股資料抓取',
        'dbs_write': ['finmind.db'],
        'memory_type': 'metric',
        'memory_tags': ['finmind', 'tw'],
        'brain_aware': False,
    },
}

def build_full_map() -> dict:
    """建構完整對應圖"""
    
    # DB → Scripts 映射
    db_to_scripts = defaultdict(list)
    script_to_db = defaultdict(lambda: {'read': [], 'write': []})
    
    for script, meta in SCRIPT_METADATA.items():
        for db in meta.get('dbs_read', []):
            script_to_db[script]['read'].append(db)
            if db not in db_to_scripts:
                db_to_scripts[db] = {'read': [], 'write': []}
            db_to_scripts[db]['read'].append(script)
        for db in meta.get('dbs_write', []):
            script_to_db[script]['write'].append(db)
            if db not in db_to_scripts:
                db_to_scripts[db] = {'read': [], 'write': []}
            db_to_scripts[db]['write'].append(script)
    
    # Cron Jobs 統計
    cron_jobs = {s: m for s, m in SCRIPT_METADATA.items() if m.get('cron')}
    active_jobs = {s: m for s, m in cron_jobs.items() if m.get('type') not in ['db_build', 'backtest']}
    
    # Brain-Aware 統計
    brain_aware = {s: m for s, m in SCRIPT_METADATA.items() if m.get('brain_aware')}
    not_brain_aware = {s: m for s, m in SCRIPT_METADATA.items() if not m.get('brain_aware') and m.get('cron')}
    
    # DB 大小與覆蓋
    db_sizes = {}
    for db_file in DATA_DIR.glob('*.db'):
        db_sizes[db_file.name] = round(db_file.stat().st_size / 1e6, 1)
    
    return {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_scripts': len(SCRIPT_METADATA),
            'cron_active': len(active_jobs),
            'brain_aware': len(brain_aware),
            'pending_brain_aware': len(not_brain_aware),
            'total_dbs': len(db_sizes),
        },
        'scripts': SCRIPT_METADATA,
        'script_to_db': dict(script_to_db),
        'db_to_scripts': {k: dict(v) for k, v in db_to_scripts.items()},
        'db_sizes_mb': db_sizes,
        'cron_jobs': cron_jobs,
        'active_jobs': active_jobs,
        'brain_aware_scripts': brain_aware,
        'pending_brain_aware': not_brain_aware,
    }

def format_map_summary(m: dict) -> str:
    """格式化地圖摘要"""
    s = m['summary']
    lines = [
        '📊 全系統腳本 × DB × 記憶對應圖',
        '═' * 40,
        f'腳本總數：{s["total_scripts"]} 個',
        f'活躍 Cron Jobs：{s["cron_active"]} 個',
        f'已整合 BrainAware：{s["brain_aware"]} 個',
        f'待整合（活躍 Job）：{s["pending_brain_aware"]} 個',
        f'資料庫總數：{s["total_dbs"]} 個',
        '',
        '【腳本分類】',
    ]
    
    by_type = defaultdict(list)
    for script, meta in m['scripts'].items():
        by_type[meta['type']].append(script)
    
    for jtype in sorted(by_type.keys()):
        scripts = by_type[jtype]
        active = sum(1 for s in scripts if m['active_jobs'].get(s))
        brain = sum(1 for s in scripts if m['scripts'][s].get('brain_aware'))
        lines.append(f'  {jtype}: {len(scripts)} 個（{active} 活躍, {brain} 已整合）')
    
    lines.extend(['', '【DB 規模 Top 5】'])
    for db, size in sorted(m['db_sizes_mb'].items(), key=lambda x: -x[1])[:5]:
        scripts_w = m['db_to_scripts'].get(db, {}).get('write', [])
        scripts_r = m['db_to_scripts'].get(db, {}).get('read', [])
        lines.append(f'  {db}: {size}MB | 讀:{len(scripts_r)} 寫:{len(scripts_w)}')
    
    lines.append('')
    lines.append('【待整合腳本（活躍 Cron Jobs）】')
    for script in sorted(m['pending_brain_aware'].keys())[:10]:
        meta = m['pending_brain_aware'][script]
        lines.append(f'  - {script}: {meta.get("cron", "")} ({meta.get("memory_type", "")})')
    
    lines.append('═' * 40)
    return '\n'.join(lines)

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    print('Building Full System Map...')
    m = build_full_map()
    
    # Save JSON
    out_file = STORES_DIR / 'full_system_map.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    print(f'Map saved: {out_file}')
    
    # Print summary
    summary = format_map_summary(m)
    print('\n' + summary)