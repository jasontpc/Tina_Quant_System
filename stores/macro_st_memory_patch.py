# -*- coding: utf-8 -*-
"""
Macro Brain Patch — Macro Jobs 的 Brain-Aware 整合
================================================
職責：
1. Macro Job 完成後自動寫入 short_term (observation)
2. 讀取長期記憶脈絡（相關 Pattern、Lessons）
3. 建立 Macro × 記憶系統 的標準流程

使用方法（在 macro_data_fetcher.py 的 main() 末尾加入）：
  # === Brain-Aware 整合 ===
  try:
      from stores.macro_st_memory_bridge import MacroSTBridge
      bridge = MacroSTBridge()
      # 找到输出的 JSON 檔
      import os
      report_date = datetime.now().strftime('%Y%m%d')
      report_type = 'morning' if args.type == 'morning' else 'afternoon'
      json_path = os.path.join(BASE_DIR, 'reports', 'macro', f'{report_date}_{report_type}.json')
      bridge.write_macro_observation(json_path, job_name=f'{report_type}_macro')
      bridge.write_macro_decision(json_path, action='macro_update', reason='晨間/盤後Macro報告更新', confidence=7)
  except Exception as e:
      print(f'[BrainAware] Macro patch error: {e}')
"""

import sys, json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')

def macro_memory_integration(report_type: str = 'morning') -> str:
    """
    Macro Job 完成後呼叫這個函式。
    讀取 macro JSON → 寫入短期記憶 → 回傳 memory ID
    """
    sys.path.insert(0, str(BASE_DIR / 'stores'))
    
    try:
        from macro_st_bridge import MacroSTBridge
    except ImportError:
        print('[MacroBrain] macro_st_bridge not available')
        return None
    
    bridge = MacroSTBridge()
    
    # 找 Macro JSON
    report_date = datetime.now().strftime('%Y%m%d')
    json_path = BASE_DIR / 'reports' / 'macro' / f'{report_date}_{report_type}.json'
    
    if not json_path.exists():
        print(f'[MacroBrain] JSON not found: {json_path}')
        return None
    
    # 寫入觀測記憶
    obs_id = bridge.write_macro_observation(str(json_path), job_name=f'{report_type}_macro')
    
    # 讀取 Macro JSON 取得預測方向，寫入 decision
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            macro_data = json.load(f)
        
        forecast = macro_data.get('forecast', {})
        direction = forecast.get('direction', 'neutral')
        confidence = macro_data.get('confidence', {})
        overall = confidence.get('overall', 5)
        
        if direction != 'neutral':
            bridge.write_macro_decision(
                str(json_path),
                action=f'macro_{direction}',
                reason=f"TWII 預測方向：{direction}，信心：{overall}/10",
                confidence=overall
            )
    except Exception as e:
        print(f'[MacroBrain] Decision write error: {e}')
    
    return obs_id

def get_macro_brain_summary() -> dict:
    """Macro 專用的記憶脈絡摘要"""
    sys.path.insert(0, str(BASE_DIR / 'stores'))
    
    from brain_aware_executor import BrainAwareExecutor
    
    brain = BrainAwareExecutor(
        job_name='macro_summary',
        universe='MULTI',
        job_type='macro'
    )
    ctx = brain.before_execute()
    
    # 只取 Macro 相關的 patterns 和 lessons
    macro_patterns = [
        p for p in ctx.get('patterns', [])
        if any(tag in p.get('tags', []) for tag in ['macro', 'TWII', 'VIX', 'DXY', 'geopolitical'])
    ]
    macro_lessons = [
        l for l in ctx.get('lessons', [])
        if any(tag in l.get('tags', []) for tag in ['macro', 'geopolitical', 'Fed'])
    ]
    
    return {
        'macro_patterns': macro_patterns,
        'macro_lessons': macro_lessons,
        'recent_macro_observations': len([m for m in ctx.get('short_term_summary', {}).get('by_type', {}).get('observation', {}).get('recent', [])]),
        'active_positions': ctx.get('active_positions', []),
        'watchlist': ctx.get('watchlist', [])
    }

if __name__ == '__main__':
    print('Macro Brain Patch Test')
    print('Usage: call macro_memory_integration("morning") or macro_memory_integration("afternoon")')