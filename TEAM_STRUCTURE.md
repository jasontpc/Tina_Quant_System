# Tina 系統團隊組織架構 v1.0

**版本：** v1.0  
**日期：** 2026-05-08  
**狀態：** ⭐ 正式版

---

## 🏛️ 核心團隊（3個）

| 團隊 | 角色 | 負責人 | 核心腳本 |
|:-----|:-----|:-------|:---------|
| **Nana** | 波段交易系統 | Tina | `nana_v68.py` |
| **Leo** | 科技股分析 | Tina | `leo_analyzer.py` |
| **Ray** | ETF DCA 管理 | Tina | `ray_etf_dca.py` |

---

## 📊 支援團隊（3個）

| 團隊 | 角色 | 狀態 |
|:-----|:-----|:-----|
| **Sherry** | ETF 分析參考 | ⚠️ 觀察中 |
| **Maggy** | 美股追蹤 | ⚠️ 觀察中 |
| **Tina Brain** | 系統協調 | ⭐ 主核心 |

---

## 🔒 封存團隊（5個）

| 團隊 | 原因 |
|:-----|:-----|
| `vogel` | 實驗性，已停用 |
| `automation` | 功能重疊，已整合 |
| `leadtrades` | 功能不明 |
| `reports` | 重疊已整合 |
| `data` | 功能重疊 |

---

## 🎯 團隊職責定義

### Nana — 波段交易
```
職責：台股個股波段操作
範圍：2330, 2382, 3034 等科技股
腳本：nana_v68.py
Cron：faf759b4（5次/日）
```

### Leo — 科技股分析
```
職責：台股 AI/科技股分析
範圍：2454, 2317, 3034 等
腳本：leo_analyzer.py
Cron：6263e6d0（5次/日）
```

### Ray — ETF DCA
```
職責：ETF 定期定額管理
範圍：0050, 00646, 00713 等
腳本：ray_etf_dca.py
Cron：f051f79e（16:10每日）
```

---

## 📋 Cron Job 分工

| Bot | Agent | Cron Jobs | 團隊 |
|:----|:------|:----------|:-----|
| @Na8888bot | main | 健康監控、MEMORY、Gateway | Tina Brain |
| @Rayray888bot | tina-reports | News、ETF、分析報告 | Ray + Sherry + Maggy |

---

## 🔄 自動化標準程序

### 每日流程（06:00-22:00）

| 時間 | 任務 | 團隊 |
|:-----|:-----|:-----|
| 06:00 | Wake-up 健康檢查 | Tina Brain |
| 07:00 | MEMORY AM 同步 | Tina Brain |
| 08:00 | News Trends AM | tina-reports |
| 08:00 | ETF 分析 | Ray |
| 08:00 | TW History 更新 | Leo |
| 09:00 | 大腦整合監控 | Tina Brain |
| 10:00 | Leo 波段分析 | Leo |
| 每30m | 系統監控 | Tina Brain |
| 每1h | 五大層決策 | Tina Brain |
| 16:35 | ETF 收盤更新 | Ray |
| 20:00 | News Trends Evening | tina-reports |
| 22:00 | MEMORY PM 同步 | Tina Brain |

---

## 🧠 決策流程標準

### 進場請求流程

```
1. Jo 發送進場請求
         ↓
2. Tina Brain Layer 1-5 決策
         ↓
3. APPROVE → 等待 Jo 確認
         ↓
4. Jo 確認 → 執行
         ↓
5. 結果寫入 decision_log.md
         ↓
6. 如果止損 → 寫入 lessons/losses/
```

---

## 📊 成功指標

| 指標 | 目標 | 目前 |
|:-----|:----:|:----:|
| Cron Error | 0 | ✅ |
| 五大層執行率 | 100% | 75% |
| decision_log 完整度 | 100% | 70% |
| 版本穩定性 | nana_v68 | ✅ |

---

## 🔮 迭代改善

### 每日改善
- Tina Brain 每小時自動檢查
- decision_log 每日摘要

### 每週改善
- 週日 10:00 大腦回顧
- 清理無用檔案

### 每月改善
- 版本審計
- 腳本優化

---

_Last update: 2026-05-08_
