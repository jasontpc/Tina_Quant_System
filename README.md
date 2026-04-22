# Tina Quant System

## 🎯 系統概述

Tina 是一個 AI 量化交易系統，專注於台股/美股 ETF 波段操作。

## 📁 專案架構

```
Tina_Quant_System/
├── core/                    # 核心系統
│   ├── tina_system.py      # Tina 主程式
│   └── monitor_rules.json   # 監控規則
├── api/                    # API 整合
│   ├── api_gateway.py       # 統一調用介面 + Rate Limiter
│   ├── twse_api_complete.py # TWSE OpenAPI 完整版
│   └── twse_endpoints.json  # 143 個 API 端點
├── strategies/              # 策略模組
│   ├── daily_report.py      # 每日報告
│   ├── step1_screen.py     # 第一階段篩選
│   ├── step2_ai_filter.py # AI 過濾
│   └── step3_execute.py    # 執行監控
├── backtest/                # 回測系統
│   ├── v3_12_top50.py     # v3.12 Top50 回測
│   └── loss_pattern_analysis.py # 虧損模式分析
├── data/                    # 資料庫
│   ├── tina_master.db      # 主資料庫
│   ├── watchlist.json      # 觀察名單
│   └── loss_rules.json     # 虧損規則
└── archive/                # 歸檔
```

## 👥 團隊角色

| 角色 | 核心任務 |
|:-----|:---------|
| **Architect** | 系統全局設計、任務分配 |
| **Quant Developer** | v3.13 策略開發與優化 |
| **Debugger** | 分析 Traceback、API 報錯 |
| **SRE** | Git 版本控制、檔案歸檔、API 限流監控 |
| **Backtester** | 完整年度回測、生成報告 |

## 📊 v3.12 系統效能

| 指標 | 數值 |
|:-----|:-----|
| 勝率 | 67.8% |
| 平均報酬 | +3.22% |
| 總信號 | 90 個 |
| 分析期間 | 2025-04 ~ 2026-04 |

## 🔧 使用方式

```python
from api_gateway import get_stock_price, get_top_gainers

# 取得股票現價
price = get_stock_price('3017')

# 取得熱門漲幅股
top10 = get_top_gainers()
```

## 📝 版本歷史

- **v3.12** (2026-04-22): 系統清理、API 整合、Loss Rules 自動化
- **v3.11** (2026-04-15): Relaxed filters, 71.4% WR
- **v3.03** (2026-03-31): Q1 2026 optimized, 66.7% WR

## 📄 授權

私人使用 - Jo & Tina AI
