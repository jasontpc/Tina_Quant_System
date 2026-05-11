# Tina 大腦慢思考檢討報告
**日期：** 2026-05-11 17:04
**性質：** 全面系統審查 + SOP 重建 + 自動化排程優化

---

## 一、現狀診斷（Slow-Think 引擎）

### 🔴 緊急問題

| 問題 | 嚴重度 | 根因 |
|:-----|:------:|:-----|
| Cron Governor 10次連續錯誤 | 🔴 P0 | Telegram bot token missing — delivery 層級設定錯誤 |
| Tina MEMORY 每日同步 2次 timeout | 🟠 P1 | 120s timeout 不夠，light distillation 需下調複雜度或增加timeout |
| gateway_ok: false | 🔴 P0 | OpenClaw Gateway 連線異常，影響 Cron Governor 判斷 |

### 🟡 系統問題

| 問題 | 嚴重度 | 說明 |
|:-----|:------:|:-----|
| Vegas Tunnel 無自動化掃描 | 🟡 P2 | 只有手動按鈕，沒有 end-of-day 批量掃描 |
| US 個股無 daily 分析排程 | 🟡 P2 | US AI Tech 只做廣度，沒有深度 Vegas 隧道分析 |
| Streamlit Cloud 更新後無驗證 | 🟡 P2 | 依賴被動回報，應主動驗證 |
| 4個 Cron Job 處於 error/delivery fail 狀態 | 🟠 P1 | Governor/風控/MEMORY/每日同步 |

### ✅ 今日成果

| 項目 | 狀態 |
|:-----|:----:|
| Vegas Tunnel 研發完成（EMA 144/169/576/676）| ✅ |
| TW 500檔 批量掃描（13秒 / 419檔）| ✅ |
| Streamlit 整合（TW + US）| ✅ |
| Cloud 部署成功 | ✅ |

---

## 二、專家委員會裁決

### 📈 量化分析師（35%）
- **勝率框架：** Vegas 策略需經過 100根K線回測驗證才能實盤
- **當前狀態：** 只完成廣度掃描（419檔），未做個股回測
- **建議：** 先跑 Top 20 BUY 候選的回測（MA20/MA60 進場，Fib TP 1-4 出場）

### ⚙️ 資深開發者（35%）
- **架構觀察：** Cron 系統完整（12 jobs），但有 3個處於 error 狀態
- **優先修復：** Governor token error → 否則所有 announce 都會失敗
- **Vegas 自動化：** 現有架構可支撐 end-of-day job，不需新建底層

### 🛡️ 風控長（30%）
- **TWII RSI 84 過熱：** 全市場警訊，所有 Trend-following 策略應謹慎
- **持有天數：** 需確認 2376/3034/2379 等是否接近危險線（>25天）
- **建議：** 現有 Tina Cron v2 每3小時監控足夠，Vegas 應設定 RSI 門檻

**委員會裁決：** 總分 +25（CAUTION）→ 建議觀望改善，優先修復基礎設施

---

## 三、SOP 標準作業程序（重建）

### SOP-001：Vegas Tunnel 每日掃描流程

```
觸發時間：每日 16:30（TW 收盤後）
執行腳本：scripts/vegas_bulk_scan.py
範圍：TOP 500 TW stocks
產出：vegas_tunnel_scan.json

Step 1：過濾 BUY signal（score ≥ 50）
Step 2：按照 score 排序，取 Top 10
Step 3：檢查每檔的 tunnel 狀態
  - BULL + EMA12 confirmed → WATCH LIST
  - FAKEOUT → 排除
  - INSIDE_TUNNEL → 觀望名單
Step 4：產出 Telegram 摘要報告
Step 5：寫入 decision_log.md
```

### SOP-002：Cron Job 健康度檢查（每小時）

```
Governor 每小時監控以下指標：
1. 所有 jobs 的 lastRunStatus
2. consecutiveErrors ≥ 2 → 發出 Warning
3. consecutiveErrors ≥ 3 → 發出 Alert + 嘗試自動修復
4. 修復順序：timeout → 重試 / delivery error → 跳過並通知
```

### SOP-003：Streamlit Cloud 部署驗證

```
觸發條件：git push 後 3分鐘
驗證流程：
1. 檢查 share.streamlit.app 可訪問
2. 確認 Single Stock Deep Analysis 頁面有 Vegas Tunnel 區塊
3. 點擊 Vegas 分析按鈕，確認有輸出（不報錯）
4. 若失敗：git checkout rollback + 通知 Jo
```

### SOP-004：Vegas Tunnel 進場評估

```
進場前必須滿足：
1. TWII RSI < 75（市場不过热）
2. H1 tunnel (EMA144/169) > H4 tunnel (EMA576/676) — 多頭背景確認
3. Price > EMA144 AND Price > EMA169 — 價格在隧道上方
4. EMA12 > EMA144 AND EMA12 > EMA169 — 濾波器確認
5. 持有天數 < 25天
6. 移動停損：SL = EMA169 - 1%

進場後：
- TP1（55 fib）：立即收割 30%
- TP2（89 fib）：再收割 30%
- TP3（144 fib）：持有到隧道回調
- TP4（233 fib）：紀律收割

風控：
- 最大持有天數：10天（隧道策略不走長線）
- SL：跌破 EMA169 立刻停損
```

---

## 四、改善計劃（自動化排程）

### Phase 1：緊急修復（今天）

| Job | 動作 | 期限 |
|:----|:-----|:-----|
| Cron Governor | 檢查 Telegram token 設定，確認 delivery 設定正確 | 今天 |
| Tina MEMORY sync | timeout 120s → 180s，降低 light distillation 複雜度 | 今天 |
| 3個 error jobs | 分析錯誤日誌，逐一修復 | 今天 |

### Phase 2：Vegas 自動化（明天）

| Job | 時間 | 功能 |
|:----|:-----|:-----|
| Vegas Daily Scan (TW) | 每日 16:30 | TW 500檔 Vegas 批量掃描 |
| Vegas Daily Scan (US) | 每日 06:30 | US 科技股 Vegas 批量掃描 |
| Vegas Top 10 Watch | 每日 07:00 | Vegas WATCH LIST Telegram 摘要 |

### Phase 3：系統強化（這週）

| 優化項目 | 說明 |
|:---------|:-----|
| Cron Governor 自動修復 | consecutiveErrors ≥ 3 時自動重啟 job |
| Decision Log 自動化 | 所有進場/出场決策自動寫入 decision_log.md |
| Streamlit 驗證 Cron | 每次 push 之後自動驗證部署狀態 |

---

## 五、自動化排程建議（新增 Job）

| Job Name | 排程 | Timeout | Priority |
|:---------|:-----|:-------:|:--------:|
| Vegas TW 每日掃描 | `0 16 * * 1-5` | 300s | 🟢 高 |
| Vegas US 每日掃描 | `0 6 * * 1-5` | 300s | 🟢 高 |
| Tina 收盤 summary | `0 17 * * 1-5` | 120s | 🟡 中 |
| Streamlit 部署驗證 | Push觸發鉤 | 60s | 🟡 中 |

---

## 六、模板：每日大腦同步格式

```
## 每日大腦同步 — YYYY-MM-DD HH:MM

### 市場狀態
- TWII: XXXX | RSI: XX | 狀態: [BULL/BEAR/OVERHEAT]
- SPY:  XXXX | RSI: XX | 狀態: [BULL/BEAR/OVERHEAT]

### 持倉健康
- [代碼] 持有X天 | RSI: XX | vs SL: XX%
- [代碼] 持有X天 | RSI: XX | vs SL: XX%

### Vegas 掃描結果
- BUY signals: X 檔（Top: 代碼1, 代碼2...）
- WATCH: X 檔
- FAKEOUT: X 檔

### Cron 系統狀態
- ✅ OK: X jobs
- ⚠️ WARNING: X jobs
- 🔴 ERROR: X jobs

### 明日行動
1. [具體行動]
2. [具體行動]
```

---

_本報告由 Tina 大腦 v3.6 慢思考引擎產出_
_下次檢討：2026-05-12 17:00_