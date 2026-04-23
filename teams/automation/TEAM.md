# Tina 自動化循環團隊 (Automation Team)

## 團隊定位

Automation Team 是 Tina 系統的**永續優化引擎**，負責執行 10 步驟循環的持續改善。

## 團隊成員

| 成員 | 角色 | 功能 |
|:-----|:-----|:-----|
| **AutoEngine** | 自動化執行器 | 執行 10 步驟循環 |
| **Scheduler** | 排程管理 | 管理 cron 任務 |
| **Monitor** | 進度監控 | 追蹤迴圈進度 |

## 10 步驟循環

| 步驟 | 名稱 | 功能 |
|:----:|:-----|:-----|
| 1 | 分析失敗原因並修正 | 找出問題，**當日發現、當日處理** |
| 2 | 安裝缺少技能 | 自動識別並安裝技能知識 |
| 3 | 擴充資料 | 抓取更多法人/價格資料 |
| 4 | 優化評分 | 調整評分權重 |
| 5 | 回測股票池 | 擴充後的股票池回測 |
| 6 | 分級策略 | Tier1/2/3 差異化進場 |
| 7 | 動態調整 | ATR 停損/持有期優化 |
| 8 | 權重優化 | 資金面與技術面配置 |
| 9 | 系統檢討並立即執行 | 全面審視，**當日發現、當日處理** |
| 10 | 新增建議並立即執行 | 系統新增其他建議，**並立即執行所有建議事項** |

## 檔案架構

```
automation/
├── TEAM.md                     # 本檔案
├── SKILL.md                    # 自動化技能定義
├── README.md                   # 操作說明
├── scripts/
│   ├── automation_loop.py      # 10步驟執行引擎
│   ├── scheduler.py            # 排程管理工具
│   ├── progress_tracker.py    # 進度追蹤
│   ├── auto_optimizer.py      # 自動優化器
│   └── alert_system.py        # 警示系統
├── references/
│   ├── automation-index.md     # 完整索引
│   ├── scheduler-ref.md       # 排程參考
│   └── version-history.md     # 版本歷史
└── memory/
    └── automation_progress.md  # 主進度檔
```

## 使用方式

### 啟動自動化循環

```bash
python automation_loop.py
```

### 查看進度

```bash
python scheduler.py list
```

### 手動觸發步驟

```bash
python automation_loop.py --step 1    # 只執行步驟1
python automation_loop.py --cycle 3   # 執行到第3輪完成
```

## 進度檔案

- **主進度**: `memory/automation_progress.md`
- **每輪詳情**: `memory/automation_cycle_YYYYMMDD.md`
- **步驟專用**: `memory/step{N}-{name}-YYYYMMDD.md`

## 關鍵指標追蹤

| 指標 | 目標 | 目前 |
|:-----|:-----|:-----|
| 勝率 | ≥ 60% | 74.3% (v4.21) |
| 平均報酬 | ≥ 1.5% | +4.52% (v4.21) |
| 股票池 | 200+檔 | 131檔 |
| 年交易次數 | 20-30次 | 230信號 |

---

_Last Updated: 2026-04-23_