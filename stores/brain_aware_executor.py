# -*- coding: utf-8 -*-
"""
Brain-Aware Executor — 讓 Isolated Jobs 有記憶的 Middleware
==========================================================
功能：
1. Job 執行前：讀取 long_term 脈絡（patterns、active_positions、watchlist）
2. Job 執行後：自動寫入 short_term（result、decision、observation）
3. 提供與現有腳本的無縫整合（不影响原有執行邏輯）

用法：
  # 在現有腳本最後加入（不影響原有邏輯）：
  from brain_aware_executor import BrainAwareExecutor
  brain = BrainAwareExecutor(job_name='nana_job', universe='TW')
  brain.after_execute(success=True, 
                      signals=[...],  # Nana/Leo 信號
                      metrics={...})  # 績效指標

  # 讓腳本開頭加入（可選）：
  context = brain.before_execute()
  # context 包含：patterns、watchlist、active_positions 等
"""

import sys, json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
ST_DIR = STORES_DIR / 'short_term'
WORK_DIR = STORES_DIR / 'working'
LT_DIR = STORES_DIR / 'long_term'

sys.path.insert(0, str(BASE_DIR / 'stores'))
from short_term_writer import write_memory, get_short_term_summary

class BrainAwareExecutor:
    """讓每個 isolated job 都能感知並寫入記憶系統"""
    
    def __init__(self, job_name: str, universe: str = 'MULTI', job_type: str = 'scanner'):
        """
        job_name: 腳本名稱（用於source標記）
        universe: TW / US / SOX / MULTI
        job_type: scanner / macro / nana / leo / etf
        """
        self.job_name = job_name
        self.universe = universe
        self.job_type = job_type
        self.execution_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 長期記憶
        self.patterns = self._load_patterns()
        self.lessons = self._load_lessons()
        self.frameworks = self._load_frameworks()
        self.working = self._load_working()
    
    # ===== 讀取長期記憶 =====

    def _load_patterns(self) -> List[Dict]:
        """讀取 patterns.json"""
        f = LT_DIR / 'patterns.json'
        if f.exists():
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                return data.get('patterns', [])
        return []

    def _load_lessons(self) -> List[Dict]:
        """讀取 lessons.json"""
        f = LT_DIR / 'lessons.json'
        if f.exists():
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                return data.get('lessons', [])
        return []

    def _load_frameworks(self) -> List[Dict]:
        """讀取 frameworks.json"""
        f = LT_DIR / 'frameworks.json'
        if f.exists():
            with open(f, 'r', encoding='utf-8') as fp:
                data = json.load(fp)
                return data.get('frameworks', [])
        return []

    def _load_working(self) -> Dict:
        """讀取 working/active_context.json"""
        f = WORK_DIR / 'active_context.json'
        if f.exists():
            with open(f, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        return {'active_positions': [], 'watchlist': [], 'alerts': []}

    def before_execute(self) -> Dict[str, Any]:
        """
        Job 執行前呼叫 — 取得脈絡 + 決定是否要跳過
        回傳 dict：
          - patterns: 相關的 patterns（universe 過濾）
          - lessons: 相關的 lessons
          - active_positions: 目前持倉
          - watchlist: 觀察名單
          - alerts: 警示
          - skip_reason: 若需跳過，填入原因
        """
        # 過濾符合 universe 的 patterns
        relevant_patterns = [
            p for p in self.patterns
            if p.get('universe', 'UNKNOWN') in (self.universe, 'MULTI')
            and p.get('status') != 'inactive'
        ]
        
        # 近期 lessons（90天內）
        cutoff = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        recent_lessons = [
            l for l in self.lessons
            if l.get('date', '') >= cutoff
        ]
        
        # 與 universe 相關的 lessons
        relevant_lessons = [
            l for l in recent_lessons
            if self.universe in l.get('tags', []) 
            or self.universe in l.get('summary', '')
        ]
        
        result = {
            'execution_id': self.execution_id,
            'job_name': self.job_name,
            'universe': self.universe,
            'timestamp': datetime.now().isoformat(),
            'patterns': relevant_patterns,
            'lessons': relevant_lessons[-5:],  # 最近5筆
            'active_positions': self.working.get('active_positions', [])[:10],
            'watchlist': self.working.get('watchlist', [])[:20],
            'alerts': self.working.get('alerts', [])[:5],
            'short_term_summary': get_short_term_summary(),
            'skip_reason': None
        }
        
        # 檢查是否需要跳過（根據 alert）
        for alert in result['alerts']:
            if alert.get('symbol') in self.working.get('watchlist', []):
                # 有 alert，不跳過，但註記
                result['alert_active'] = True
        
        print(f'[BrainAware] Job: {self.job_name} | Universe: {self.universe}')
        print(f'  Patterns: {len(relevant_patterns)} | Lessons: {len(relevant_lessons)}')
        print(f'  Active positions: {len(result["active_positions"])} | Watchlist: {len(result["watchlist"])}')
        
        return result

    # ===== 寫入短期記憶 =====

    def after_execute(
        self,
        success: bool = True,
        summary: str = '',
        signals: List[Dict] = None,
        metrics: Dict = None,
        decisions: List[Dict] = None,
        errors: List[str] = None,
        output_file: str = None,
        **kwargs
    ) -> str:
        """
        Job 執行後呼叫 — 寫入短期記憶
        
        signals: Nana/Leo 的買賣信號列表
        metrics: 績效指標（勝率、報酬等）
        decisions: 具體交易決定
        """
        memory_ids = []
        
        # 1. 觀測記錄（observation）
        if summary:
            obs_id = write_memory(
                mtype='observation',
                summary=summary[:200],
                detail=json.dumps({
                    'job_name': self.job_name,
                    'universe': self.universe,
                    'execution_id': self.execution_id,
                    'output_file': output_file,
                    'metrics': metrics,
                    **kwargs
                }, ensure_ascii=False),
                source=f'{self.job_type}_job',
                tags=[self.universe, self.job_type, 'scan'],
                importance=self._calc_importance(metrics),
                links=[],
                expiry_days=30
            )
            memory_ids.append(obs_id)
        
        # 2. 信號記錄（decision）
        if signals:
            for sig in signals:
                # 避免重複信號（根據 symbol + date）
                sig_id = write_memory(
                    mtype='decision',
                    summary=f"{sig.get('symbol','?')} {sig.get('action','?')} @ ${sig.get('price','?')} — {sig.get('reason','')[:80]}",
                    detail=json.dumps(sig, ensure_ascii=False),
                    source=f'{self.job_type}_job',
                    tags=[self.universe, sig.get('symbol',''), sig.get('action',''), self.job_type],
                    importance=sig.get('strength', 5),
                    links=sig.get('pattern_links', []),
                    expiry_days=60  # 信號比 observation 保留更久
                )
                memory_ids.append(sig_id)
        
        # 3. 指標記錄（metric）
        if metrics:
            metric_summary = self._format_metrics(metrics)
            met_id = write_memory(
                mtype='metric',
                summary=metric_summary[:200],
                detail=json.dumps(metrics, ensure_ascii=False),
                source=f'{self.job_type}_job',
                tags=[self.universe, self.job_type, 'performance'],
                importance=6,
                links=[],
                expiry_days=30
            )
            memory_ids.append(met_id)
        
        # 4. 決定記錄（decision — 高層次策略決定）
        if decisions:
            for dec in decisions:
                dec_id = write_memory(
                    mtype='decision',
                    summary=dec.get('summary', str(dec))[:200],
                    detail=json.dumps(dec, ensure_ascii=False),
                    source=f'{self.job_type}_job',
                    tags=[self.universe, 'strategic', self.job_type],
                    importance=dec.get('importance', 7),
                    links=dec.get('pattern_links', []),
                    expiry_days=90
                )
                memory_ids.append(dec_id)
        
        # 5. 錯誤記錄（lesson — 失敗經驗）
        if errors:
            for err in errors:
                err_id = write_memory(
                    mtype='lesson',
                    summary=f"[ERROR] {self.job_name}: {err[:150]}",
                    detail=json.dumps({'errors': errors, 'execution_id': self.execution_id}, ensure_ascii=False),
                    source=f'{self.job_type}_job',
                    tags=[self.universe, 'error', self.job_type],
                    importance=8,
                    lesson_type='error',
                    links=[],
                    expiry_days=90
                )
                memory_ids.append(err_id)
        
        # 6. Framework 更新追蹤
        if kwargs.get('framework_version'):
            fw_id = write_memory(
                mtype='framework_change',
                summary=f"{self.job_name} v{kwargs['framework_version']}: {kwargs.get('framework_note','')}",
                detail='',
                source=f'{self.job_type}_job',
                tags=[self.universe, 'framework', self.job_type],
                importance=7,
                links=[],
                expiry_days=365  # Framework 版本永久保留
            )
            memory_ids.append(fw_id)
        
        print(f'[BrainAware] Wrote {len(memory_ids)} memory entries: {memory_ids}')
        return ', '.join(memory_ids)

    # ===== 工具方法 =====

    def _calc_importance(self, metrics: Dict = None) -> int:
        """根據 metrics 計算重要性"""
        if not metrics:
            return 5
        score = 6
        # 有實測勝率且樣本夠多
        if 'win_rate' in metrics and metrics.get('sample_size', 0) >= 10:
            score += 1
            if metrics['win_rate'] >= 0.7:
                score += 1
            elif metrics['win_rate'] < 0.5:
                score -= 1
        # 發現異常
        if metrics.get('anomaly_detected'):
            score += 2
        return min(10, max(1, score))

    def _format_metrics(self, metrics: Dict) -> str:
        """格式化 metrics 摘要"""
        parts = []
        if 'win_rate' in metrics:
            wr = metrics['win_rate']
            parts.append(f'勝率{wr:.0%}')
        if 'avg_return' in metrics:
            ar = metrics['avg_return']
            parts.append(f'均報酬{ar:+.2f}%')
        if 'total_signals' in metrics:
            ts = metrics['total_signals']
            parts.append(f'信號{ts}筆')
        if 'high_quality' in metrics:
            hq = metrics['high_quality']
            parts.append(f'高品質{hq}檔')
        return ' | '.join(parts) if parts else str(metrics)

    # ===== 與現有腳本的整合掛鉤 =====

    def attach_to_scanner_output(self, report_json: Dict) -> str:
        """
        自動包裝 Universe Scanner 的 JSON 輸出，寫入短期記憶
        用於 universe_scanner.py 的 main() 最後呼叫
        """
        universe = report_json.get('universe', self.universe)
        strategy = report_json.get('strategy', 'unknown')
        top_picks = report_json.get('top_picks', [])
        total = report_json.get('total_scanned', 0)
        summary_data = report_json.get('summary', {})
        
        # 整理信號
        signals = []
        for pick in top_picks[:5]:
            signals.append({
                'symbol': pick.get('symbol'),
                'action': 'buy' if pick.get('score', 0) >= 60 else 'watch',
                'price': pick.get('price'),
                'score': pick.get('score'),
                'reason': f"{strategy}策略評分{pick.get('score')}分",
                'strength': min(10, pick.get('score', 5) / 10),
                'strategy': strategy,
                'universe': universe,
                'pattern_links': []
            })
        
        metrics = {
            'total_scanned': total,
            'high_quality': summary_data.get('high_score_count', 0),
            'strategy': strategy,
            'universe': universe
        }
        
        summary = f"{universe.upper()} {strategy}掃描：{total}檔中 {summary_data.get('high_score_count', 0)} 檔高品質（≥60分）"
        
        return self.after_execute(
            success=True,
            summary=summary,
            signals=signals,
            metrics=metrics,
            output_file=f'reports/{universe}/{datetime.now().strftime("%Y%m%d")}_{strategy}.json'
        )

# ===== 便捷包裝函數 =====

def after_scanner(universe: str, strategy: str, report_json: Dict) -> str:
    """Universe Scanner 結果寫入短期記憶"""
    brain = BrainAwareExecutor(
        job_name=f'{universe}_scanner',
        universe=universe.upper(),
        job_type='scanner'
    )
    return brain.attach_to_scanner_output(report_json)

def after_nana(signals: List[Dict], metrics: Dict = None) -> str:
    """Nana Job 結果寫入短期記憶"""
    brain = BrainAwareExecutor(
        job_name='nana_v68',
        universe='TW',
        job_type='nana'
    )
    summary = f"Nana波段：{len(signals)} 個信號"
    return brain.after_execute(success=True, summary=summary, signals=signals, metrics=metrics)

def after_leo(signals: List[Dict], metrics: Dict = None) -> str:
    """Leo Job 結果寫入短期記憶"""
    brain = BrainAwareExecutor(
        job_name='leo_v65',
        universe='TW',
        job_type='leo'
    )
    summary = f"Leo波段：{len(signals)} 個信號"
    return brain.after_execute(success=True, summary=summary, signals=signals, metrics=metrics)

def after_macro(macro_json_path: str, job_name: str = 'macro') -> str:
    """Macro Job 結果寫入短期記憶"""
    brain = BrainAwareExecutor(
        job_name=f'{job_name}_macro',
        universe='MULTI',
        job_type='macro'
    )
    return brain.after_execute(
        success=True,
        summary=f"Macro {job_name} 執行完成",
        output_file=macro_json_path
    )

if __name__ == '__main__':
    # 測試模式
    brain = BrainAwareExecutor(job_name='test_job', universe='TW', job_type='scanner')
    ctx = brain.before_execute()
    print('\n=== Context ===')
    print(f'Patterns: {len(ctx["patterns"])}')
    print(f'Recent lessons: {len(ctx["lessons"])}')
    print(f'Active positions: {len(ctx["active_positions"])}')
    
    # 測試寫入
    mid = brain.after_execute(
        success=True,
        summary='Test scan: 300 stocks, 15 high quality',
        signals=[{'symbol': '2330.TW', 'action': 'buy', 'price': 890, 'score': 72, 'reason': 'P/E=18, RSI=55'}],
        metrics={'total_scanned': 300, 'high_quality': 15, 'win_rate': 0.72, 'sample_size': 20}
    )
    print(f'\nMemory IDs: {mid}')
    print('\nDONE')