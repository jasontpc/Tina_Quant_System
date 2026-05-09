# Nana 版本索引 (VERSION_INDEX)

**更新時間：** 2026-05-08  
**現況：** 已清理

---

## 📋 版本狀態

| 版本 | 檔案 | 狀態 | 備註 |
|:----:|:-----|:-----|:-----|
| **v6.8** | `nana_v68.py` | ⭐ **正式版** | Cron 活躍（faf759b4）|
| v6.6 | `archive/nana_v66.py` | 🔒 已封存 | 2026-05-08 移入 |
| v6.5 | `archive/nana_v65.py` | 🔒 已封存 | 2026-05-08 移入 |
| v6.4 | `archive/nana_v64.py` | 🔒 已封存 | 2026-05-08 移入 |
| v3 | `archive/nana_system_v3.py` | 🔒 已封存 | 2026-05-08 移入 |
| v3-quick | `archive/nana_system_v3_quick.py` | 🔒 已封存 | 2026-05-08 移入 |
| v2-full | `archive/nana_v2_full.py` | 🔒 已封存 | 2026-05-08 移入 |
| v2-optimizer | `archive/nana_v2_optimizer.py` | 🔒 已封存 | 2026-05-08 移入 |
| v2-test | `archive/nana_v2_test.py` | 🔒 已封存 | 2026-05-08 移入 |

---

## ⭐ 正式版： Nana v6.8

**檔案：** `nana_v68.py` (2701 bytes)  
**Cron Job：** `faf759b4` — Nana 波段v6.4  
**排程：** `0 8,10,13,15,17 * * 1-5`（交易日 5次）  
**Agent：** main（Tina）

---

## 📊 版本演進歷史

| 日期 | 版本 | 變更 |
|:----:|:----:|:-----|
| 2026-05-08 | v6.8 | ⭐ 設為正式版 |
| 2026-05-08 | v6.6-v6.4 | 移入 archive |
| 2026-05-08 | v2/v3 | 移入 archive |
| 2026-04-25 | v6.4 | 波段系統重啟 |

---

## 🔒 Archive 內容

```
archive/
├── nana_v64.py       # v6.4
├── nana_v65.py       # v6.5
├── nana_v66.py       # v6.6
├── nana_v2_full.py   # v2 完整版
├── nana_v2_optimizer.py  # v2 優化版
├── nana_v2_test.py   # v2 測試版
├── nana_system_v3.py # v3 系統
└── nana_system_v3_quick.py  # v3 快速版
```

**注意：** 如需恢復任何版本，從 archive 資料夾取回即可。

---

## 📋 活躍腳本（非版本分類）

| 腳本 | 功能 | Cron |
|:-----|:-----|:-----|
| `nana_v68.py` | 波段交易旗艦 | faf759b4 |
| `nana_band_system.py` | 波段系統核心 | — |
| `nana_backtrader.py` | 回測引擎 | — |
| `nana_autonomous_system.py` | 自主交易 | — |
| `nana_decision.py` | 決策模組 | — |
| `nana_scanner.py` | 市場掃描 | — |
| `nana_telegram.py` | 訊息通知 | — |

---

## 🚫 禁止事項

1. **禁止直接修改 nana_v68.py** — 修改前先備份到 archive
2. **禁止新增 Nana 版本** — 除非 v6.8 有重大問題
3. **禁止在 archive 建立新檔案** — 僅存放歷史版本

---

## 🔄 版本更新流程

```
1. 提出變更需求
         ↓
2. 在測試環境驗證（nana_sim_backtest.py）
         ↓
3. 如果成功，更新 nana_v68.py
         ↓
4. 將舊版移入 archive
         ↓
5. 更新本文件
```

---

_Last update: 2026-05-08_
