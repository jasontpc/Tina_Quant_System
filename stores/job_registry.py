# -*- coding: utf-8 -*-
"""
Job Memory Profile Registry — 全系統 Isolated Jobs 記憶配置
===========================================================
每個 Isolated Job 的標準配置：標籤、指摽格式、短期記憶寫入格式

目的：
1. 統一所有 Job 的輸出格式
2. 蒸餾系統有稳定的攧取來源
3. Tina 主腦讀取全系統狀態
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
REGISTRY_FILE = STORES_DIR / 'job_registry.json'

# ===== Job Memory Profiles =====

JOB_PROFILES = {

    # === Universe Scanner（已整合 BrainAware）===
    'universe_scanner': {
        'name': 'Universe Scanner',
        'universe': 'MULTI',
        'job_type': 'scanner',
        'frequency': 'weekly',
        'tags': ['scanner', 'value', 'growth', 'momentum', 'revenue'],
        'output_format': 'reports/{universe}/{date}_{strategy}.json',
        'memory_types': ['observation', 'decision', 'metric'],
        'decision_tags': ['buy', 'watch', 'sell'],
        'metrics': ['total_scanned', 'high_quality', 'strategy', 'universe'],
        'signals_per_run': 5,  # Top 5 寫入 decision
        'status': 'active',
        'brain_aware': True
    },

    # === Macro Jobs ===
    'macro_morning': {
        'name': '晨間宏觀快報',
        'universe': 'MULTI',
        'job_type': 'macro',
        'frequency': 'daily',
        'tags': ['macro', 'morning', 'TWII', 'VIX', 'DXY', 'geopolitical'],
        'output_format': 'reports/macro/{date}_morning.json',
        'memory_types': ['observation'],
        'metrics': ['TWII_change', 'VIX', 'DXY', 'yield_10y', 'confidence'],
        'forecast_tags': ['TWII_direction', 'VIX_direction', '台股影響'],
        'status': 'active',
        'brain_aware': False,  # 待整合
        'script': 'macro_data_fetcher.py'
    },

    'macro_afternoon': {
        'name': '盤後宏觀整合報告',
        'universe': 'MULTI',
        'job_type': 'macro',
        'frequency': 'daily',
        'tags': ['macro', 'afternoon', 'TWII', 'VIX', 'geopolitical', 'thematic'],
        'output_format': 'reports/macro/{date}_afternoon.json',
        'memory_types': ['observation'],
        'metrics': ['TWII_close', 'VIX', 'yield_curve', 'thematic_trends'],
        'status': 'active',
        'brain_aware': False,
        'script': 'macro_data_fetcher.py'
    },

    # === 台股 Jobs ===
    'nana_v68': {
        'name': 'Nana 波段v6.4',
        'universe': 'TW',
        'job_type': 'nana',
        'frequency': 'intraday',
        'schedule': '0 8,10,13,15,17 * * 1-5',
        'tags': ['TW', 'nana', '波段', 'RSI', 'MA', 'value'],
        'output_format': 'logs/nana_v68_{timestamp}.json',
        'memory_types': ['decision', 'metric'],
        'decision_tags': ['buy', 'sell', 'hold', 'watch'],
        'metrics': ['signals_total', 'win_rate_estimate', 'positions_active'],
        'signals_per_run': 10,
        'status': 'active',
        'brain_aware': False,
        'script': 'teams/nana/nana_v68.py',
        'framework': 'NANA_BAND_SYSTEM'
    },

    'leo_v65': {
        'name': 'Leo 科技股波段v6.5',
        'universe': 'TW',
        'job_type': 'leo',
        'frequency': 'intraday',
        'schedule': '0 8,11,14,17,21 * * 1-5',
        'tags': ['TW', 'leo', '科技股', 'AI', 'RSI'],
        'output_format': 'logs/leos_v65_{timestamp}.json',
        'memory_types': ['decision', 'metric'],
        'decision_tags': ['buy', 'sell', 'hold', 'watch'],
        'metrics': ['signals_total', 'win_rate_estimate', 'tech_sector_exposure'],
        'signals_per_run': 10,
        'status': 'active',
        'brain_aware': False,
        'script': 'teams/leadtrades/leos/leos_v65.py',
        'framework': 'LEO_AI_CHAIN'
    },

    # === 資料庫更新 Jobs ===
    'daily_db_update': {
        'name': '每日DB收盤更新',
        'universe': 'MULTI',
        'job_type': 'db',
        'frequency': 'daily',
        'schedule': '30 16 * * 1-5',
        'tags': ['db', 'update', 'TW', 'US', 'closing'],
        'memory_types': ['metric'],
        'metrics': ['symbols_updated', 'total_rows', 'new_records'],
        'status': 'active',
        'brain_aware': False,
        'script': 'scripts/daily_db_update.py'
    },

    'etf_daily_update': {
        'name': 'ETF 每日收盤更新',
        'universe': 'MULTI',
        'job_type': 'etf',
        'frequency': 'daily',
        'schedule': '35 16 * * 1-5',
        'tags': ['etf', 'update', 'TW', 'US'],
        'memory_types': ['metric'],
        'metrics': ['etfs_updated', 'total_records'],
        'status': 'active',
        'brain_aware': False,
        'script': 'scripts/etf_daily_update.py'
    },

    'tina_auto_learner': {
        'name': 'Tina 自動學習擴充DB',
        'universe': 'MULTI',
        'job_type': 'learner',
        'frequency': 'daily',
        'schedule': '0 17 * * 1-5',
        'tags': ['learn', 'expand', 'db'],
        'memory_types': ['lesson', 'metric'],
        'metrics': ['symbols_added', 'data_quality', 'learning_actions'],
        'status': 'active',
        'brain_aware': False,
        'script': 'scripts/tina_auto_learner.py'
    },

    # === 蒸餾 Jobs（記憶系統內部）===
    'daily_light_distill': {
        'name': '每日輕度蒸餾',
        'universe': 'MEMORY',
        'job_type': 'distill',
        'frequency': 'daily',
        'schedule': '0 20 * * *',
        'tags': ['distill', 'short_term', 'cleanup'],
        'memory_types': ['metric'],  # 寫入蒸餾結果
        'metrics': ['short_term_total', 'cleaned', 'preserved'],
        'status': 'active',
        'brain_aware': False,
        'script': 'stores/memory_distiller.py'
    },

    'weekly_medium_distill': {
        'name': '每週中度蒸餾',
        'universe': 'MEMORY',
        'job_type': 'distill',
        'frequency': 'weekly',
        'schedule': '0 18 * * 5',
        'tags': ['distill', 'promotion', 'pattern', 'lesson'],
        'memory_types': ['pattern', 'lesson'],
        'metrics': ['promotions', 'patterns_total', 'lessons_total'],
        'status': 'active',
        'brain_aware': False,
        'script': 'stores/memory_distiller.py'
    },

    'monthly_deep_distill': {
        'name': '月度深度蒸餾',
        'universe': 'MEMORY',
        'job_type': 'distill',
        'frequency': 'monthly',
        'schedule': '0 22 * * 0',
        'tags': ['distill', 'deep', 'framework', 'decay'],
        'memory_types': ['framework_change', 'pattern'],
        'metrics': ['patterns_decayed', 'patterns_confirmed', 'frameworks_updated'],
        'status': 'active',
        'brain_aware': False,
        'script': 'stores/memory_distiller.py'
    },

    'weekly_brain_distill': {
        'name': '每週大腦蒸餾',
        'universe': 'MEMORY',
        'job_type': 'distill',
        'frequency': 'weekly',
        'schedule': '0 10 * * 0',
        'tags': ['distill', 'brain', 'decision_patterns', 'macro'],
        'memory_types': ['lesson', 'framework_change'],
        'metrics': ['decision_patterns_updated', 'macro_lessons'],
        'status': 'active',
        'brain_aware': False,
        'script': None  # Agent 直接執行
    },

    # === 風控/系統 Jobs ===
    'risk_check': {
        'name': '風控檢查',
        'universe': 'MULTI',
        'job_type': 'risk',
        'frequency': 'hourly',
        'tags': ['risk', 'stop_loss', 'RSI', 'holding_days'],
        'memory_types': ['lesson', 'alert'],
        'metrics': ['positions_checked', 'violations', 'alerts'],
        'status': 'active',
        'brain_aware': False,
        'script': None  # Agent 直接執行
    },

    'autonomous_decision': {
        'name': '自主決策五大層',
        'universe': 'MULTI',
        'job_type': 'decision',
        'frequency': 'hourly',
        'tags': ['autonomous', 'decision', 'layer'],
        'memory_types': ['decision', 'observation'],
        'metrics': ['decisions_made', 'confidence'],
        'status': 'active',
        'brain_aware': False,
        'script': None
    },

    # === 晨間 Macro Jobs ===
    'morning_db_snapshot': {
        'name': '晨間資料庫快照',
        'universe': 'MULTI',
        'job_type': 'snapshot',
        'frequency': 'daily',
        'schedule': '0 7 * * 1-5',
        'tags': ['morning', 'snapshot', 'TWII', 'VIX'],
        'memory_types': ['observation', 'metric'],
        'metrics': ['symbols_snapshot', 'prev_close_available'],
        'status': 'active',
        'brain_aware': False,
        'script': 'macro_data_fetcher.py'
    },
}

def get_all_profiles() -> Dict:
    """回傳所有 Job Profiles"""
    return JOB_PROFILES

def get_profile(job_name: str) -> Dict:
    """取得特定 Job Profile"""
    return JOB_PROFILES.get(job_name, {})

def get_jobs_by_type(job_type: str) -> List[str]:
    """依 job_type 過濾"""
    return [k for k, v in JOB_PROFILES.items() if v.get('job_type') == job_type]

def get_jobs_by_tag(tag: str) -> List[str]:
    """依 tag 過濾"""
    return [k for k, v in JOB_PROFILES.items() if tag in v.get('tags', [])]

def get_brain_aware_jobs() -> List[str]:
    """回傳已整合 BrainAware 的 Jobs"""
    return [k for k, v in JOB_PROFILES.items() if v.get('brain_aware')]

def get_pending_brain_aware_jobs() -> List[str]:
    """回傳尚未整合 BrainAware 的 Jobs"""
    return [k for k, v in JOB_PROFILES.items() if not v.get('brain_aware')]

def save_registry():
    """寫入 Registry 檔"""
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
        json.dump({'profiles': JOB_PROFILES, 'updated': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    save_registry()
    print(f'=== Job Memory Profile Registry ===')
    print(f'Total jobs: {len(JOB_PROFILES)}')
    print(f'Brain-aware: {len(get_brain_aware_jobs())}')
    print(f'Pending: {len(get_pending_brain_aware_jobs())}')
    print()
    print('By type:')
    for jtype in set(v['job_type'] for v in JOB_PROFILES.values()):
        jobs = get_jobs_by_type(jtype)
        print(f'  {jtype}: {len(jobs)} jobs')
    print()
    print('Pending brain-aware:')
    for job in get_pending_brain_aware_jobs():
        print(f'  - {job}: {JOB_PROFILES[job]["script"] or "agent"}')