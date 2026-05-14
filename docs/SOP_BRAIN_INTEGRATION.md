# Brain System — Isolated Jobs × 記憶系統 深度整合指南
## Brain-Aware Integration Guide v1.0
> 「每個 Job 都是大腦的神經元，每個記憶都是神經連接。」

---

## 整合架構

```
┌──────────────────────────────────────────────────────────────┐
│                    Tina 主腦（Main Session）                   │
│  • 讀取 brain_dashboard.json（全系統狀態）                      │
│  • 蒸餾 Job 的輸出                                              │
│  • 跨 Job 協調決策                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │ 讀取
                       ▼
┌──────────────────────────────────────────────────────────────┐
│          Brain Dashboard (brain_dashboard.json)               │
│  • short_term: 7天記憶分項統計                                  │
│  • long_term: patterns/lessons/frameworks                    │
│  • working: 持仓/觀察名單/警示                                 │
│  • growth: 記憶成長率                                          │
│  • health: 系統健康度                                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────────┐
        ▼              ▼                  ▼
 ┌─────────────┐ ┌──────────────┐ ┌────────────────┐
 │ Short-Term  │ │  Working     │ │  Long-Term     │
 │ (30天)      │ │  Memory      │ │  (永久)         │
 │             │ │              │ │                │
 │ stores/     │ │ stores/      │ │ stores/        │
 │ short_term/ │ │ working/     │ │ long_term/     │
 │             │ │              │ │                │
 │ • observation│ │ • active_ctx │ │ • patterns.json│
 │ • decision  │ │ • pending    │ │ • lessons.json │
 │ • metric    │ │ • alerts     │ │ • frameworks   │
 │ • lesson    │ │ • watchlist   │ │                │
 └──────┬──────┘ └──────┬───────┘ └───────┬────────┘
        │               │                 │
        └───────────────┴────────┬────────┘
                                 │ 每週五 18:00 蒸餾
                                 ▼
              ┌─────────────────────────────────┐
              │   Distillation Engine           │
              │   (memory_distiller.py)        │
              │   • daily → cleanup             │
              │   • weekly → promote patterns  │
              │   • monthly → decay/confirm    │
              └─────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              Isolated Jobs（每個都是感測器）                    │
│                                                              │
│  【已整合 BrainAware】                                        │
│    ✅ universe_scanner.py → 自動寫入 short_term              │
│                                                              │
│  【待整合（推薦順序）】                                         │
│    1. macro_data_fetcher.py → 觀測寫入                        │
│    2. nana_v68.py → 信號寫入                                  │
│    3. leos_v65.py → 信號寫入                                  │
│    4. daily_db_update.py → 指標寫入                           │
│    5. etf_daily_update.py → 指標寫入                          │
│    6. tina_auto_learner.py → lesson 寫入                      │
│                                                              │
│  【整合方式】                                                  │
│    A. 深度整合（修改腳本）：import universal_brain_wrapper    │
│    B. 外部整合（不改腳本）：job message 末尾呼叫 brain CLI     │
└──────────────────────────────────────────────────────────────┘
```

---

## 整合方式 A — 深度整合（修改腳本）

### Step 1：加入 import
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'stores'))
from universal_brain_wrapper import brain
```

### Step 2：啟動時註冊
```python
# main() 或初始化時
brain.register('my_job_name', universe='TW', job_type='nana')
```

### Step 3：執行中記錄
```python
# 發現信號時
brain.log(signals=[{'symbol': '2330.TW', 'action': 'buy', 'price': 890, 'score': 75}])

# 產生指標時
brain.log(metrics={'win_rate': 0.72, 'total_signals': 15, 'high_quality': 5})

# 發現問題時
brain.log(errors=['TWII 資料取得失敗'])

# 觀測時
brain.log(observation='VIX 突破 25，市場恐慌情緒上升')
```

### Step 4：結束時 flush
```python
# 腳本即將結束前
memory_ids = brain.flush()
print(f'Memory: {memory_ids}')
```

---

## 整合方式 B — 外部整合（不改腳本，推薦！）

在任何 isolated job 的 `message` 末尾加上 Python 呼叫：

```
cd C:\Users\USER\.openclaw\workspace\Tina_Quant_System && python my_script.py && \
python -c "from stores.brain_memory_cli import cmd_complete; \
import argparse; \
cmd_complete(argparse.Namespace(job='my_script', universe='TW', \
signals='[{\"symbol\":\"2330\",\"action\":\"buy\",\"price\":890,\"score\":75}]', \
metrics='{}', summary='my_script 完成', output=''))"
```

---

## 各 Job 整合模板

### Universe Scanner（已整合，示範）
```python
brain = BrainAwareExecutor(job_name=f'{universe}_scanner', universe=..., job_type='scanner')
ctx = brain.before_execute()
# ... 原邏輯 ...
brain.after_execute(success=True, summary=..., signals=..., metrics=...)
```

### Macro Job
```python
from stores.macro_st_memory_patch import macro_memory_integration
# ... 主邏輯 ...
macro_memory_integration('morning')  # 或 'afternoon'
```

### Nana/Leo Job
```python
import sys
sys.path.insert(0, r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores')
from universal_brain_wrapper import brain

brain.register('nana_v68', universe='TW', job_type='nana')
# ... 原邏輯 ...
brain.log(signals=entry_signals)
brain.log(metrics={'win_rate_estimate': 0.72, 'signals_total': len(entry_signals)})
# ... 結束 ...
brain.flush()
```

---

## 蒸餾流程（記憶如何變成智慧）

```
每日 20:00（每日輕度蒸餾）
  → 清理 short_term（>30天且無 links）
  → 更新 distillation_log

每週五 18:00（每週中度蒸餾）
  → 讀取 short_term 過去 14 天
  → Pattern 出現 ≥3 次 → 晉升 long_term/patterns.json
  → Lesson 內容 → 晉升 long_term/lessons.json
  → 計算每個 Pattern 的 hit_rate
  → 更新 distillation_log

每月最後週日 22:00（月度深度蒸餾）
  → 讀取 short_term 過去 90 天
  → hit_rate < 40% → status: 'inactive'
  → hit_rate ≥ 75% + occurrences ≥ 5 → status: 'confirmed'
  → 框架版本更新記錄

每週日 10:00（每週大腦蒸餾）
  → 蒸餾 macro + nana + leos + lessons
  → 更新 decision_patterns.json
  → 寫入 MEMORY.md
```

---

## 大腦系統與 Tina 主腦的連結

### Tina 主腦讀取流程
```
1. 每日早晨（07:00）讀取 brain_dashboard.json
2. 根據 short_term 摘要（昨日 Scanner/Macro/Nana/Leo 結果）做決策
3. 根據 long_term patterns 避開高風險標的
4. 根據 lessons 避免重複過去錯誤
5. 根據 watchlist 追蹤關注標的
```

### Dashboard 讀取方式（Agent 代碼）
```python
import json
from pathlib import Path

DASH_FILE = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\brain_dashboard.json')
with open(DASH_FILE) as f:
    dash = json.load(f)

print(dash['short_term']['total'])  # 近7天記憶總量
print(dash['long_term']['patterns']['total'])  # Patterns 總數
print(dash['working']['watchlist'])  # 觀察名單
```

---

## 記憶寫入優先順序

| 優先 | 情況 | mtype | expiry |
|:----:|:-----|:------|:-------|
| 1 | Scanner 發現 Top 5 信號 | decision | 60天 |
| 2 | Macro 重大預測變化 | observation | 30天 |
| 3 | 風控突破/錯誤 | lesson | 90天 |
| 4 | Pattern 出現 3 次 | → 晉升 long_term | — |
| 5 | Framework 版本更新 | framework_change | 365天 |
| 6 | 日常觀測 | observation | 30天 |

---

## 健康度指標

| 分數 | 等級 | 標準 |
|:----:|:----:|:-----|
| 80+ | 🟢 Excellent | short_term > 50 + patterns > 10 + growth 合理 |
| 60-79 | 🟡 Good | short_term > 20 + patterns > 5 |
| 40-59 | 🟠 Fair | short_term > 5 + patterns > 0 |
| < 40 | 🔴 Low | 低於這個需要緊急补充 |

---

_本指南版本：v1.0 | 更新日期：2026-05-08_