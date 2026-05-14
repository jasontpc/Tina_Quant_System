# SOP_BRAIN_SLOW_THINKING.md — 大腦慢思考累積智慧標準作業程序

> 版本：v1.0  
> 建立：2026-05-08  
> 目的：讓 Tina 的 isolated jobs 不只是跑任務，而是能累積智慧、從經驗中學習

---

## 1. 核心理念

### 1.1 慢思考 vs 快思考

| | 快思考（快任務）| 慢思考（累積智慧）|
|--|-------------|----------------|
| **頻率** | 每小時、每日 | 每週、每月 |
| **目的** | 當下及時任務（掃描、風控）| 從歷史經驗中提煉智慧 |
| **輸出** | 當下結論 | 結構化知識 + SOP 更新 |
| **時間視角** | 現在 → 未來 | 過去 → 現在 → 未來 |

### 1.2 累積智慧的三大燃料

```
燃料一：經驗（Experience）
  └─ 每一筆交易決策的 outcome
  └─ 每一份 Macro 預測的準確度

燃料二：模式（Patterns）
  └─ 市場重複出現的規律
  └─ 我的判斷系統性偏差

燃料三：教訓（Lessons）
  └─ wins/ 正確的判斷邏輯
  └─ losses/ 錯誤的判斷邏輯 + 修正方式
```

---

## 2. 架構：Isolated Jobs → 寫入 → 累積 → 蒸餾

```
┌──────────────────────────────────────────────────────────────┐
│  Isolated Jobs（快思考，寫入結構化 JSON）                      │
│                                                              │
│  Nana 波段 v6.4 → nana_reports/daily_YYYYMMDD.json           │
│  Leo v6.5 → leos_reports/daily_YYYYMMDD.json                 │
│  Macro 預測 → macro_predictions/YYYYMMDD.json                 │
│  風控決策 → decisions/YYYYMMDD.json                           │
│  自選股監控 → watchlist_analysis/YYYYMMDD.json                │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  每週蒸餾 Job（慢思考，讀取一週 JSON → 蒸餾智慧）              │
│                                                              │
│  Tina 每週大腦蒸餾（週日 10:00）                              │
│  └─ 讀取 macro_predictions/*（一週）                        │
│  └─ 讀取 decisions/*（一週）                                 │
│  └─ 蒸餾：Macro 預測準確度、Lessons 提取、Pattern 發現        │
│  └─ 寫入：memory/weekly_distill_YYYYMMDD.md                  │
│  └─ 更新：SOP 修正建議                                        │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  每週 Macro 複審（週五 17:00，驗證 + 更新）                   │
│                                                              │
│  └─ 驗證本週 Macro 預測 vs 實際市場                           │
│  └─ 蒸餾：「預期 vs 實際」的偏差模式                          │
│  └─ 更新：SOP_MACRO_DAILY.md 第8章修正建議                    │
│  └─ 寫入：macro_weekly_review_YYYYMMDD.md                    │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  主腦讀取（Main Session，定期讀取蒸餾結果）                   │
│                                                              │
│  └─ 讀取 memory/weekly_distill_*.md                          │
│  └─ 讀取 macro_weekly_review_*.md                            │
│  └─ 更新：MEMORY.md 的「市場模型」章節                        │
│  └─ 更新：decision_patterns.json（系統性偏差）                │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Isolated Jobs 結構化輸出標準

每一個 isolated job 在執行完後，必須寫入一份 JSON 報告到 workspace。

### 3.1 輸出目錄結構

```
Tina_Quant_System/
  ├─ reports/
  │   ├─ nana/              ← Nana 波段每日報告
  │   │   └─ {date}.json
  │   ├─ leos/               ← Leo 科技波段每日報告
  │   │   └─ {date}.json
  │   ├─ macro/               ← Macro 每日預測報告
  │   │   └─ {date}.json
  │   ├─ decisions/           ← 風控/決策每日記錄
  │   │   └─ {date}.json
  │   └─ watchlist/           ← 自選股監控報告
  │       └─ {date}.json
  └─ distillations/           ← 蒸餾輸出（每週）
      ├─ weekly/
      │   └─ {date}.md
      └─ monthly/
          └─ {date}.md
```

### 3.2 JSON 報告標準格式

**Macro 每日預測（macro/{date}.json）**
```json
{
  "date": "2026-05-08",
  "type": "macro_daily",
  "geopolitical": {
    "forecast": "美中談判持續，關稅維持現狀",
    "confidence": 0.7,
    "actual": null
  },
  "economic": {
    "forecast": "CPI 年增 2.8%，Fed 暫停升息",
    "confidence": 0.65,
    "actual": null
  },
  "trend_theme": {
    "forecast": "AI 基礎建設持續吸金",
    "confidence": 0.75,
    "actual": null
  },
  "taiwan_impact": {
    "forecast": "台積電法說助攻，台股撐在 23000 以上",
    "confidence": 0.7,
    "actual": null
  }
}
```

**決策記錄（decisions/{date}.json）**
```json
{
  "date": "2026-05-08",
  "type": "decision_log",
  "decisions": [
    {
      "id": "20260508-001",
      "time": "09:15",
      "trigger": "Nana 波段 v6.4 發現 4532 RSI=25.8",
      "action": "WATCH（未進場）",
      "reasoning": "TWII OVERBOUGHT，全市場觀望",
      "outcome": null,
      "lesson_id": null
    }
  ],
  "lessons_learned": [],
  "anomalies": []
}
```

**Lesson 記錄（lessons/wins/{date}_{id}.md）**
```markdown
# Lesson {id}: 波段正確捕捉 RSI 超賣反彈

**日期**：2026-05-08  
**情境**：4532 RSI=25.8，Nana 發出 WATCH 訊號  
**決策**：觀望（未進場）  
**依據**：TWII OVERBOUGHT → 系統性風險  

**事後諸葛**：正確。市場在 RSI=25.8 並未立即反彈。  

**Pattern 提取**：  
- RSI 觸發超賣 + TWII OVERBOUGHT → 觀望
- RSI 觸發超賣 + TWII 中性/低估 → 考慮分批進場

**下次應用**：當 RSI < 30 且 TWII RSI > 70 時，提高警覺
```

---

## 4. 每週蒸餾流程（週日 10:00）

### 4.1 蒸餾 Job 輸入

| 來源 | 路徑 | 用途 |
|------|------|------|
| Macro 預測 | `reports/macro/*.json`（過去一週）| 計算預測準確度 |
| 決策記錄 | `reports/decisions/*.json`（過去一週）| 找出重複決策模式 |
| Lessons | `lessons/wins/*.md` + `lessons/losses/*.md`（過去一個月）| 蒸餾長期 Pattern |
| MEMORY.md | `MEMORY.md` | 讀取當前持倉視角 |

### 4.2 蒸餾 Job 輸出

**memory/weekly_distill_{date}.md** 包含：

```
## 本週 Macro 預測準確度

| 維度 | 預測正確 | 偏差 | 準確度 |
|------|---------|------|--------|
| 地緣政治 | 4/5 | 1 次（美中談判延後）| 80% |
| 總經數據 | 3/5 | CPI 偏高 0.2% | 60% |
| 趨勢主題 | 5/5 | — | 100% |
| 台股影響 | 4/5 | 一次誤判科技股回檔 | 80% |

## 本週新增 Pattern

### Pattern 1：AI 基礎建設 → 台積電 CoWoS → 光通訊落後補漲
**觀察**：本週 3 次出現此傳導鏈
**上次發生**：2026-04-15
**建議**：納入 SOP 光通訊追蹤清單

## 本週新 Lessons

### Lesson: 波段 - TWII OVERBOUGHT + 个股 RSI 超賣 → 觀望
（詳見 lessons/losses/...）

## 下週重點觀察

1. 美中 6 月談判結果
2. Nvidia GB300 量產時程
3. 台積電 CoWoS 產能利用率
```

### 4.3 蒸餾 Job Prompt（isolated session）

```
【每週大腦蒸餾 Job】

你是 Tina 的慢思考系統。請執行以下蒸餾任務：

1. 讀取以下目錄，取過去一週（不包含今天）的所有 JSON 報告：
   - C:\Users\USER\.openclaw\workspace\Tina_Quant_System\reports\macro\
   - C:\Users\USER\.openclaw\workspace\Tina_Quant_System\reports\decisions\
   - C:\Users\USER\.openclaw\workspace\Tina_Quant_System\reports\nana\
   - C:\Users\USER\.openclaw\workspace\Tina_Quant_System\reports\leos\

2. 讀取以下目錄，取過去一個月的 lessons：
   - C:\Users\USER\.openclaw\workspace\Tina_Quant_System\lessons\wins\
   - C:\Users\USER\.openclaw\workspace\Tina_Quant_System\lessons\losses\

3. 讀取 MEMORY.md（視角 anchor）：
   - C:\Users\USER\.openclaw\workspace\MEMORY.md

4. 蒸餾輸出（寫入）：
   - memory/weekly_distill_YYYYMMDD.md（YYYYMMDD 為上週五日期）

5. 蒸餾內容需包含：
   A. Macro 預測準確度（4 維度各別評分）
   B. 決策 Pattern（重複出現的判斷邏輯）
   C. Lessons 摘要（wins + losses 各 1-3 個重點）
   D. Pattern 更新建議（建議寫入 decision_patterns.json）
   E. 下週 3 個最重要觀察點
   F. 對 SOP 的修正建議（具體條款）
```

---

## 5. 每週 Macro 複審流程（週五 17:00）

### 5.1 複審 Job 輸入

讀取 `reports/macro/` 本週預測，與實際市場結果比對。

### 5.2 複審 Job 輸出

**macro_weekly_review_{date}.md** + **SOP_MACRO_DAILY.md 修正建議**

---

## 6. Isolated Jobs 結構化輸出改造清單

以下 jobs 需改造，使其在執行後寫入結構化 JSON：

| Job | 現況 | 改造目標 |
|-----|------|---------|
| Tina 晨間宏觀快報 | Prompt only | 執行後寫入 `reports/macro/{date}.json` |
| Tina 盤後宏觀整合報告 | Prompt only | 執行後寫入 `reports/macro/{date}.json`（update actuals）|
| Tina 風控檢查 | Prompt only | 執行後寫入 `reports/decisions/{date}.json` |
| Tina 自主決策五大層 | Prompt only | 執行後寫入 `reports/decisions/{date}.json` |
| Nana 波段 v6.4 | nana_v68.py 已有報告輸出 | 統一為 `reports/nana/{date}.json` |
| Leo v6.5 科技股波段 | leos_v65.py 已有輸出 | 統一為 `reports/leos/{date}.json` |

---

## 7. Decision Pattern DB（系統性偏差追蹤）

建立 `data/decision_patterns.json`：

```json
{
  "patterns": [
    {
      "id": "PATTERN-001",
      "name": "TWII OVERBOUGHT + 個股 RSI 超賣",
      "description": "當 TWII RSI > 70（OVERBOUGHT）時，個股 RSI 超賣訊號往往失效",
      "evidence_count": 12,
      "last_seen": "2026-05-08",
      "confidence": 0.85,
      "sop_reference": "SOP_MACRO_DAILY.md §3.2"
    },
    {
      "id": "PATTERN-002",
      "name": "AI 基礎建設傳導鏈",
      "description": "GB300 量產 → CoWoS 需求 ↑ → 光通訊落後補漲",
      "evidence_count": 5,
      "last_seen": "2026-05-01",
      "confidence": 0.7,
      "sop_reference": null
    }
  ],
  "偏差修正": {
    "系統性高估": [
      "小型股反彈幅度（平均高估 30%）"
    ],
    "系統性低估": [
      "光通訊補漲時機（平均低估 2 天）"
    ]
  }
}
```

---

## 8. MEMORY.md 結構更新

慢思考累積的智慧，最終要寫入 MEMORY.md 的以下章節：

```
MEMORY.md
  ├─ ## 市場模型（Market Model）
  │   ├─ 趨勢主題傳導鏈（最新）
  │   ├─ Pattern DB（decision_patterns.json 的摘要）
  │   └─ 系統性偏差清單
  │
  ├─ ## Lessons 精華
  │   ├─ wins/ 最近 10 個（按 date）
  │   └─ losses/ 最近 10 個（按 date）
  │
  └─ ## Macro 預測準確度追蹤
      ├─ 本月：地緣 75%、總經 65%、趨勢 85%、台股 80%
      └─ 上月：地緣 70%、總經 60%、趨勢 80%、台股 75%
```

---

## 9. 實施時間表

| 階段 | 內容 | 期限 |
|------|------|------|
| Phase 1 | 建立 `reports/` 目錄結構 + JSON 標準格式 | 2026-05-09 |
| Phase 2 | 改造 Macro jobs（晨間+盤後）寫入 JSON | 2026-05-09 |
| Phase 3 | 改造 Nana/Leo jobs 統一 JSON 格式 | 2026-05-12 |
| Phase 4 | 建立 decision_patterns.json | 2026-05-12 |
| Phase 5 | 每週蒸餾 Job 實作（週日 10:00）| 2026-05-11 |
| Phase 6 | 每週 Macro 複審 Job 實作（週五 17:00）| 2026-05-09 |
| Phase 7 | MEMORY.md 結構更新 + 主腦讀取流程 | 2026-05-13 |

---

## 10. 關鍵成功指標

- **Macro 預測準確度**：每月底結算，目標 70% 以上
- **Lesson 提取數量**：每週至少 2 個新 lesson（1 win + 1 loss）
- **Pattern 驗證率**：每季回測，目標 60% 以上
- **SOP 更新頻率**：每週至少 1 次修正建議
