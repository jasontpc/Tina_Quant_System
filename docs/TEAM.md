# Tina 運維開發團隊

## 團隊成員

| 角色 | 技能檔案 | 核心任務 |
|:-----|:---------|:---------|
| **Architect** | `skills/tina-architect/` | 系統全局設計、任務分配 |
| **Quant Developer** | `skills/tina-quant/` | v3.13 策略開發與優化 |
| **Debugger** | `skills/tina-debugger/` | 分析 Traceback、API 錯誤 |
| **SRE** | `skills/tina-sre/` | Git 版本控制、檔案歸檔 |
| **Backtester** | `skills/tina-backtester/` | 完整年度回測、生成報告 |

## 如何觸發團隊成員

| 關鍵字 | 觸發角色 |
|:--------|:---------|
| "系統架構"、"任務分配" | Architect |
| "策略開發"、"v3.13"、"參數優化" | Quant Developer |
| "Error"、"Traceback"、"Bug" | Debugger |
| "Git"、"歸檔"、"清理" | SRE |
| "回測"、"backtest"、"勝率" | Backtester |

## 協作流程

```
用戶請求
    ↓
Architect (分析需求)
    ↓
根據類型分派 → Quant / Debugger / SRE / Backtester
    ↓
執行任務
    ↓
Architect (整合結果)
    ↓
回報用戶
```

## 緊急應變

| 情況 | 處理的角色 |
|:-----|:-----------|
| API 403 錯誤 | SRE + Debugger |
| 策略邏輯錯誤 | Quant + Backtester |
| 系統崩潰 | Architect + SRE |
