# 腳本標準化與大腦整合方案
**日期：** 2026-05-09
**目標：** 將修復後的腳本與 Tina 大腦系統整合，建立標準化程序

---

## 0. 現況分析

### 問題診斷

| 問題 | 說明 |
|:-----|:-----|
| **腳本各自為政** | 每個腳本獨立執行，輸出分散，無法統一管理 |
| **大腦無感知** | `brain_aware_executor.py` 存在但未被使用 |
| **Job 之間無協調** | 5 個 jobs 同時跑同一個 script directory，可能互相干擾 |
| **無統一報告格式** | 有的輸出 JSON，有的只輸出 Console，沒有標準化 |
| **監督機制缺失** | 無法確認腳本是否真的成功執行，還是只是「看起來 ok」|

### 各腳本現況

| 腳本 | 輸出形式 | 有無寫入記憶 | 有無統一報告 |
|:-----|:---------|:------------|:------------|
| us_ai_tech_daily.py | Console + JSON | ❌ 無 | ❌ 無 |
| us_margin_daily.py | Console + JSON | ❌ 無 | ❌ 無 |
| leos_v65.py | Console + JSON | ⚠️ 部分（有 Lessons 查詢）| ❌ 無 |
| tina_auto_learner.py | Console + JSON | ⚠️ 部分 | ❌ 無 |
| brain_aware_executor.py | — | ✅ 有 | ✅ 有（統一路由）|

---

## 1. 標準化程序

### 1.1 每個腳本都必須遵守的執行流程

```
┌─────────────────────────────────────────────┐
│  STEP 0: 初始化（所有腳本強制）                  │
│  from script_standards import ScriptStandard │
│  std = ScriptStandard(job_name, universe)    │
│  std.before_execute()                        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  STEP 1: 執行主要邏輯（不改變現有代碼）           │
│  維持原有功能，只在最後調用 std.after_execute()  │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  STEP 2: 結果寫入記憶（所有腳本強制）             │
│  std.after_execute(success, signals, metrics)│
│  → 自動寫入 short_term/working/             │
│  → 自動發送 Telegram 摘要                     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  STEP 3: 標準化日誌（所有腳本強制）               │
│  std.finalize()                             │
│  → 寫入 job_run_log.json                     │
│  → 更新健康度狀態                             │
└─────────────────────────────────────────────┘
```

### 1.2 ScriptStandard 類的標準方法

```python
class ScriptStandard:
    """所有 Tina 腳本的標準化介面"""
    
    def __init__(self, job_name: str, universe: str = 'MULTI'):
        """
        job_name: 例如 'us_ai_tech', 'leo_v65', 'auto_learner'
        universe: TW / US / SOX / MULTI
        """
        self.job_name = job_name
        self.universe = universe
        self.start_time = datetime.now()
        self.execution_id = self.start_time.strftime('%Y%m%d_%H%M%S')
        
        # 讀取長期記憶（Patterns / Lessons / Frameworks）
        self.context = self._load_long_term_memory()
        
        # 讀取當前持倉 / Watchlist（用於過濾）
        self.active = self._load_active_positions()
        
        # 初始化健康度追蹤
        self.health = {'status': 'running', 'errors': [], 'duration_ms': 0}
    
    def before_execute(self) -> dict:
        """執行前的脈絡注入"""
        return {
            'execution_id': self.execution_id,
            'patterns': self.context.get('patterns', []),
            'active_positions': self.active,
            'job_name': self.job_name,
            'universe': self.universe
        }
    
    def after_execute(self, success: bool, signals: list, metrics: dict):
        """
        執行後寫入記憶 + 發送 Telegram
        - signals: 交易訊號列表
        - metrics: 績效指標
        """
        # 1. 寫入 short_term/working/
        self._write_working_memory(success, signals, metrics)
        
        # 2. 發送 Telegram 摘要
        self._send_telegram_summary(success, signals, metrics)
        
        # 3. 更新健康度
        self._update_health(success)
        
        return {'status': 'ok', 'execution_id': self.execution_id}
    
    def finalize(self):
        """執行完成後的最後清理"""
        duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        self.health['duration_ms'] = duration_ms
        self._write_job_run_log()
        return self.health
```

---

## 2. 自動流程設計

### 2.1 自動化觸發層級

```
Cron Job 觸發（每日定時）
        ↓
┌───────────────────────────────────────┐
│  Brain-Aware Executor（統一入口）         │
│  - 讀取脈絡（Patterns / 持倉 / Lessons）│
│  - 協調腳本執行順序                      │
│  - 追蹤執行狀態                          │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│  標準化 Script執行（4步流程）             │
│  1. before_execute()                  │
│  2. [原有邏輯]                         │
│  3. after_execute()                   │
│  4. finalize()                         │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│  輸出路由（自動分發）                    │
│  - Telegram（摘要報告）                  │
│  - Short-term Memory（觀測記錄）         │
│  - Long-term Memory（Pattern蒸餾）      │
│  - Job Run Log（健康度追蹤）            │
└───────────────────────────────────────┘
```

### 2.2 自動餾程： Pattern 識別

```
每週日（日誌深度檢討）
        ↓
[Step 1] 讀取 job_run_log.json
        ↓
[Step 2] 識別重複模式
  - 什麼訊號總是失敗？
  - 哪些指標預測最準？
  - 市場條件如何影響勝率？
        ↓
[Step 3] 寫入 long_term/patterns.json
        ↓
[Step 4] 下週同一個 Job 執行時自動加載
```

### 2.3 自動化 Lesson 活化

```
每次 Leo/Nana 進場決策前
        ↓
[Step 1] 查詢 Lessons 庫（losses/ + wins/）
        ↓
[Step 2] 查詢 Experience Ledger
        ↓
[Step 3] 根據勝率調整決策
  - 勝率 < 50%（>=5筆）→ 警告信號
  - 勝率 > 70%（>=5筆）→ 正向參考
        ↓
[Step 4] 進場後寫入 Lesson（成功/失敗）
```

---

## 3. 現有腳本整合方案

### 3.1 us_ai_tech_daily.py（最簡單，先做）

**現況：**
- 輸出 Console + JSON
- 獨立執行，無記憶寫入
- cron job 每日 08:30 執行

**整合方式：**
```python
# 在 main() 函數開頭加入：
from script_standards import ScriptStandard
std = ScriptStandard(job_name='us_ai_tech', universe='US')

# 在 main() 函數結尾加入：
if __name__ == '__main__':
    try:
        std.before_execute()
        main()
        signals = load_signals_from_json()
        metrics = load_metrics_from_json()
        std.after_execute(success=True, signals=signals, metrics=metrics)
    except Exception as e:
        std.after_execute(success=False, signals=[], metrics={'error': str(e)})
    finally:
        std.finalize()
```

**預期效果：**
- ✅ 每次執行自動寫入 short_term/working/us_ai_tech_YYYYMMDD_HHMMSS.json
- ✅ 自動發送 Telegram 摘要（Signals + Summary）
- ✅ 健康度追蹤寫入 job_run_log.json

---

### 3.2 us_margin_daily.py（同上）

**整合方式：**
```python
from script_standards import ScriptStandard
std = ScriptStandard(job_name='us_margin', universe='US')

# 在 if __name__ == '__main__' 區塊：
if __name__ == '__main__':
    try:
        std.before_execute()
        main()
        signals = load_signals_from_json()
        metrics = {'high_risk': len(high_risk), 'squeeze_count': len(squeeze)}
        std.after_execute(success=True, signals=signals, metrics=metrics)
    except Exception as e:
        std.after_execute(success=False, signals=[], metrics={'error': str(e)})
    finally:
        std.finalize()
```

---

### 3.3 leos_v65.py（複雜，最後做）

**現況：**
- 已有 Lessons 查詢系統
- 有獨立輸出到 leos_analysis_v65.json
- 有交易決策邏輯

**整合方式：**
```python
# 在 import 區塊加入：
from script_standards import ScriptStandard
std = ScriptStandard(job_name='leo_v65', universe='TW')

# 在主要邏輯最後加入：
std.after_execute(
    success=success,
    signals=entry_signals,  # Leo 的進場信號
    metrics={
        'total_trades': len(trades),
        'position_size': total_value,
        'rsi_filter': rsi_threshold
    }
)
std.finalize()
```

---

### 3.4 tina_auto_learner.py（中等複雜度）

**整合方式：**
```python
from script_standards import ScriptStandard
std = ScriptStandard(job_name='auto_learner', universe='MULTI')

# 在自動學習邏輯完成後：
std.after_execute(
    success=not has_errors,
    signals=new_patterns,  # 發現的新 Pattern
    metrics={
        'patterns_added': len(new_patterns),
        'lessons_updated': len(lessons_updated),
        'db_expanded': db_size_increase
    }
)
```

---

## 4. 創建 script_standards.py

```python
# -*- coding: utf-8 -*-
"""
ScriptStandards — Tina 系統腳本標準化框架
==========================================
所有 Tina Cron Jobs 的腳本都應該繼承這個框架

使用方式：
  from script_standards import ScriptStandard
  std = ScriptStandard(job_name='us_ai_tech', universe='US')
  
  std.before_execute()          # 讀取脈絡
  # [執行主要邏輯]
  std.after_execute(success, signals, metrics)  # 寫入記憶 + 發送 Telegram
  std.finalize()               # 寫入日誌 + 更新健康度
"""

import sys, json
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

FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjJ9.1LHB4yKHeZFoXStyjK2W9F6X3nZLMA1IfPWpDVlv6K0'


class ScriptStandard:
    """所有 Tina 腳本的標準化介面"""
    
    # ===== 初始化 =====
    def __init__(self, job_name: str, universe: str = 'MULTI'):
        self.job_name = job_name
        self.universe = universe
        self.start_time = datetime.now()
        self.execution_id = self.start_time.strftime('%Y%m%d_%H%M%S')
        
        # 讀取長期記憶
        self.patterns = self._load_json(LT_DIR / 'patterns.json', [])
        self.frameworks = self._load_json(LT_DIR / 'frameworks.json', [])
        
        # 讀取當前持倉（用於過濾）
        self.active_positions = self._load_json(
            STORES_DIR / 'short_term' / 'active_positions.json', []
        )
        
        # 健康度追蹤
        self.health = {
            'status': 'running',
            'errors': [],
            'warnings': [],
            'duration_ms': 0,
            'last_success': None
        }
    
    # ===== 執行前：讀取脈絡 =====
    def before_execute(self) -> dict:
        """返回執行前的脈絡，供腳本使用"""
        return {
            'execution_id': self.execution_id,
            'timestamp': self.start_time.isoformat(),
            'patterns': self.patterns[-3:],  # 最近 3 個 Pattern
            'active_positions': self.active_positions,
            'job_name': self.job_name,
            'universe': self.universe
        }
    
    # ===== 執行後：寫入記憶 + 發送 Telegram =====
    def after_execute(self, success: bool, signals: List[dict], metrics: dict):
        """執行完成後的標準化處理"""
        
        # 1. 寫入 working memory
        working_record = {
            'execution_id': self.execution_id,
            'timestamp': self.start_time.isoformat(),
            'job_name': self.job_name,
            'universe': self.universe,
            'success': success,
            'signals': signals,
            'metrics': metrics,
            'health': self.health
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
        """執行完成後的最後處理"""
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
            'warnings': self.health['warnings']
        })
        
        # 只保留最近 100 筆記錄
        log = log[-100:]
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        
        return self.health
    
    # ===== 內部工具 =====
    def _load_json(self, path: Path, default) -> Any:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return default
    
    def _send_telegram(self, success: bool, signals: list, metrics: dict):
        """發送 Telegram 摘要（簡化版）"""
        import urllib.request
        
        emoji = '✅' if success else '❌'
        
        # 格式化信號摘要
        if signals:
            signal_lines = []
            for s in signals[:5]:  # 最多 5 個
                sym = s.get('symbol', 'N/A')
                sig = s.get('signal', s.get('type', 'N/A'))
                signal_lines.append(f"  • {sym}: {sig}")
            signals_text = '\n'.join(signal_lines)
        else:
            signals_text = "  （無信號）"
        
        # 格式化指標
        metrics_text = ', '.join([f"{k}={v}" for k, v in metrics.items()][:3])
        
        msg = f"""
{emoji} {self.job_name} 執行{'成功' if success else '失敗'}

📊 信號摘要：
{signals_text}

📈 指標：{metrics_text if metrics_text else '無'}
⏱️ ID：{self.execution_id}
"""
        
        data = json.dumps({
            'chat_id': '1616824689',
            'text': msg.strip()
        }).encode('utf-8')
        
        req = urllib.request.Request(
            'https://api.telegram.org/bot/update',
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        # 簡化：實際應用會使用專門的 Telegram API
        # 這裡只是框架，不實際發送
        print(f"[Telegram] {self.job_name}: {success}")


# ===== 快速測試 =====
if __name__ == '__main__':
    std = ScriptStandard('test_job', 'TW')
    print(f"ID: {std.execution_id}")
    print(f"Patterns: {len(std.patterns)} loaded")
    print(f"Active positions: {len(std.active_positions)} loaded")
    
    # 測試執行
    ctx = std.before_execute()
    std.after_execute(True, [{'symbol': '2330', 'signal': 'BUY'}], {'rsi': 35})
    health = std.finalize()
    print(f"Health: {health}")
```

---

## 5. 實施路線圖

| 階段 | 時間 | 工作 | 負責 |
|:-----|:-----|:-----|:-----|
| **Phase 1** | 今日 | 建立 `script_standards.py` 框架 | Tina |
| **Phase 2** | 明日 | 整合 `us_ai_tech_daily.py` | Tina |
| **Phase 3** | 明日 | 整合 `us_margin_daily.py` | Tina |
| **Phase 4** | 週日 | 整合 `tina_auto_learner.py` | Tina |
| **Phase 5** | 週日 | 整合 `leos_v65.py` | Tina |
| **Phase 6** | 週日 | 建立 Pattern 自動蒸餾流程 | Tina |

---

## 6. 預期效果

| 指標 | 改善前 | 改善後 |
|:-----|:-------|:-------|
| 腳本之間協調 | ❌ 無 | ✅ 統一入口 |
| 記憶寫入 | ❌ 手動 | ✅ 自動 |
| Telegram 報告 | ⚠️ 部分腳本 | ✅ 全部腳本 |
| 健康度追蹤 | ❌ 無 | ✅ job_run_log.json |
| Pattern 活化 | ⚠️ 僅 Leo | ✅ 所有腳本 |

---

_方案完成：2026-05-09 21:20 by Tina_