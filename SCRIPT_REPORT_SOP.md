# Tina 系統腳本工作報告標準作業程序 v1.0

**版本：** v1.0  
**日期：** 2026-05-08  
**狀態：** ⭐ 正式版

---

## 📋 腳本分類與報告標準

### A. 大腦核心（Brain Core）

| 腳本 | 功能 | 報告標準 | 頻率 |
|:-----|:-----|:---------|:-----:|
| `tina_brain_core.py` | 五大層決策 | ✅ 必須報告：Layer 1-5 決策結果 | 每 1h |
| `tina_integrated_monitor.py` | 整合監控 | ✅ 必須報告：健康狀態 + 五大層 | 每 30m |
| `tina_decision_trigger.py` | 決策觸發器 | ⚠️ 僅異常時報告 | 手動 |

---

### B. 記憶系統（Memory）

| 腳本 | 功能 | 報告標準 | 頻率 |
|:-----|:-----|:---------|:-----:|
| `tina_memory_sync.py` | MEMORY.md 同步 | ✅ 必須報告：同步狀態 | AM/PM |
| `tina_health_status_writer.py` | 健康狀態寫入 | ⚠️ 僅變更時報告 | 每 30m |
| `tina_brain_monitor.py` | 大腦監控 | ⚠️ 僅異常時報告 | 每 30m |

---

### C. 分析系統（Analysis）

| 腳本 | 功能 | 報告標準 | 頻率 |
|:-----|:-----|:---------|:-----:|
| `news_trends_cron.py` | News Trends | ✅ 必須報告：6國新聞摘要 | 08:00/14:00/20:00 |
| `etf_analysis.py` | ETF 分析 | ✅ 必須報告：RSI + Bias | 每日 08:30 |
| `daily_db_update.py` | DB 每日更新 | ⚠️ 僅異常時報告 | 每日 08:00 |
| `tina_paper_trading.py` | Paper Trade | ✅ 必須報告：沙盒模擬結果 | 每日 16:30 |

---

### D. 波段系統（Trading）

| 腳本 | 功能 | 報告標準 | 頻率 |
|:-----|:-----|:---------|:-----:|
| `leo_analyzer.py` | Leo 波段分析 | ✅ 必須報告：進場/出場建議 | 每交易日 5次 |
| `nana_v68.py` | Nana 波段交易 | ✅ 必須報告：交易結果 | 每交易日 5次 |
| `ray_etf_dca.py` | Ray DCA 管理 | ✅ 必須報告：DCA 狀態 | 每日 16:10 |

---

### E. 自動化改善（Auto Improve）

| 腳本 | 功能 | 報告標準 | 頻率 |
|:-----|:-----|:---------|:-----:|
| `tina_auto_improve.py` | 系統自動化改善 | ✅ 必須報告：Cron 健康 + DB 狀態 | 每 2h |

---

## 📊 報告輸出格式標準

### 格式 1：決策報告（五大層）

```
📊 【Tina 決策報告】{時間}

Layer 1 — 市場感知
- TWII RSI：{value}
- 持倉數量：{count}

Layer 2 — 風控邊界
- RSI > 65：{count} 檔
- 持有 > 30天：{count} 檔

Layer 3 — 專家委員會
- 評分：{score}（{verdict}）

Layer 4 — 裁決
- {APPROVE/CAUTION/REJECT}

Layer 5 — 行動
- {action}
```

### 格式 2：系統健康報告

```
🏥 【Tina 健康報告】{時間}

Cron Job 健康度：
- OK：{count}
- Error：{count}
- Idle：{count}

記憶系統：
- MEMORY.md：{size} bytes
- decision_log：{count} 筆
- lessons：wins={w}, losses={l}

DB 狀態：
- yfinance.db：{size}MB
- tw_history.db：{size}MB
```

### 格式 3：分析報告

```
📊 【{系統} 分析報告】{時間}

{分析內容}

⚠️ 警示：{count} 檔過熱
✅ 健康：{count} 檔正常
```

---

## ⏰ 排程時間表

| 時間 | 腳本 | 報告類型 | Bot |
|:-----|:-----|:---------|:----:|
| 07:00 | `tina_memory_sync.py` | MEMORY AM 同步 | main |
| 08:00 | `daily_db_update.py` | DB 更新 | — |
| 08:00 | `news_trends_cron.py` | News AM | tina-reports |
| 08:30 | `etf_analysis.py` | ETF 分析 | tina-reports |
| 09:00 | `tina_integrated_monitor.py` | 健康報告 | main |
| 每30m | `tina_brain_monitor.py` | 監控 | main |
| 每1h | `tina_brain_core.py` | 決策報告 | main |
| 14:00 | `news_trends_cron.py` | News PM | tina-reports |
| 16:10 | `ray_etf_dca.py` | DCA 報告 | tina-reports |
| 16:30 | `tina_paper_trading.py` | Paper Trade | main |
| 20:00 | `news_trends_cron.py` | News Evening | tina-reports |
| 22:00 | `tina_memory_sync.py` | MEMORY PM 同步 | main |

---

## 🚨 報告標準規則

### 必須報告的情況

| 情況 | 報告级别 | 動作 |
|:-----|:--------:|:-----|
| Cron Job Error | 🚨 緊急 | 立即通知 |
| RSI > 85（大盤）| 🚨 緊急 | 立即通知 |
| 虧損 > 8% | 🚨 緊急 | 立即通知 |
| 持有 > 30天 + RSI > 50 | ⚠️ 警告 | 下次心跳 |
| DB 5天未更新 | ⚠️ 警告 | 下次心跳 |
| 進場/出場執行 | ✅ 一般 | 彙報 |

### 禁止過度報告

| 情況 | 原因 |
|:-----|:-----|
| Idle Cron Job | 正常排程等待 |
| 健康系統正常運行 | 避免噪音 |
| 重複相同的市場狀態 | 避免冗餘 |

---

## 📊 Cron Job 對照表

| Job ID | 腳本 | 頻率 | 報告標準 |
|:-------|:-----|:-----|:---------|
| `a6d89b10` | price_check.py | 每日3次 | ✅ 必須 |
| `d78a40b2` | tina_brain_core.py | 每1h | ✅ 必須 |
| `94238b98` | tina_auto_improve.py | 每2h | ✅ 必須 |
| `6533a29f` | Tina 風控檢查 | 每15m | ✅ 必須 |
| `ff547cbe` | Tina 心跳監控 | 每1h | ⚠️ 僅異常 |
| `afa6812d` | news_trends_cron.py | 14:00 | ✅ 必須 |
| `18a4b1ae` | news_trends_cron.py | 20:00 | ✅ 必須 |
| `f051f79e` | ray_etf_dca.py | 16:10 | ✅ 必須 |
| `8c337856` | GUARD 軍工掃描 | 09:00/15:00 | ⚠️ 僅異常 |
| `6263e6d0` | leo_v65.py | 每交易日5次 | ✅ 必須 |
| `faf759b4` | nana_v68.py | 每交易日5次 | ✅ 必須 |

---

## 🔧 腳本優先級分類

### 🚨 高優先級（立即處理）

| 腳本 | 原因 |
|:-----|:-----|
| `tina_brain_core.py` | 核心決策系統 |
| `tina_auto_improve.py` | 系統健康監控 |
| `leo_analyzer.py` | 波段分析 |
| `nana_v68.py` | 波段交易 |

### ⚠️ 中優先級（每日處理）

| 腳本 | 原因 |
|:-----|:-----|
| `news_trends_cron.py` | 新聞資訊 |
| `etf_analysis.py` | ETF 分析 |
| `tina_memory_sync.py` | 記憶同步 |
| `ray_etf_dca.py` | DCA 管理 |

### 📝 低優先級（必要時處理）

| 腳本 | 原因 |
|:-----|:-----|
| `daily_db_update.py` | 後台維護 |
| `finmind_fetcher.py` | 資料更新 |
| `tina_health_status_writer.py` | 後台寫入 |
| `tina_brain_monitor.py` | 監控 |

---

## 📋 工作報告檢查清單

### 每日開始檢查

- [ ] 昨夜 News Trends 已發送？
- [ ] 昨夜 Cron Job 錯誤？
- [ ] MEMORY.md 已同步？
- [ ] DB 已更新？

### 每日結束檢查

- [ ] 今日決策已記錄？
- [ ] 今日 lessons 已寫入？
- [ ] MEMORY PM 已同步？
- [ ] 明日排程已確認？

---

_Last update: 2026-05-08_
