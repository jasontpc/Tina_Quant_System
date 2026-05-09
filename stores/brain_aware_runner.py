# -*- coding: utf-8 -*-
"""
Brain-Aware Job Runner — 賦予 Isolated Jobs 記憶能力
====================================================
用法：
  python stores/brain_aware_runner.py --job nana_v68 --results logs/nana_v68_latest.json
  python stores/brain_aware_runner.py --job leo_v65 --results logs/leos_v65_latest.json

職責：
1. 解析 Job 的輸出檔（JSON）
2. 寫入短期記憶（signals + metrics）
3. 讓蒸餾系統能追蹤每次執行的預測品質
"""

import argparse, json, sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
sys.path.insert(0, str(STORES_DIR))
from short_term_writer import write_memory

JOB_PROFILES = {
    'nana_v68': {
        'universe': 'TW',
        'job_type': 'nana',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'rsi', 'score', 'price', 'action'],
        'action_field': 'action',
    },
    'leo_v65': {
        'universe': 'TW',
        'job_type': 'leo',
        'score_field': 'score',
        'signal_fields': ['symbol', 'action', 'price', 'rsi', 'kd_golden', 'entry_signals'],
        'action_field': 'action',
    },
    'macro_review': {
        'universe': 'MULTI',
        'job_type': 'macro',
        'score_field': 'accuracy',
        'signal_fields': ['prediction', 'actual', 'direction', 'geopolitical', 'macro', 'trend', 'twii'],
        'action_field': 'prediction',
    },
    # Universe Scanner jobs
    'sp500_value': {
        'universe': 'US',
        'job_type': 'scanner',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'price', 'score', 'tier'],
        'action_field': 'action',
    },
    'sp500_growth': {
        'universe': 'US',
        'job_type': 'scanner',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'price', 'score', 'tier'],
        'action_field': 'action',
    },
    'ndx_ai': {
        'universe': 'US',
        'job_type': 'scanner',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'price', 'score', 'tier'],
        'action_field': 'action',
    },
    'sox30': {
        'universe': 'US',
        'job_type': 'scanner',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'price', 'score', 'tier'],
        'action_field': 'action',
    },
    'us_etf_hi_div': {
        'universe': 'US',
        'job_type': 'etf',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'price', 'score', 'tier'],
        'action_field': 'action',
    },
    'us_etf_growth': {
        'universe': 'US',
        'job_type': 'etf',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'price', 'score', 'tier'],
        'action_field': 'action',
    },
    'tw_etf_hi_div': {
        'universe': 'TW',
        'job_type': 'etf',
        'score_field': 'score',
        'signal_fields': ['symbol', 'name', 'price', 'score', 'tier'],
        'action_field': 'action',
    },
}

def run(job_name: str, results_file: str = None):
    profile = JOB_PROFILES.get(job_name)
    if not profile:
        print(f'[BrainAware Runner] Unknown job: {job_name}')
        return

    universe = profile['universe']
    job_type = profile['job_type']
    execution_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 嘗試讀取結果檔
    results = []
    if results_file:
        fp = Path(results_file)
        if fp.exists():
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    results = data.get('results', data.get('candidates', data.get('signals', [])))
                elif isinstance(data, list):
                    results = data
                print(f'[BrainAware Runner] {job_name}: loaded {len(results)} results from {fp.name}')
            except Exception as e:
                print(f'[BrainAware Runner] Failed to load {results_file}: {e}')

    # 如果沒有結果檔，嘗試找最新的 log
    if not results:
        log_dir = BASE_DIR / 'logs'
        pattern = f'{job_name}_*.json'
        candidates = list(log_dir.glob(pattern))
        if candidates:
            latest = sorted(candidates, key=lambda x: -x.stat().st_mtime)[0]
            try:
                with open(latest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    results = data.get('results', data.get('candidates', data.get('signals', [])))
                elif isinstance(data, list):
                    results = data
                print(f'[BrainAware Runner] {job_name}: loaded {len(results)} results from {latest.name}')
            except Exception as e:
                print(f'[BrainAware Runner] Failed to load {latest}: {e}')

    memory_ids = []

    # 寫入信號（decision 類型）
    for sig in results[:20]:  # 最多 20 筆
        try:
            action = sig.get(profile['action_field'], sig.get('signal', 'scan'))
            score = sig.get(profile['score_field'], 0)
            importance = int(min(10, score / 50)) if score else 5

            sig_id = write_memory(
                mtype='decision',
                summary=f"{sig.get('symbol','?')} {action} @ ${sig.get('price','?')} — score={score}",
                detail=json.dumps(sig, ensure_ascii=False),
                source=f'{job_type}_job',
                tags=[universe, job_type, sig.get('symbol','?'), action],
                importance=importance,
                links=[],
                expiry_days=60
            )
            memory_ids.append(sig_id)
        except Exception as e:
            print(f'[BrainAware Runner] Failed to write signal: {e}')

    # 寫入執行 summary（observation 類型）
    if results:
        obs_id = write_memory(
            mtype='observation',
            summary=f'{job_name} 執行：{len(results)} 候選個股，最高 score={max(r.get(profile["score_field"],0) for r in results):.0f}',
            detail=json.dumps({
                'job_name': job_name,
                'universe': universe,
                'execution_id': execution_id,
                'total_candidates': len(results),
                'top_score': max(r.get(profile['score_field'], 0) for r in results) if results else 0,
            }, ensure_ascii=False),
            source=f'{job_type}_job',
            tags=[universe, job_type, 'scan', 'execution'],
            importance=6,
            links=[],
            expiry_days=14
        )
        memory_ids.append(obs_id)

    print(f'[BrainAware Runner] {job_name}: wrote {len(memory_ids)} memory entries')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='BrainAware Job Runner')
    parser.add_argument('--job', required=True, choices=list(JOB_PROFILES.keys()) + ['nana_v68', 'leo_v65'])
    parser.add_argument('--results', default=None, help='Path to results JSON file')
    args = parser.parse_args()
    run(args.job, args.results)