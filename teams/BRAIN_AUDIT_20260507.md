# Tina 團隊大腦檢討報告
**日期：** 2026-05-07
**評估：** Tina Brain v3 系統性審計

---

## 📊 團隊結構總覽

| 團隊 | 市場 | 腳本 | 紙本交易 | 大腦智能 | 狀態 |
|:----:|:----:|:-----|:-------:|:-------:|:----:|
| Leo | TW+US | leos_v65.py | ✅ 121口 | ✅ | ⚠️ DB stats失效 |
| Nana | TW個股 | nana_v6.py | ❌ 0口 | ✅ | ⚠️ 無交易紀錄 |
| Ray | TW+US ETF | ray_etf_dca.py | ✅ 757口 | ❌ | ✅ |
| Maggy | TW全市場 | maggy_*.py | ❌ | ❌ | 🔴 cron error |
| Sherry | ETF | sherry_*.py | ❌ | ❌ | 🔴 cron idle |

---

## 🔴 P0 — 立即修復

### 1. leos_trades.json Stats 欄位壞死
**問題：** `stats` 欄位停留在 `{total:0, wins:0, losses:0, total_pnl:0}`，與真實資料嚴重不符（真實：83W/14L/587,109）

**影響：** 每日報告的 Win Rate / PnL 數字錯誤

**根因：** `save_trades()` 有在寫 stats，但 `load_trades()` 初始化時 stats 就是 `{total:0, wins:0, losses:0, total_pnl:0}` — stats 沒跟著每次交易即時更新

**復原：** stats 應該每次 close trade 時重新計算（closed trades 動態加總），而不是累積更新

**行動：**
- [ ] 修復 `save_trades()`：每次平倉後重新計算 stats from scratch
- [ ] 修「excess_positions_reduced」佔太多筆（19筆同日同價出清2382），這些該視為正常平倉，不是異常

---

### 2. US 股息 current_price 缺失
**問題：** US 開倉部位的 `current_price` 欄位不存在，`pnl_pct` 為 `N/A`

**影響：** 停利/停損判斷失效（系統無法計算 US 倉位的即時帳面損益）

**根因：** `leos_daily_review.py` 有 `get_current_prices()` 抓 yfinance，但結果沒有更新到 `leos_trades.json` 的 `current_price` 欄位

**行動：**
- [ ] 在 `save_trades()` 或daily review结束前，将 `current_price` 写入 trade 记录
- [ ] 添加 `pnl_pct` 動態計算

---

### 3. Nana autonomous_trades.json 為空
**問題：** Nana 團隊的交易記錄檔是空的（0筆）

**影響：** 無法追蹤 Nana 的真實交易表現、無法計算勝率

**根因：** `autonomous_trader.py` 可能根本沒有寫入 autonomous_trades.json，或者寫入格式不符

**行動：**
- [ ] 檢查 `autonomous_trader.py` 的 `save_trades()` 邏輯
- [ ] 確認 Nana 的 cron job 為何顯示 error

---

## 🔴 P1 — 嚴重（影響Cron自動化）

### 4. 兩個Cron Job 持續 Error
| Job ID | 名稱 | 問題 |
|:-------|:-----|:-----|
| `27597611-...` | Nana 每日DB收盤更新 | error |
| `618aa329-...` | Tina 全團隊整合 | error |

**行動：**
- [ ] 手動跑一次這兩個 cron job 看錯誤訊息
- [ ] 修復後 `--expect-final` 開啟

---

### 5. leos_daily_review.py 日報無主動 Telegram 發送
**問題：** 腳本輸出結果（print），但沒有主動推送到 Telegram

**現況：** 只有 `openclaw cron` 的 delivery 機制，未啟用 `--expect-final` 時結果不會發送

**行動：**
- [ ] 確認 `Leo 每日Paper Trade檢討` cron 已設定 `--expect-final`（已確認有）
- [ ] 建議新增 `push_telegram()` 直接從腳本發送，防止 cron delivery 失效

---

## 🟡 P2 — 改善項目

### 6. 法人資料更新的 cron 太多太分散
| Cron | 時間 | 問題 |
|:-----|:-----|:-----|
| TW法人資料每日更新 30 16 | 30 16 | 可能是多餘的 |
| Tina 每日DB收盤更新 0 16 | 0 16 | 與 TW法人衝突 |
| Nana 每日DB收盤更新 30 16 | 30 16 | error |

**行動：**
- [ ] 合併 TW 法人資料更新到 `Tina 每日DB收盤更新`（0 16）
- [ ] 移除 `Nana 每日DB收盤更新`，改由 Nana 自己的 cron 處理

---

### 7. 缺乏統一的失敗報警機制
**問題：** cron job failed 時只有少數有 failure-alert

**行動：**
- [ ] 對所有 cron job 啟用 `--failure-alert` 并設定 `failure-alert-after 2`
- [ ] 避免連續失敗2次才報警（及時發現問題）

---

### 8. 缺少跨團隊的統一日報
**問題：** 每個團隊各自為政，沒有一份「Tina 全系統每日總結」

**行動：**
- [ ] 合併到 `Tina 全團隊整合` cron job（需先修復 error 狀態）
- [ ] 報告格式：Leo PnL + Nana 訊號 + Ray DCA + 大盤狀態

---

## ✅ 已正常運作

- **Leo v6.5 雙市場版** — 13 TW + 21 US 股票，cron 正常驅動
- **Ray DCA** — 757筆交易記錄，cron 正常
- **Tina 大腦監控** — 每30分鐘健康檢查
- **每日排程** — 16:30 / 23:00 收盤報告

---

## 🛠️ 預防措施

| 措施 | 說明 |
|:-----|:-----|
| **Stats 即時更新鉤子** | 每次 close trade 時觸發 stats 重新計算 |
| **Cron failure-alert** | 所有 cron job 設定 `--failure-alert-after 2` |
| **日終一致性檢查** | 每天 23:00 跑一次「DB一致性檢查腳本」 |
| **日終DB備份** | `leos_trades.json` 每天備份到 `backup/` |
| **Leo/US 即時價格寫入** | `current_price` 欄位每次 review 更新 |
| **跨團隊總結報告** | 合併到 `Tina 全團隊整合`（待修復） |

---

## 📋 立即行動清單

1. [ ] 修復 `leos_trades.json` stats 即時更新
2. [ ] 修復 US `current_price` 寫入
3. [ ] 檢查 Nana `autonomous_trades.json` 為何為空
4. [ ] 調查並修復兩個 error cron job
5. [ ] 合併 TW法人 cron 到 Tina 每日DB收盤更新
6. [ ] 啟用所有 cron failure-alert

---

_報告：Tina Brain v3 — 2026-05-07 14:11_
