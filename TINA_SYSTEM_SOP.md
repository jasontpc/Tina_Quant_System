# Tina 大腦系統標準作業程序 (SOP) v1.0

**版本：** v1.0  
**日期：** 2026-05-08  
**狀態：** 草稿

---

## 📋 系統概覽

### 目標
建立統一、整合、可維護的 Tina 量化交易大腦系統

### 核心原則
1. **簡單直接** — 一個腳本做一件事
2. **可追蹤** — 所有決策寫入 decision_log.md
3. **可學習** — 記憶回路閉合
4. **自動化** — 減少人工干預

---

## 🏛️ 系統架構

```
MEMORY.md（持倉、狀態）
       ↓ 讀取
┌─────────────────────────────────────┐
│  Layer 3: 感知分析                   │
│  tina_brain_core.py                │
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│  Layer 4: 專家委員會                │
│  量化/開發/風控 三方評分             │
└─────────────────────────────────────┘
       ↓
┌─────────────────────────────────────┐
│  Layer 5: 反思進化                  │
│  decision_log.md + lessons          │
└─────────────────────────────────────┘
       ↓
MEMORY.md（每日同步）
```

---

## 📁 腳本分類標準

### A. 大腦核心（Brain Core）
| 腳本 | 功能 | 執行頻率 |
|:-----|:-----|:--------:|
| `tina_brain_core.py` | 五大層統一決策 | 每 1h |
| `tina_integrated_monitor.py` | 整合監控 | 每 30m |

### B. 記憶系統（Memory）
| 腳本 | 功能 | 執行頻率 |
|:-----|:-----|:--------:|
| `tina_memory_sync.py` | MEMORY.md 同步 | AM/PM |

### C. 分析系統（Analysis）
| 腳本 | 功能 | 對應 Bot |
|:-----|:-----|:---------|
| `news_trends_cron.py` | News Trends | tina-reports |
| `etf_analysis_jo.py` | ETF 分析 | tina-reports |
| `tw_etf_daily.py` | TW ETF | tina-reports |

### D. 波段系統（Trading）
| 腳本 | 功能 | 對應 Bot |
|:-----|:-----|:---------|
| `nana_*.py` | Nana 波段 | main |
| `leo_*.py` | Leo 分析 | main |

---

## 🔄 標準作業流程

### 每日流程

| 時間 | 任務 | 腳本 | Bot |
|:-----|:-----|:-----|:----:|
| 07:00 | MEMORY AM 同步 | `tina_memory_sync.py` | main |
| 08:00 | News Trends AM | `news_trends_cron.py` | tina-reports |
| 08:00 | ETF 分析 | `etf_analysis_jo.py` | tina-reports |
| 08:00 | TW ETF | `tw_etf_daily.py` | tina-reports |
| 09:00 | 大腦整合監控 | `tina_integrated_monitor.py` | main |
| 10:00 | Leo 波段分析 | `leo_analyzer.py` | main |
| 每 30m | 健康監控 | `tina_integrated_monitor.py` | main |
| 每 1h | 五大層決策 | `tina_brain_core.py` | main |
| 16:35 | ETF 收盤更新 | `etf_daily_update.py` | tina-reports |
| 20:00 | News Trends Evening | `news_trends_cron.py` | tina-reports |
| 22:00 | MEMORY PM 同步 | `tina_memory_sync.py` | main |

---

## 📊 決策流程標準

### 進場決策（Full Think 模式）

```
1. 收到進場請求
     ↓
2. Layer 1 — 讀取 MEMORY.md 持倉
     ↓
3. Layer 2 — 風控邊界檢查（RSI<65、虧損<8%）
     ↓
4. Layer 3 — 感知分析（TWII RSI + 技術指標）
     ↓
5. Layer 4 — 專家委員會評分（三方投票）
     ↓
6. Layer 5 — 沙盒驗證（Paper Trade）
     ↓
7. 裁決：APPROVE / CAUTION / REJECT
     ↓
8. 等待 Jo 確認（60秒）
     ↓
9. 執行 + 寫入 decision_log.md
```

### 風控裁決標準

| RSI 條件 | 裁決 | 建議 |
|:---------|:-----|:-----|
| RSI < 40 | APPROVE | 超賣，積極進場 |
| RSI 40-65 | CAUTION | 觀望或小部位 |
| RSI > 65 | REJECT | 不進場 |
| TWII RSI > 85 | REJECT | 市場過熱 |

---

## 🗃️ DB 維護標準

### 更新頻率

| DB | 更新頻率 | Cron Job |
|:---|:--------:|:---------|
| yfinance.db | 每日 08:00 | `yfinance_daily.py` |
| tw_history.db | 每日 08:00 | `tina_daily_update.py` |
| us_history.db | 每日 08:00 | `tina_daily_update.py` |
| etf.db | 每日 16:35 | `etf_daily_update.py` |
| news_trends.db | 08:00/14:00/20:00 | `news_trends_cron.py` |

---

## 📝 記憶系統標準

### decision_log.md 格式

```markdown
## 決策日誌 {日期}

### 市場感知
- TWII RSI：{value}
- 持倉數量：{count}

### 專家委員會
- 評分：{score}（{verdict}）
- 理由：{reasons}

### 執行結論
- 結果：{SUCCESS/PARTIAL/FAILURE}
```

### lessons 寫入標準

| 情況 | 目錄 |
|:-----|:-----|
| 止損 >5% | `lessons/losses/` |
| 成功止盈 | `lessons/wins/` |
| 持有 >30天 + RSI>50 | `lessons/losses/` |

---

## 🚨 警報標準

### 緊急警報（立即通知）

| 條件 | 行動 |
|:-----|:-----:|
| TWII RSI > 90 | 發送 Telegram 警報 |
| 單筆虧損 >8% | 發送 Telegram 警報 |
| Gateway offline | 發送 Telegram 警報 |
| 持有 >30天 + RSI>50 | 發送 Telegram 警報 |

### 警告警報（下次心跳通知）

| 條件 | 行動 |
|:-----|:-----:|
| DB 5天未更新 | 記錄到 HEARTBEAT.md |
| Cron Job 失敗 3次 | 嘗試自動修復 |
| Session >5000 個 | 提醒清理 |

---

## 🔧 腳本命名標準

```
{功能}_{子功能}.py

範例：
- tina_brain_core.py          # 大腦核心
- tina_memory_sync.py        # 記憶同步
- tina_integrated_monitor.py  # 整合監控
- etf_analysis_jo.py         # ETF 分析（ Jo 用）
- leo_analyzer.py            # Leo 分析
- news_trends_cron.py        # News Trends 定時
```

---

## 📊 成功指標

| 指標 | 目標 | 目前 |
|:-----|:----:|:----:|
| Cron Error Jobs | 0 | ✅ 0 |
| 五大層執行率 | 100% | ✅ 已建立 |
| decision_log 完整度 | 100% | ✅ 已建立 |
| 記憶回路閉合 | 100% | ⚠️ 75% |

---

## 🔮 未來改善

### v1.1（短期）
- [ ] 合併 `tina_brain_monitor.py` 到 `tina_integrated_monitor.py`
- [ ] 合併 `tina_lifecycle_monitor.py` 到 `tina_integrated_monitor.py`
- [ ] 建立腳本對照表（README.md）

### v1.2（中期）
- [ ] 建立統一大腦協調器（tina_brain_coordinator.py）
- [ ] 實現 lessons 自動寫入
- [ ] 實現 decision_log 自動摘要

### v1.3（長期）
- [ ] 建立 Web UI 監控面板
- [ ] 建立 API 接口
- [ ] 建立移動端通知

---

## 📞 聯絡人

- **系統管理員：** Tina 大腦
- **緊急聯絡：** Jo（Telegram）

---

_Last update: 2026-05-08_
