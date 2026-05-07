# Tina 團隊結構健檢報告
# 2026-05-07 16:50

---

## 📊 檔案數量（teams/）

| 團隊 | .py 檔案 | 狀態 |
|:-----|:--------:|:-----:|
| Nana | 67 | 🔴 失控 |
| Ray | 32 | 🟡 需整理 |
| Maggy | 28 | 🟡 需整理 |
| Leadtrades/Leo | 36 | 🟡 需整理 |
| Vogel | 16 | 🟡 需整理 |
| Sherry | 9 | 🟢 可接受 |
| Leo（主） | 6 | 🟢 可接受 |
| **合計** | **194** | |

---

## 🔴 致命缺陷 #1：版本淹沒

### Nana — 67 個檔案

**版本混戰：**
```
nana_v2.py, v4, v5, v53, v54, v55, v56, v57, v58, v6, v64, v65, v66, v67, v68
nana_system_v3.py, nana_system_v3_quick.py
nana_backtest.py, nana_improved_v2.py, nana_realistic_backtest.py
nana_sim_backtest.py, nana_stress_test.py
backtest_final.py, backtest_quick.py, historical_backtester.py
```

**問題：**
- 沒有人知道哪個是「正式版」
- v68 是最新的，但 v65/v66/v67 是啥？
- 多個 backtest 版本不知道哪個被 cron 調用

**改善方案：**
```
archive/nana/
  ├── old/
  │   ├── nana_v2.py ~ v63  (全部移入)
  │   ├── nana_backtest_v1.py 等舊版 backtest
  ├── active/
  │   └── nana_v68.py   (唯一正式版)
  └── cron/
      └── 只調用 archive/active/nana_v68.py
```

---

## 🔴 致命缺陷 #2：功能重疊

| 團隊 | 重疊症狀 |
|:-----|:---------|
| **Leo vs Leadtrades** | `leo_autonomous.py` vs `leo_autonomous_v2.py` vs `leo_master.py` vs `leos_v65.py` vs `leos_v68.py` — 到底哪個在跑？ |
| **Nana 多版本** | `nana_v68.py` vs `nana_system_v3.py` — 哪個是主力？ |
| **Ray** | `dca_backtest.py` vs `ray_backtester.py` vs `ray_market_backtest.py` — 用途各不同但名稱相似 |

---

## 🟡 中度缺陷 #3：職責分工混淆

### Leo vs Leadtrades 重疊
```
leo/          vs  leadtrades/leos/
leo_autonomous.py     leos_v65.py
leo_analysis.py        leos_v68.py
leo_core_v2.py         leos_daily_review.py
```

**問題：**
- `leo/` 6 個檔案 vs `leadtrades/leos/` 36 個檔案，差距太大
- 有兩個 Leo 一個在 teams/leo，一個在 teams/leadtrades/leos
- 沒有明確說明哪個是 AI 分析，哪個是交易執行

**改善方案：**
```
teams/leo/           # AI 分析 + 策略研發
  ├── leo_analysis.py
  ├── leo_autonomous_ai_chain.py
  └── leo_failure_db.py

teams/leadtrades/    # 實際交易執行
  ├── leos_v68.py    # 正式交易腳本（由 cron 調用）
  ├── leos_daily_review.py
  └── leos_trades.json
```

---

## 🟡 中度缺陷 #4：Cron 調用混乱

**不知道哪些腳本被 cron 調用：**
- Nana 的 67 個檔案中，到底哪個在 `*/20 0-23` 被呼叫？
- Leo 的 36 個檔案中，cron 叫哪一個？

**建議：**
在每個團隊的 `INDEX.md` 或 `README.md` 清楚標明：
```
## Cron 調用
- nana_v68.py  →  cron: */20 0-23
- leos_v65.py  →  cron: 0 9 * * 1-5
```

---

## 🟡 中度缺陷 #5：BACKTEST 結果散落

```
teams/nana/reports/       ← 空的？（需要確認）
teams/leads/trades/reports/
teams/maggy/reports/
teams/ray/reports/
```

**改善方案：**
- 每個團隊統一把 backtest 結果寫入 `teams/{team}/reports/backtest_latest.json`
- cron 調用時自動更新，INDEX.md 指向這個檔案

---

## ✅ 現況健康的項目

| 項目 | 說明 |
|:-----|:-----|
| **Sherry（9個）** | 輕量級，職責清晰（DCA + ETF） |
| **Leo 主（6個）** | 從 teams/leo 看得出是分析腳本，非交易腳本 |
| **Tina 核心** | `tina_think.py` / `tina_weekly_reflection.py` / `tina_health_check.py` 都在正確位置 |
| **團隊文檔** | `分工.md` / `策略地圖.md` / `SHARED_TEAM_PROTOCOL.md` 齊備 |

---

## 🛠️ 改善方案（優先順序）

### P0（立即執行）

**1. 清理 Nana 版本洪水**
- 現有 nana_v2~v67 → 移入 `archive/nana/old/`
- 只保留 `nana_v68.py` 為正式版
- cron 明確指向 `teams/nana/nana_v68.py`

**2. 確認 leadtrades/Leo 的正式版**
- `leos_v65.py` 還是 `leos_v68.py` ？
- 確認 cron 叫哪個，其他移 archive

### P1（本週內）

**3. 建立 Cron 對照表**
```
| Cron ID | 團隊 | 腳本 | 頻率 |
|---------|------|------|------|
| 98b172e3 | Leo | leos_v65.py | 平日09:00 |
| faf759b4 | Nana | nana_v68.py | */20 |
```

**4. 建立 `teams/{team}/INDEX.md`**
每個團隊目錄下建立 INDEX.md，說明：
- 正式版腳本名稱
- Cron 調用方式
- 最新表現數據（勝率/報酬）

**5. 清理 Maggy 28 → 留下 3-5 個**

### P2（長期重構）

**6. 統一 backtest 格式**
所有團隊的 backtest 結果寫入 `teams/{team}/reports/latest.json`，格式一致

**7. 合併 Leo + Leadtrades**
確認 teams/leo 是「研究」，teams/leadtrades/leos 是「執行」

**8. 清理 Ray**
32 個 → 留下 5-8 個核心腳本

---

## 📋 INDEX.md 模板

```markdown
# {Team} — 任務索引

## 正式版腳本
- `v68.py` — 主要交易邏輯（Cron 調用）

## Cron 對照
| 時間 | 腳本 | 說明 |
|:-----|:-----|:-----|
| */20 0-23 | v68.py | 波段掃描 |

## 績效
- 勝率：67.8%
- 平均報酬：+3.97%

## Archive
- `v2.py` ~ `v67.py` → 移至 `archive/`
```

---

## 🚀 立即行動（Jo 確認後執行）

1. **合併 Nana 版本**（v2~v67 → archive/old/，只留 v68）
2. **確認 Leo 正式版**（leos_v65 或 leos_v68？）
3. **建立 Nana INDEX.md**（含 cron/績效/archive 位置）

---

_Last updated: 2026-05-07 16:50_