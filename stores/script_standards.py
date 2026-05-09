# -*- coding: utf-8 -*-
"""
ScriptStandards — Tina 系統腳本標準化框架
==========================================
所有 Tina Cron Jobs 的腳本都應該使用這個框架

使用方式：
  from script_standards import ScriptStandard
  std = ScriptStandard(job_name='us_ai_tech', universe='US')
  
  ctx = std.before_execute()          # 讀取脈絡
  # [執行主要邏輯]
  std.after_execute(success, signals, metrics)  # 寫入記憶 + 發送 Telegram
  std.finalize()                       # 寫入日誌 + 更新健康度

建立日期：2026-05-09
版本：v1.0
"""

import sys, json, urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
STORES_DIR = BASE_DIR / 'stores'
ST_DIR = STORES_DIR / 'short_term'
WORK_DIR = STORES_DIR / 'working'
LT_DIR = STORES_DIR / 'long_term'
LOG_DIR = BASE_DIR / 'logs'

# 確保必要的目錄存在
for d in [ST_DIR, WORK_DIR, LT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Telegram Bot Token（從 secrets 或直接設定）
TELEGRAM_BOT_TOKEN = ''  # 若有專門的 Tina Bot，在這裡設定
TELEGRAM_CHAT_ID = '1616824689'


class ScriptStandard:
    """所有 Tina 腳本的標準化介面"""
    
    # ===== 初始化 =====
    def __init__(self, job_name: str, universe: str = 'MULTI'):
        """
        job_name: 腳本名稱，用於 source 標記和檔案命名
                  例如：us_ai_tech, leo_v65, nana_v68, auto_learner
        universe: TW / US / SOX / MULTI
        """
        self.job_name = job_name
        self.universe = universe
        self.start_time = datetime.now()
        self.execution_id = self.start_time.strftime('%Y%m%d_%H%M%S')
        
        # 讀取長期記憶
        self.patterns = self._load_json(LT_DIR / 'patterns.json', [])
        if isinstance(self.patterns, dict):
            self.patterns = self.patterns.get('items', self.patterns.get('patterns', []))
        self.frameworks = self._load_json(LT_DIR / 'frameworks.json', [])
        if isinstance(self.frameworks, dict):
            self.frameworks = self.frameworks.get('items', self.frameworks.get('frameworks', []))
        self.lessons = self._load_json(LT_DIR / 'lessons.json', {'losses': [], 'wins': []})
        
        # 讀取當前持倉（用於過濾）
        self.active_positions = self._load_json(
            STORES_DIR / 'short_term' / 'active_positions.json', []
        )
        if isinstance(self.active_positions, dict):
            self.active_positions = self.active_positions.get('positions', [])
        
        # 健康度追蹤
        self.health = {
            'status': 'running',
            'errors': [],
            'warnings': [],
            'duration_ms': 0,
            'last_success': None
        }
        
        # 腳本輸出統計
        self._signal_count = 0
        self._metric_summary = {}
    
    # ===== 執行前：讀取脈絡 =====
    def before_execute(self) -> dict:
        """
        返回執行前的脈絡，供腳本使用
        
        返回值包含：
        - execution_id: 本次執行 ID
        - timestamp: 執行時間
        - patterns: 最近 3 個 Pattern
        - active_positions: 當前持倉
        - job_name / universe: 腳本標記
        """
        patterns_list = self.patterns if isinstance(self.patterns, list) else []
        frameworks_list = self.frameworks if isinstance(self.frameworks, list) else []
        
        return {
            'execution_id': self.execution_id,
            'timestamp': self.start_time.isoformat(),
            'patterns': patterns_list[-3:] if len(patterns_list) >= 3 else patterns_list,  # 最近 3 個
            'frameworks': frameworks_list[-1:] if frameworks_list else [],
            'active_positions': self.active_positions,
            'lessons_summary': {
                'losses': len(self.lessons.get('losses', [])),
                'wins': len(self.lessons.get('wins', []))
            },
            'job_name': self.job_name,
            'universe': self.universe
        }
    
    # ===== 執行後：寫入記憶 + 發送 Telegram =====
    def after_execute(self, success: bool, signals: List[dict] = None, metrics: dict = None):
        """
        執行完成後的標準化處理
        
        參數：
        - success: 是否成功執行
        - signals: 交易訊號列表，例如 [{'symbol': '2330', 'signal': 'BUY', 'rsi': 35}]
        - metrics: 績效指標，例如 {'rsi_avg': 42.5, 'signals_found': 3}
        """
        signals = signals or []
        metrics = metrics or {}
        
        self._signal_count = len(signals)
        self._metric_summary = metrics
        
        # 1. 寫入 working memory
        working_record = {
            'execution_id': self.execution_id,
            'timestamp': self.start_time.isoformat(),
            'job_name': self.job_name,
            'universe': self.universe,
            'success': success,
            'signals': signals,
            'metrics': metrics,
            'health': self.health.copy()
        }
        
        work_file = WORK_DIR / f'{self.job_name}_{self.execution_id}.json'
        with open(work_file, 'w', encoding='utf-8') as f:
            json.dump(working_record, f, ensure_ascii=False, indent=2)
        
        # 2. 發送 Telegram 摘要
        self._send_telegram(success, signals, metrics)
        
        # 3. 更新健康度
        self.health['status'] = 'ok' if success else 'error'
        self.health['last_success'] = datetime.now().isoformat() if success else None
        
        return working_record
    
    # ===== 最終化：寫入日誌 =====
    def finalize(self) -> dict:
        """
        執行完成後的最後處理
        
        - 計算執行耗時
        - 寫入 job_run_log.json（保留最近 200 筆記錄）
        - 返回健康度摘要
        """
        duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        self.health['duration_ms'] = duration_ms
        
        # 寫入 job_run_log.json
        log_file = LOG_DIR / 'job_run_log.json'
        log = self._load_json(log_file, [])
        
        log.append({
            'execution_id': self.execution_id,
            'timestamp': self.start_time.isoformat(),
            'job_name': self.job_name,
            'universe': self.universe,
            'duration_ms': duration_ms,
            'status': self.health['status'],
            'errors': self.health['errors'],
            'warnings': self.health['warnings'],
            'signal_count': self._signal_count,
            'metrics_summary': self._metric_summary
        })
        
        # 只保留最近 200 筆記錄
        log = log[-200:]
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        
        return self.health
    
    # ===== 便捷方法：錯誤處理 =====
    def handle_error(self, error: Exception, context: str = ''):
        """
        便捷的錯誤處理方法
        
        用法：
          try:
              # [主要邏輯]
          except Exception as e:
              std.handle_error(e, '讀取股價時發生錯誤')
              raise
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.health['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'error': error_msg
        })
        print(f"[ERROR] {self.job_name}: {error_msg}")
    
    def add_warning(self, message: str):
        """添加警告訊息"""
        self.health['warnings'].append({
            'timestamp': datetime.now().isoformat(),
            'message': message
        })
        print(f"[WARNING] {self.job_name}: {message}")
    
    # ===== 內部工具 =====
    def _load_json(self, path: Path, default: Any) -> Any:
        """安全讀取 JSON 檔案"""
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load {path}: {e}")
        return default
    
    def _send_telegram(self, success: bool, signals: list, metrics: dict):
        """發送 Telegram 摘要"""
        # 如果沒有 Bot Token，不發送
        if not TELEGRAM_BOT_TOKEN:
            print(f"[Telegram] (no token) {self.job_name}: {success}")
            return
        
        emoji = '✅' if success else '❌'
        
        # 格式化信號摘要（最多 5 個）
        if signals:
            signal_lines = []
            for s in signals[:5]:
                sym = s.get('symbol', s.get('code', 'N/A'))
                sig = s.get('signal', s.get('type', s.get('action', 'N/A')))
                rsi = s.get('rsi', s.get('entry_rsi', ''))
                price = s.get('price', s.get('entry_price', ''))
                if price:
                    line = f"  • {sym}: {sig} (RSI={rsi}, ${price})"
                else:
                    line = f"  • {sym}: {sig} (RSI={rsi})"
                signal_lines.append(line)
            signals_text = '\n'.join(signal_lines)
            if len(signals) > 5:
                signals_text += f'\n  ... 還有 {len(signals) - 5} 個'
        else:
            signals_text = "  （無信號）"
        
        # 格式化指標（最多 4 個）
        if metrics:
            metrics_items = [(k, v) for k, v in metrics.items()]
            metrics_text = ', '.join([f"{k}={v}" for k, v in metrics_items[:4]])
        else:
            metrics_text = '無'
        
        msg = f"""
{emoji} {self.job_name} 執行{'成功' if success else '失敗'}

📊 信號摘要：
{signals_text}

📈 指標：{metrics_text}

⏱️ {self.execution_id}
        """
        
        try:
            data = json.dumps({
                'chat_id': TELEGRAM_CHAT_ID,
                'text': msg.strip()
            }).encode('utf-8')
            
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass  # 發送成功
                
        except Exception as e:
            print(f"[Telegram] Failed to send: {e}")


# ===== 快速測試 =====
if __name__ == '__main__':
    print("=" * 60)
    print("  ScriptStandards v1.0 — 測試模式")
    print("=" * 60)
    
    std = ScriptStandard('test_job', 'TW')
    print(f"\n[INIT] Job: {std.job_name}")
    print(f"[INIT] Universe: {std.universe}")
    print(f"[INIT] Execution ID: {std.execution_id}")
    print(f"[INIT] Patterns loaded: {len(std.patterns)}")
    print(f"[INIT] Active positions: {len(std.active_positions)}")
    
    # 測試執行
    print("\n[BEFORE] Context:")
    ctx = std.before_execute()
    print(f"  execution_id: {ctx['execution_id']}")
    print(f"  patterns: {len(ctx['patterns'])} loaded")
    print(f"  active_positions: {len(ctx['active_positions'])} loaded")
    
    # 模擬成功執行
    print("\n[AFTER] Simulating success:")
    signals = [
        {'symbol': '2330', 'signal': 'BUY', 'rsi': 35, 'price': 1050},
        {'symbol': '2303', 'signal': 'WATCH', 'rsi': 42, 'price': 125}
    ]
    metrics = {'signals_found': len(signals), 'rsi_avg': 38.5, 'scan_time': '08:30'}
    result = std.after_execute(True, signals, metrics)
    print(f"  work_file: {result['execution_id']}")
    
    # 最終化
    print("\n[FINALIZE]")
    health = std.finalize()
    print(f"  status: {health['status']}")
    print(f"  duration_ms: {health['duration_ms']}")
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)