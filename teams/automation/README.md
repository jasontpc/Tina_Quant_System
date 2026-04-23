# Tina Automation Team - 操作說明

## 團隊簡介

Automation Team 是 Tina 量化系統的**永續優化引擎**，負責執行 10 步驟循環的持續改善。

## 快速開始

### 1. 啟動自動化迴圈

```bash
cd Tina_Quant_System/teams/automation
python scripts/automation_loop.py
```

### 2. 查看當前進度

```bash
python scripts/progress_tracker.py
```

### 3. 管理排程

```bash
python scripts/scheduler.py list        # 列出所有排程
python scripts/scheduler.py templates    # 顯示範本
python scripts/scheduler.py add "daily-report" "30 16 * * *" "python daily_report.py"
```

## 10 步驟循環

每次迴圈執行以下步驟：

1. **分析失敗原因** - 找出交易虧損根本原因
2. **安裝缺少技能** - 自動識別並安裝技能知識
3. **擴充資料** - 抓取更多法人/價格資料
4. **優化評分** - 調整評分權重
5. **回測股票池** - 擴充後的股票池回測
6. **分級策略** - Tier1/2/3 差異化進場
7. **動態調整** - ATR 停損/持有期優化
8. **權重優化** - 資金面與技術面配置
9. **系統檢討** - 全面審視待辦事項
10. **執行改善** - 根據建議付諸實踐

## 進度追蹤

### 主進度檔案
位置：`memory/automation_progress.md`

### 每輪完整報告
位置：`memory/automation_cycle_YYYYMMDD.md`

### 步驟專用檔案
位置：`memory/step{N}-{name}-YYYYMMDD.md`

## 自動化腳本

| 腳本 | 功能 |
|:-----|:-----|
| `automation_loop.py` | 10 步驟執行引擎 |
| `scheduler.py` | 排程管理工具 |
| `progress_tracker.py` | 進度追蹤 |
| `auto_optimizer.py` | 自動策略優化 |
| `stock_tracker.py` | 庫存追蹤 |

## 版本歷史

| 版本 | 日期 | 勝率 | 平均報酬 | 信號數 |
|:-----|:-----|:----:|:--------:|:------:|
| v4.21 | 2026-04-23 | 74.3% | +4.52% | 230 |
| v4.24 | 2026-04-23 | 53.8% | +1.75% | 2098 |
| v3 FINAL | 2026-04-23 | 100% | +3.93% | 6 |
| Nana v5.0 | 2026-04-23 | 62.1% | +1.59% | 58 |

## 與其他團隊協作

```
Automation Team (永續優化)
       ↓
  ┌────┴────┐
  ↓         ↓
Nana Team  Tina 主系統
(波段)     (高勝率)
```

## 關鍵指標目標

| 指標 | 目標 | 目前 |
|:-----|:-----|:-----|
| 勝率 | ≥ 60% | 74.3% ✅ |
| 平均報酬 | ≥ 1.5% | +4.52% ✅ |
| 股票池覆蓋 | 200+ 檔 | 131 檔 |
| 年交易次數 | 20-30 次 | 230 信號 |

---

_Last Updated: 2026-04-23_