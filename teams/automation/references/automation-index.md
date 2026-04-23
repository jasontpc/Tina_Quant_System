---
name: automation-index
description: Tina 量化系統的自動化索引樞紐。當需要快速查找任何自動化相關內容、查看系統狀態、追蹤所有進度檔案位置、或查找特定腳本和技能時使用。
---

# Automation Index - 自動化索引表

## Tina 自動化系統全景圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Tina 量化系統 - 自動化架構                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┐    ┌───────────────────┐    ┌───────────────────┐  │
│  │ automation-   │    │  automation-rules  │    │ automation-       │  │
│  │ index         │───▶│  (10步驟循環)      │───▶│ scheduler         │  │
│  │ (索引樞紐)     │    │                   │    │ (排程工具)         │  │
│  └───────────────┘    └───────────────────┘    └───────────────────┘  │
│         │                    │                       │               │
│         ▼                    ▼                       ▼               │
│  ┌───────────────┐    ┌───────────────────┐    ┌───────────────────┐  │
│  │ 技能、技能     │    │ stock-analyzer    │    │ stock-monitor     │  │
│  │ 腳本、進度     │    │                   │    │                   │  │
│  │ 檔案位置       │    │ bandwave_system   │    │ check_alerts.py   │  │
│  └───────────────┘    └───────────────────┘    └───────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                      資料流 / 進度追蹤                            │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  memory/automation_progress.md  (主進度)                           │ │
│  │  ├── step1-fail-YYYYMMDD.md  (失敗分析)                           │ │
│  │  ├── step2-skills-YYYYMMDD.md (技能安裝)                          │ │
│  │  ├── step3-data-YYYYMMDD.md  (資料擴充)                           │ │
│  │  ├── step4-scoring-YYYYMMDD.md (評分優化)                         │ │
│  │  ├── step5-pool-YYYYMMDD.md  (股票池)                             │ │
│  │  ├── step6-tier-YYYYMMDD.md  (分級策略)                           │ │
│  │  ├── step7-dynamic-YYYYMMDD.md (動態調整)                         │ │
│  │  ├── step8-weights-YYYYMMDD.md (權重優化)                         │ │
│  │  ├── step9-review-YYYYMMDD.md (系統檢討)                          │ │
│  │  └── step10-execute-YYYYMMDD.md (執行改善)                        │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 技能索引 (Skills)

| 技能名稱 | 功能 | 位置 |
|:---------|:-----|:-----|
| `automation-index` | 自動化索引樞紐 | `skills/automation-index/` |
| `automation-rules` | 10步驟循環規則 | `skills/automation-rules/` |
| `automation-scheduler` | 排程工具 | `skills/automation-scheduler/` |
| `stock-analyzer` | 股票分析/回測 | `skills/stock-analyzer/` |
| `stock-monitor` | 股票監控警示 | `skills/stock-monitor/` |
| `tw-stock-info` | 台股資料取得 | `skills/tw-stock-info/` |
| `yahoo-finance` | 美股/ETF資料 | `skills/yahoo-finance/` |

## 腳本索引 (Scripts)

### 波段系統核心腳本

| 腳本 | 功能 | 路徑 |
|:-----|:-----|:-----|
| `daily_report.py` | 每日收盤報告 | `skills/stock-analyzer/bandwave_system/daily_report.py` |
| `weekly_review.py` | 每週檢討 | `skills/stock-analyzer/bandwave_system/weekly_review.py` |
| `step1_screen.py` | 法人+技術篩選 | `skills/stock-analyzer/bandwave_system/step1_screen.py` |
| `step2_ai_filter.py` | AI語意過濾 | `skills/stock-analyzer/bandwave_system/step2_ai_filter.py` |
| `step3_execute.py` | 起漲點監控 | `skills/stock-analyzer/bandwave_system/step3_execute.py` |
| `dynamic_exit.py` | 動態停利停損 | `skills/stock-analyzer/bandwave_system/core/dynamic_exit.py` |

### 法人資料腳本

| 腳本 | 功能 | 路徑 |
|:-----|:-----|:-----|
| `fetch_institutional_finmind.py` | FinMind法人抓取 | `skills/stock-analyzer/scripts/fetch_institutional_finmind.py` |
| `sync_inst_to_master.py` | 法人資料同步 | `skills/stock-analyzer/scripts/sync_inst_to_master.py` |

### 回測腳本

| 腳本 | 功能 | 路徑 |
|:-----|:-----|:-----|
| `backtest_rsi_bollinger.py` | RSI+布林帶回測 | `skills/stock-analyzer/scripts/backtest_rsi_bollinger.py` |
| `simple_momentum_backtest.py` | MA動量策略 | `skills/stock-analyzer/scripts/simple_momentum_backtest.py` |
| `us_now.py` | 美股現況 | `skills/stock-analyzer/scripts/us_now.py` |

## 進度檔案索引

### 主進度檔案

| 檔案 | 說明 | 更新頻率 |
|:-----|:-----|:---------|
| `memory/automation_progress.md` | 自動化循環主進度 | 每步驟完成時 |
| `memory/heartbeat-state.json` | 心跳檢查狀態 | 每30分鐘 |

### 每日記憶

| 檔案 | 說明 |
|:-----|:-----|
| `memory/YYYY-MM-DD.md` | 每日工作日誌 |
| `memory/market-analysis.md` | Marcus盤後分析 |
| `memory/stock_alerts.md` | 股票警示記錄 |

### 自動化循環詳情

| 檔案 | 說明 |
|:-----|:-----|
| `memory/automation_cycle_YYYYMMDD.md` | 每輪完整報告 |
| `memory/step{N}-{name}-YYYYMMDD.md` | 各步驟專用檔案 |

## 股票池分級

### Tier1 - 科技/AI 主題股 (~30檔)
```
2330 台積電、3231 緯創、2379 瑞昱、3017 奇鋐、
2385 群電、2303 聯電、2454 聯發科、3034 聯詠、
6683 瑞鼎、6666 益登、3545 敦泰 等
```

### Tier2 - 相關供應鏈 (~20檔)
```
2317 鴻海、2382 廣達、3023 研華、3702 大聯大、
2456 奇景-KY、6116 彩晶、4952 凌威 等
```

### Tier3 - 藍籌/高息股 (~30檔)
```
2882 國泰金、2883 開發金、2891 中信金、2892 第一金、
2603 長榮、2610 華航、2801 彰銀、2812 台銀 等
```

### ETF (~21檔)
```
0050 元大台灣50、0056 元大高股息、00646 元大S&P500、
00662 富邦NASDAQ100、00713 元大高息低波、00757 統一FANG+、
00830 國泰永續高股息、00927 群益半導體 等
```

## 評分系統架構

```
總分 = 法人(40%) + 技術(35%) + 趨勢(25%)

法人評分 (40分)
├── 連續買超天數遞增 (0-70分)
└── 合力加成 (0-10分)

技術評分 (35分)
├── RSI (20分) - 50-65=+20, <50或>70=0
├── Bias (15分) -偏離MA程度
└── ATR (10分) - 波動調整

趨勢評分 (25分)
├── MA 斜率 (15分)
└── 動量 (10分)
```

## Veto 規則（阻擋進場）

| 條件 | 閾值 | 動作 |
|:-----|:-----|:-----|
| VIF 過低 | < 1.0 | 禁止進場 |
| RSI 過高 | > 70 (多頭) / > 65 (空頭) | 禁止進場 |
| 法人連續賣超 | ≥ 3天 | 禁止進場 |
| 成交量萎縮 | < MA50 的 50% | 禁止進場 |

## 動態市場判斷

| 市場狀態 | 持有期 | RSI 閾值 | VIF 閾值 |
|:---------|:------:|:--------:|:--------:|
| 過熱 (OVERBOUGHT) | 1-3天 | < 75 | ≥ 2.0 |
| 多頭 (BULL) | 5-7天 | < 70 | ≥ 1.5 |
| 盤整 (RANGE) | 5天 | < 65 | ≥ 1.8 |
| 空頭 (BEAR) | 3天 | < 60 | ≥ 2.0 |

## 目標與績效

| 指標 | 目標 | 目前已驗證 |
|:-----|:-----|:-----------|
| 勝率 | ≥ 60% | v2.52 達 63.2-63.3% |
| 平均報酬 | ≥ 1.5% | +1.59% (新池) |
| 每年交易次數 | 20-30次 | 6次 (需擴充) |
| 最大持有天數 | 7-10天 | 5-7天 |

## 常用命令

```bash
# 查看排程
openclaw cron list

# 查看日誌
openclaw logs

# 查看系統狀態
openclaw status

# 執行股票監控
python skills/stock-monitor/scripts/check_alerts.py

# 執行每日報告
python skills/stock-analyzer/bandwave_system/daily_report.py

# 查看自動化進度
cat memory/automation_progress.md
```

## 關鍵指標追蹤

| 指標 | 現況 | 更新時間 |
|:-----|:-----|:---------|
| TWII | 如 memory/market-analysis.md | 每日 16:30 |
| SPY | 如 memory/market-analysis.md | 每日 16:30 |
| 鴻海 (2317) | 成本 $209.50，現價 ~$210.50 | 即時 |
| 市場狀態 | 過熱 (OVERBOUGHT) | 2026-04-23 |

## 版本歷史

| 版本 | 日期 | 勝率 | 關鍵變更 |
|:-----|:-----|:----:|:---------|
| v2.52 | 2026-04-22 | 63.2% | 最佳已驗證參數 |
| v3.17 | 2026-04-23 | 100% | Veto 規則加入 |
| v3.18 | 2026-04-23 | 100% | 排除 2330 |
| v3 FINAL | 2026-04-23 | 100% | 整合最終版 |

_Last Updated: 2026-04-23_