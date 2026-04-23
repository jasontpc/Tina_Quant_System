---
name: automation-team
description: Tina 自動化循環團隊 (Automation Team)。當需要執行、查看、或管理 Tina 的永續自動化改善循環（10步驟）時啟用。包括：啟動自動化迴圈、查看進度、管理排程、追蹤改善項目。
---

# Automation Team - 自動化循環團隊

## 團隊角色

| 成員 | 功能 | 觸發方式 |
|:-----|:-----|:---------|
| **AutoEngine** | 執行 10 步驟迴圈 | `python automation_loop.py` |
| **Scheduler** | 管理排程任務 | `python scheduler.py list` |
| **Monitor** | 追蹤進度 | `python progress_tracker.py` |

## 10 步驟循環流程

```
步驟1 → 步驟2 → 步驟3 → 步驟4 → 步驟5
   ↓                               ↑
步驟10 ← 步驟9 ← 步驟8 ← 步驟7 ← 步驟6
```

| 步驟 | 名稱 | 核心功能 |
|:----:|:-----|:---------|
| 1 | 分析失敗原因 | 找出交易虧損根本原因 |
| 2 | 安裝缺少技能 | 自動識別並安裝技能知識 |
| 3 | 擴充資料 | 抓取更多法人/價格資料 |
| 4 | 優化評分 | 調整評分權重 |
| 5 | 回測股票池 | 擴充後的股票池回測 |
| 6 | 分級策略 | Tier1/2/3 差異化進場 |
| 7 | 動態調整 | ATR 停損/持有期優化 |
| 8 | 權重優化 | 資金面與技術面配置 |
| 9 | 系統檢討 | 全面審視待辦事項 |
| 10 | 執行改善 | 根據建議付諸實踐 |

## 快速指令

```bash
# 啟動自動化迴圈
python automation_loop.py

# 查看進度
python progress_tracker.py

# 查看排程
python scheduler.py list

# 執行自動優化
python auto_optimizer.py

# 追蹤庫存
python stock_tracker.py
```

## 進度檔案位置

- 主進度: `memory/automation_progress.md`
- 每輪詳情: `memory/automation_cycle_YYYYMMDD.md`
- 步驟專用: `memory/step{N}-{name}-YYYYMMDD.md`

## 版本歷史

| 版本 | 日期 | 勝率 | 平均報酬 |
|:-----|:-----|:----:|:--------:|
| v4.21 | 2026-04-23 | 74.3% | +4.52% |
| v3 FINAL | 2026-04-23 | 100% | +3.93% |
| Nana v5.0 | 2026-04-23 | 62.1% | +1.59% |

## 相關團隊

- **Nana Team**: 波段交易系統 (teams/nana/)
- **Marcus**: 盤後分析
- **Tina (主)**: 量化核心

## 檔案架構

```
teams/automation/
├── TEAM.md                   # 團隊定義
├── SKILL.md                  # 本檔案
├── scripts/
│   ├── automation_loop.py    # 10步驟執行引擎
│   ├── scheduler.py          # 排程管理
│   ├── progress_tracker.py   # 進度追蹤
│   ├── auto_optimizer.py     # 自動優化器
│   └── stock_tracker.py      # 庫存追蹤
└── references/
    ├── automation-index.md   # 完整索引
    └── scheduler-ref.md      # 排程參考
```