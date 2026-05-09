# Tina 大腦記憶系統 — 標準作業程序
## Brain Memory System SOP
> 「你有記憶，但不知道自己是怎麼記憶的。」— 先建立規則，再談智慧。

---

## 一、記憶三層架構

```
┌─────────────────────────────────────────────────────────────┐
│                     Tina 大腦記憶系統                         │
├─────────────────────────────────────────────────────────────┤
│  【短期記憶 SHORT-TERM】← 工作記憶，隨取隨用，30天後衰減       │
│    stores/short_term/  （每日觀察、異常、新聞、決定）          │
│                                                             │
│  【工作記憶 WORKING】← 活躍上下文，決策進行中，跨session       │
│    stores/working/    （pending_decisions, active_context） │
│                                                             │
│  【長期記憶 LONG-TERM】← 蒸餾智慧，永久積累，跨時間            │
│    stores/long_term/   （patterns, lessons, frameworks）     │
├─────────────────────────────────────────────────────────────┤
│  【蒸餾連結 DISTILLATION】← 短期→長期的橋樑，規則驱动          │
│    distill_rules.md     （晉升標準 + 流程）                   │
│    distillation_jobs/   （自動化蒸餾腳本）                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、短期記憶（Short-Term Store）

### 2.1 存放位置
`C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\short_term\`

### 2.2 檔案命名
`{YYYYMMDD}_{type}_{source}.json`

類型（type）：
- `observation` — 市場觀察、異常、警訊
- `decision` — 交易決定（含理由）
- `news` — 重要新聞壓縮摘要
- `pattern` — 疑似規律（未確認）
- `lesson` — 失敗或成功經驗（當下記錄）
- `metric` — 策略績效指標

來源（source）：
- `macro_job`、`nana_job`、`leo_job`、`scanner`、`jo`、`brain`

### 2.3 短期記憶寫入規則
**任何時候都可寫入短期記憶**，觸發時機：

| 觸發條件 | 寫入類型 | 範例 |
|---------|---------|------|
| Macro Job 執行完畢 | `observation` | TWII單日跌>2%，附VIX變化 |
| Nana/Leo Job 輸出信號 | `decision` | 2330.TW買入信號，理由：均線多頭 |
| Universe Scanner 發現異常 | `pattern` | SOX30連續3天RSI>80 |
| Jo 直接指示 | `lesson` | Jo說「這次判斷失誤，原因：...」|
| 策略績效突然變差 | `metric` | 本週價值策略勝率降至40% |
| 新聞大事 | `news` | Fed突發聲明，壓縮成3句 |

### 2.4 短期記憶格式（JSON）
```json
{
  "id": "st_20260508_001",
  "type": "observation",
  "source": "macro_job",
  "timestamp": "2026-05-08T07:30:00+08:00",
  "expiry_days": 30,
  "tags": ["TWII", "VIX", "macro"],
  "summary": "TWII單日跌-2.3%，VIX升至22，為本週最大跌幅",
  "detail": "宏觀早報記錄的收盤數據：TWII: 22750, VIX: 22, 殖利率: 1.8%...",
  "importance": 7,
  "links": ["pattern_001", "decision_042"],
  "status": "active"
}
```

---

## 三、工作記憶（Working Store）

### 3.1 存放位置
`C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\working\`

### 3.2 核心檔案

#### `pending_decisions.json` — 等待執行的決定
```json
{
  "decisions": [
    {
      "id": "pd_001",
      "created": "2026-05-08T10:00:00+08:00",
      "symbol": "2330.TW",
      "action": "buy",
      "strategy": "nana_v68_growth",
      "signal_strength": 8.2,
      "reason": "均線多頭排列，RSI=55，成交量擴增",
      "pending_reason": "等待Leo科技股波段確認",
      "status": "pending",
      "deadline": "2026-05-08T14:00:00+08:00",
      "auto_expire": true
    }
  ]
}
```

#### `active_context.json` — 當前活躍上下文
```json
{
  "active_positions": [
    {
      "symbol": "2330.TW",
      "entry_date": "2026-05-05",
      "entry_price": 890,
      "size": 1000,
      "stop_loss": 860,
      "strategy": "nana_v68_value",
      "current_rsi": 62,
      "days_held": 3
    }
  ],
  "watchlist": ["AAPL", "NVDA", "2881.TW"],
  "alerts": [
    {"symbol": "VIX", "condition": ">25", "created": "2026-05-08T08:00:00+08:00"}
  ]
}
```

#### `memory_queue.json` — 等侍蒸餾的項目
```json
{
  "queue": [
    {
      "short_term_id": "st_20260501_015",
      "reason": "重複觀察到第3次",
      "queued_at": "2026-05-08T00:00:00+08:00",
      "priority": "high"
    }
  ]
}
```

---

## 四、長期記憶（Long-Term Store）

### 4.1 存放位置
`C:\Users\USER\.openclaw\workspace\Tina_Quant_System\stores\long_term\`

### 4.2 核心檔案

#### `patterns.json` — 市場規律庫
```json
{
  "patterns": [
    {
      "id": "pat_001",
      "name": "TWII -2% + VIX >20 = 次日反彈機率70%",
      "category": "market_anomaly",
      "universe": "TW",
      "first_observed": "2026-04-15",
      "occurrences": 12,
      "hit_rate": 0.75,
      "avg_gain": 1.2,
      "conditions": ["TWII_change<-2", "VIX>20", "非Fed會議週"],
      "status": "confirmed",
      "confidence": 8.5
    }
  ]
}
```

#### `lessons.json` — 學習教訓庫
```json
{
  "lessons": [
    {
      "id": "les_001",
      "type": "loss",
      "date": "2026-04-20",
      "symbol": "AAPL",
      "strategy": "growth",
      "loss_rate": -3.2,
      "summary": "營收YoY>20%但EPS未跟上，買入後回調",
      "root_cause": "单一營收指標不足以確認成長，需看EPS一致性",
      "lessons": ["需同時滿足營收YoY>15%且EPS YoY>10%",
                 "毛利率需穩定或上升"],
      "status": "archived"
    }
  ]
}
```

#### `frameworks.json` — 策略框架庫
```json
{
  "frameworks": [
    {
      "id": "fw_001",
      "name": "Nana波段價值進場框架",
      "universe": "TW",
      "created": "2026-03-01",
      "last_updated": "2026-05-01",
      "version": "6.8",
      "core_logic": "P/E 8-18 + P/B<2.5 + RSI 40-65 + 均線多頭",
      "entry_rules": ["規則1", "規則2"],
      "exit_rules": ["規則A", "規則B"],
      "win_rate": 0.72,
      "avg_holding_days": 18,
      "notes": "2026-05-01 v6.8: 加入成交量過濾"
    }
  ]
}
```

#### `macro_wisdom.json` — 總經智慧庫
```json
{
  "macro_predictions": [
    {
      "id": "mp_001",
      "date": "2026-05-01",
      "horizon": "1week",
      "topics": ["Fed利率", "TWII", "VIX"],
      "predictions": {
        "TWII": {"direction": "down", "magnitude": "-1~-2%", "confidence": 7},
        "VIX": {"direction": "up", "magnitude": "18-22", "confidence": 6}
      },
      "outcomes": {
        "TWII": {"actual": "-1.8%", "hit": true},
        "VIX": {"actual": "20.5", "hit": true}
      },
      "accuracy_score": 0.85
    }
  ]
}
```

---

## 五、蒸餾規則（Distillation Rules）

### 5.1 短期→長期晉升標準

**自動晉升（符合任一條件）：**

| 條件 | 目的地 | 說明 |
|------|--------|------|
| 同一 Pattern 觀察到 ≥3 次 | `patterns.json` | 從疑似升級為觀察規律 |
| Lesson（成功或失敗）| `lessons.json` | 每次交易結果都應記錄 |
| 預測準確度 >75% | `macro_wisdom.json` | 自動收錄進總經智慧 |
| Framework 修改 | `frameworks.json` | 版本更新時留log |
| Jo 明確指示 | 指定檔案 | Jo說「這個要記住」|

**手動晉升（Jo 觸發）：**
- Jo 可隨時要求「把這次決定寫入長期記憶」
- 格式：`@tina 記住這個：{描述}`

### 5.2 蒸餾流程

```
每日（自動）：
  IF short_term queue >= 5 items
     THEN 觸發「每日輕度蒸餾」
          → 合併相似項目
          → 衰減較舊項目（>14天且無重複觀察）

每週五 18:00（自動）：
  IF short_term total >= 15 items
     THEN 觸發「每週中度蒸餾」
          → 評估每項是否晉升長期
          → 更新 patterns.json hit_rate
          → 寫入 distillation_log

每月最後週日（自動）：
  觸發「月度深度蒸餾」
  → 全量審視 patterns.json（衰減hit_rate<50%）
  → 更新 frameworks 版本
  → 產生「一個新的觀察」寫入 short_term
```

### 5.3 短期記憶衰減規則

```
expiry_days: 30
若符合以下條件，自動刪除（不晉升）：
  1. 創建 > 30 天
  2. 未被任何 long_term 項目連結（links = []）
  3. links 中的目標已刪除

若符合以下條件，保留（expiry_days = 永久）：
  1. 已晉升至 long_term
  2. 被 Jo 標記為「keep」
  3. 重要性 ≥ 9/10 且非重複性資訊
```

---

## 六、自動化排程（Automated Jobs）

| Job ID | 名稱 | 時間 | 職責 |
|--------|------|------|------|
| daily_light_distill | 每日輕度蒸餾 | 20:00 每日 | 清理、合併、更新 |
| weekly_medium_distill | 每週中度蒸餾 | 週五 18:00 | 評估晉升、更新統計 |
| monthly_deep_distill | 月度深度蒸餾 | 每月最後週日 22:00 | 全量審視、框架更新 |
| memory_cleanup | 記憶清理 | 每月 1日 03:00 | 刪除過期、壓縮日誌 |

---

## 六-C、腳本 × 資料庫 × 記憶 完整對應圖

### 系統現況（2026-05-08）
```
腳本總數：20 個
活躍 Cron Jobs：9 個
已整合 BrainAware：1 個（universe_scanner）
待整合：8 個（活躍 Job）
資料庫總數：19 個
```

### DB 事件監控（stores/db_event_logger.py）
- **用途：** 所有 DB 的最後更新時間、異常偵測（大量寫入）
- **喚起：** `python stores/db_event_logger.py`
- **寫入記憶：** 重要 DB 寫入（yfinance/tw_history/us_history/sherry_sim_trades）自動寫入 short_term (metric, 7天)
- **Dashboard 整合：** DB last_updated → brain_dashboard.json 的 system_last_active

### 完整系統地圖（stores/full_system_mapper.py）
- **用途：** 審計全系統腳本 × DB 對應關係
- **喚起：** `python stores/full_system_mapper.py`
- **輸出：** `stores/full_system_map.json`

### 全系統 DB Schema（stores/db_audit_report.json）
- **用途：** 所有 DB 的 table 結構、索引狀況
- **喚起：** `python db_schema_auditor.py`

---

## 六-D、Isolated Jobs × 記憶系統 整合標準（Brain-Aware Protocol）

### 原則
**每個 isolated job 都是大腦的感測器 + 記憶寫入器。**

### 標準整合方式

#### Step 1：在腳本開頭加入 BrainAware
```python
import sys
sys.path.insert(0, str(Path(__file__).parent / 'stores'))
try:
    from brain_aware_executor import BrainAwareExecutor
    brain = BrainAwareExecutor(job_name='my_script', universe='TW', job_type='scanner')
    ctx = brain.before_execute()  # 讀取長期記憶脈絡
    # 可用 ctx['patterns']、ctx['active_positions'] 等做決策輔助
except:
    brain = None  # 降級方案
```

#### Step 2：在腳本結尾寫入短期記憶
```python
if brain:
    brain.after_execute(
        success=True,
        summary='本週掃描：X 檔中高質量',
        signals=[...],      # 買賣信號列表
        metrics={...},      # 績效指標
        output_file='...'   # 輸出檔路徑
    )
```

### 各類 Job 整合模板

| Job 類型 | 寫入記憶 | 職責 |
|:---------|:---------|:-----|
| Universe Scanner | observation + decision (Top 5) + metric | Scanner 完成後呼叫 `brain.after_execute()` |
| Macro Job | observation + forecast | 寫入 macro 觀測、預測方向共識 |
| Nana/Leo Job | decision + metric | 信號 + 勝率等 |
| 蒸餾 Job | pattern + lesson（寫入 long_term） | 讀取 short_term → 晉升 |
| 風控 Job | lesson (type=error/risk) | 突破風控條件時寫入 |

### Brain-Aware 讀取脈絡（before_execute）
```
ctx['patterns']        # Long-term patterns（universe 過濾，active only）
ctx['lessons']         # 近90天 lessons（相關性過濾）
ctx['active_positions'] # 目前持倉（可結合避開重複）
ctx['watchlist']       # 觀察名單
ctx['alerts']          # 當前警示
ctx['short_term_summary'] # 短期記憶總量（判斷是否需要蒸餾）
```

### 短期記憶類型對照
| mtype | 觸發時機 | expiry_days |
|:------|:---------|------------:|
| observation | Scanner/Macro 完成 | 30 |
| decision | 買賣信號、策略決定 | 60 |
| metric | 績效指標 | 30 |
| lesson | 錯誤、虧損、風控突破 | 90 |
| pattern | 疑似新規律（3次後晉升 long_term） | 30 |
| framework_change | 框架版本更新 | 365 |

---

## 七、與現有系統的連結

```
Macro Jobs → 寫入 short_term/observation
Nana/Leo Jobs → 寫入 short_term/decision + working/pending_decisions
Universe Scanner → 寫入 short_term/pattern（若發現異常）
Brain Weekly Distill → 讀取 short_term → 寫入 long_term
MEMORY.md（agent workspace）→ 讀取 long_term/macro_wisdom + patterns
```

---

## 八、禁忌（Red Lines）

1. **不准刪除已晉升 long_term 的項目** — 除非 Jo 明確指示
2. **不准遺失 Jo 的直接指示** — 任何 @tina 記住指令必須立即寫入
3. **不准在蒸餾時造假 hit_rate** — 必須基於真實數據計算
4. **長期記憶不輕言刪除** — 只能衰減（標記為 inactive），不物理刪除

---

_本 SOP 版本：v1.0 | 建立日期：2026-05-08_
<!-- test: 20260508 -->