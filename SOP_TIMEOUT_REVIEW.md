# Tina Quant System — Cron Job Timeout 檢討與改善 SOP

**版本：** v1.0 | **日期：** 2026-05-14 | **維護：** Tina

---

## 📊 Timeout 事件統計（2026-05-14 盤點）

### Timeout Jobs（需要修正 timeout）

| Job | 實際耗時 | 設定 timeout | 修正後 timeout | 原因 |
|:----|--------:|------------:|--------------:|:-----|
| Phase2: 7B 大師邏輯 | 604s | 600s | **900s** ✅ | ollama create + 寫入 Modelfile |
| Tina MEMORY 每日蒸餾 | 181s | 180s | **300s** ✅ | 蒸餾流程複雜，需要更多時間 |
| US Margin 每日分析 | 123s | 240s | **360s** ✅ | 資料處理量增加 |
| 08:30 開盤前預載 | 46s | 120s | ✅ 維持 | 僅 45s，但成功（預載腳本還在開發）|
| Ray 全語意固化重生（05:00）| 321s | 450s | ✅ 維持 | 需觀察下次執行 |
| 15:00 美股策略分析 | 184s | 180s | **300s** ✅ | 市場數據抓取延遲 |

### Gateway Restart Jobs（系統層級問題）

| Job | 錯誤訊息 | 根本原因 | 建議動作 |
|:----|:---------|:---------|:---------|
| Tina 自主決策五大層 | `cron: job interrupted by gateway restart` | Cold Start 時記憶體不足 | 檢查 Gateway OOM |
| Phase1: 7B 蒸餾 | 同上 | 同上 | 同上 |
| Tina 日誌晨間檢討 | 同上 | 同上 | 已禁用 |

---

## 🎯 Timeout 修正原則

### 1. 計算方式

```
正確 timeout = 實際執行時間 × 1.5 + Cold Start 預估（30-60s）
```

| 任務類型 | 典型 Cold Start | 建議 buffer |
|:---------|:---------------|:-----------|
| 簡單腳本（讀取/寫入）| 5-10s | +30s |
| 中等腳本（簡單計算）| 10-20s | +60s |
| Ollama 模型呼叫 | 30-60s | +120s |
| ollama create（模型燒錄）| 60-120s | +300s |
| 多步蒸餾（多個 ollama 呼叫）| 120-240s | +300s |

### 2. Timeout 等級分類

| 等級 | 建議 timeout | 適用場景 |
|:----:|------------:|:---------|
| **Fast** | 30-60s | 簡單查詢、訊息發送 |
| **Standard** | 120-180s | 一般分析腳本 |
| **Heavy** | 300-450s | 單次 Ollama 呼叫 |
| **Critical** | 600-900s | ollama create / 多步蒸餾 |
| **Research** | 1200s+ | 向量化回測（500檔）|

### 3. 常見任務的修正歷史

| 腳本 | 原始 timeout | 修正後 | 原因 |
|:-----|:------------:|:------:|:-----|
| 每日記憶蒸餾 | 180s | 300s | 蒸餾流程變複雜 |
| US Margin 分析 | 240s | 360s | 資料處理量增加 |
| Phase2 大師邏輯 | 600s | 900s | ollama create 燒錄太慢 |
| 開盤前預載 | 45s | 120s | 預載腳本優化 |

---

## 🔧 自我修復機制（已實作）

### ray_guard.py 的防 Timeout 機制

| 機制 | 說明 |
|:-----|:-----|
| `@ray_singleton` | VRAM 排隊，避免資源競爭 |
| `@io_singleton` | I/O 排隊，避免檔案衝突 |
| `@ray_singleton_high_priority` | 08:30 預載專用，60秒死鎖破門 |
| `@market_safe_guard` | 開盤禁區邏輯阻斷，避免高負載任務干擾實戰 |

### Cron Optimizer v2（tina_cron_optimizer_v2.py）

每個 Cron Job 失敗後：
1. 自動 +50% timeout（最多 3 次）
2. 記錄優化歷史到 `stores/cron_optimization_proposal_20260513.md`

---

## 🛡️ Gateway Restart 預防

### 原因分析
當 Gateway 在 Job 執行期間重啟，代表系統處於記憶體緊縮狀態。

### 建議動作
1. **檢查 Gateway 記憶體**：`openclaw gateway status`
2. **檢查 OOM log**：`stores/cron_governor_log.json`
3. **網卡驅動更新**：已知問題（1168.13 → 1168.23 待 Jo 確認）
4. **減少並發 Job**：錯開時間避免同時 loading 模型

### 緩解措施
- **錯開時間**：同類 Job 不要設定相同時間
- **staggerMs**：已對 14:00/17:00 的 Job 加入 300-600s 錯開
- **memory_distiller 分離**：daily（07:00）/ weekly（週五 19:30）/ monthly 分離

---

## 📋 Timeout 觀察清單

下次 Timeout 發生時，檢查清單：

- [ ] Job 實際執行時間是多少？（從 lastDurationMs 讀取）
- [ ] timeout 是否足夠？（actual × 1.5 + cold start）
- [ ] 是否是資源競爭？（ray_vram.lock 存在）
- [ ] 是否是 Cold Start 太慢？（model loading 時間）
- [ ] 是否有 Gateway Restart 跡象？（lastErrorReason: "interrupted by gateway restart"）

---

## 🚨 緊急處理 SOP

當一個 Job 連續 2 次 Timeout：

1. **第一時間**：手動增加 timeout +50%
2. **第二天**：檢查 `cron_governor_state.json` 的 activity_score
3. **第三天**：若仍失敗，發送 Telegram 警示通知 Jo
4. **根本解決**：檢查腳本本身是否需要優化（例如：減少 API 呼叫、簡化邏輯）

---

_Last updated: 2026-05-14 by Tina_
_下次檢查：2026-05-21_