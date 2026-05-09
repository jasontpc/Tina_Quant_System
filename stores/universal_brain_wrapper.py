# -*- coding: utf-8 -*-
"""
Universal Brain Wrapper — 雨露同霑，兩行整合任何腳本
===============================================
用法（任何現有 Python 腳本的最後一行加入）：
  from stores.universal_brain_wrapper import brain_wrapper
  brain_wrapperglobals()[__name__].register('job_name', universe='TW', job_type='nana')

  # 然後在腳本任意位置呼叫：
  brain.log(signals=[...], metrics={...}, summary='...')

或者，直接在 crontab job 的 message 末尾加入（推薦）：
  python -c "from stores.brain_memory_cli import cmd_complete; \
    cmd_complete(argparse.Namespace(job='nana_v68', universe='TW', signals='[...json...]', metrics='{}', summary='', output=''))"

這是隔絕層：不改變原有腳本邏輯，只在外層包記憶寫入。
"""

import sys, json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
sys.path.insert(0, str(BASE_DIR / 'stores'))

class UniversalBrainWrapper:
    """
    通用大腦感知包裝器。
    任何腳本只需：
      from universal_brain_wrapper import brain
      brain.register('my_job', universe='TW', job_type='scanner')
    
    然後在任意位置：
      brain.log(signals=[...])   # 寫入決策
      brain.log(metrics={...})   # 寫入指標
      brain.log(observation='...') # 寫入觀測
    """
    
    _instance = None
    _registered = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._logs = []
            cls._instance._job_name = 'generic'
            cls._instance._universe = 'MULTI'
            cls._instance._job_type = 'unknown'
        return cls._instance
    
    def register(self, job_name: str, universe: str = 'MULTI', job_type: str = 'unknown'):
        """向 Wrapper 登錄此 Job"""
        self._job_name = job_name
        self._universe = universe
        self._job_type = job_type
        self._registered = True
        print(f'[BrainWrapper] Registered: {job_name} ({universe}, {job_type})')
        
        # 自動建立 BrainAwareExecutor 並讀取脈絡
        try:
            from brain_aware_executor import BrainAwareExecutor
            self._brain = BrainAwareExecutor(job_name, universe, job_type)
            self._ctx = self._brain.before_execute()
        except Exception as e:
            print(f'[BrainWrapper] Warning: {e}')
            self._brain = None
            self._ctx = {}
    
    def log(self, 
            signals: List[Dict] = None,
            metrics: Dict = None,
            summary: str = None,
            observation: str = None,
            decisions: List[Dict] = None,
            errors: List[str] = None,
            output_file: str = None,
            **kwargs):
        """寫入記憶（日誌批次）"""
        if not self._registered:
            return
        
        # 累積 log
        self._logs.append({
            'signals': signals or [],
            'metrics': metrics or {},
            'summary': summary or observation or '',
            'decisions': decisions or [],
            'errors': errors or [],
            'output_file': output_file,
            'kwargs': kwargs,
            'timestamp': datetime.now().isoformat()
        })
    
    def flush(self) -> Optional[str]:
        """
        腳本結束時（或任何時機）Flush 所有累積的 logs 到短期記憶。
        返回寫入的 memory IDs。
        """
        if not self._registered or not self._logs or not self._brain:
            return None
        
        all_signals = []
        all_metrics = []
        combined_summary = []
        all_errors = []
        
        for log in self._logs:
            all_signals.extend(log.get('signals', []))
            if log.get('metrics'):
                all_metrics.append(log['metrics'])
            if log.get('summary'):
                combined_summary.append(log['summary'])
            all_errors.extend(log.get('errors', []))
        
        #合併 metrics
        merged_metrics = {}
        for m in all_metrics:
            merged_metrics.update(m)
        if len(all_metrics) > 1:
            merged_metrics['_runs'] = len(all_metrics)
        
        # 合併 summary
        final_summary = f"{self._job_name}: {'; '.join(combined_summary[:5])}"
        
        memory_ids = self._brain.after_execute(
            success=not all_errors,
            summary=final_summary[:200],
            signals=all_signals[:20],
            metrics=merged_metrics or None,
            errors=all_errors if all_errors else None,
            output_file=self._logs[0].get('output_file') if self._logs else None
        )
        
        self._logs.clear()
        return memory_ids
    
    @property
    def context(self) -> Dict:
        """取得 Job 執行前的長期記憶脈絡"""
        return self._ctx
    
    def __del__(self):
        """解構時自動 flush"""
        if self._registered and self._logs:
            try:
                self.flush()
            except:
                pass

# 預設實例（import brain 即用）
brain = UniversalBrainWrapper()
brain_wrapper = brain  # 別名

if __name__ == '__main__':
    # 測試
    print('Universal Brain Wrapper Test')
    print('Usage:')
    print('  from stores.universal_brain_wrapper import brain')
    print('  brain.register("my_job", universe="TW", job_type="scanner")')
    print('  brain.log(signals=[...], metrics={...})')
    print('  brain.flush()  # 結束時')