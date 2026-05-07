# Tina 系統健檢報告
# 更新：2026-05-07 21:10

## ✅ 已處理項目（2026-05-07）

| 項目 | 狀態 | 說明 |
|:-----|:----:|:-----|
| Nana 版本洪水 | ✅ 已清理 | 12個舊版移入 `archive/old/` |
| maggy.db 空殼 | ✅ 已修復 | `system_status.py` 加 table guard |
| rsi.db / limitup.db 用途 | ✅ 已確認 | 不在 cron 使用，可觀察 |
| Teams INDEX.md | ✅ 已建立 | Nana/Leo/Maggy/Vogel/Sherry/Ray 全部建立 |

---

## 🏗️ 架構缺陷（仍需處理）

### 1. 腳本淹沒在雜草中（770 個 .py 檔案）

**問題：** 根目錄有 ~200 個腳本，無法分辨哪些是活躍/廢棄

**需清理（明顯廢棄）：**
```
fix_tg.py / fix_tg2-6.py    — Streamlit 修復實驗後留下
fix_form.py / fix_form_session.py / fix_form_us.py
fix_secret.py / fix_secret2.py
fix_p1.py / fix_scope.py
check_2382.py / check_token.py / check_twii.py / check_us_price.py
check_button.py / check_dbs.py / check_inst.py / check_leos.py
debug_find.py / debug_scope.py / debug_secret_name.py
commit_fix.py / patch_daily_review.py
verify.py / verify_fix.py / verify_latest_data.py / verify_trends_db.py
```

**建議：** 廢棄腳本移入 `archive/debug/` 或 `archive/fix/`，活躍腳本留在 `teams/` 或 `scripts/`

---

### 2. 備份目錄混亂

```
backup_20260502/
backup_20260502_1704/
```
建議合併或刪除舊的

---

## 🗄️ 資料庫問題（仍需處理）

### 空DB現況（0 字節 = 從未建立 table）

| DB | 大小 | 狀態 | 說明 |
|:---|-----:|:-----|:-----|
| `maggy.db` | 0 MB | ✅ 已確認廢棄 | `system_status.py` 已加 guard |
| `limitup.db` | 4 KB | 📌 待觀察 | 不在 cron 使用，可能永遠是空的 |
| `rsi.db` | 0 MB | 📌 待觀察 | `system_optimizer.py` 提到但實為 `maggy_rsi.db` |

### 已確認正常的 DB

| DB | 狀態 | 說明 |
|:---|:----:|:-----|
| `leo_stocks.db` | ✅ | `stock_tracking` 有數據，`price_history`/`signals` 預設為空 |
| `nana_stocks.db` | ✅ | 同上，設計如此 |
| `yfinance.db` | ✅ | Maggy 實際寫入位置 |

### finmind.db 更新（仍落後）

| DB | 大小 | 更新 | 說明 |
|:---|-----:|:-----|:-----|
| `finmind.db` | 0.8 MB | 2026-04-30 | ⚠️ 落後 7 天，新 API URL 已更換為 `api.finmindtrade.com` |

**建議：** 確認新 FinMind API token 正常運作後，更新 `finmind.db` 寫入腳本


---
## ⚠️ 高優先級（P2）

1. **清理根目錄廢棄 debug/fix 腳本** → 移入 `archive/debug/`
2. **確認 finmind.db 更新腳本** → 新 API 是否正常寫入
3. **備份目錄清理** → 合併 `backup_20260502/`

---
## 低優先級（長期）

- Nana 版本合併（9個→1個） ✅ 已完成
- cron jobs 功能分類（目前38個）
- scripts/ vs teams/ vs skills/ 邊界澄清

---

_Last updated: 2026-05-07 21:10_

## 🏗️ 架構缺陷

### 1. 腳本淹沒在雜草中（770 個 .py 檔案）

**問題：** 根目錄有 ~200 個腳本，無法分辨哪些是活躍/廢棄

**需清理（明顯廢棄）：**
```
fix_tg.py / fix_tg2-6.py    — 實驗後留下的
fix_form.py / fix_form_session.py / fix_form_us.py
fix_secret.py / fix_secret2.py
fix_p1.py / fix_scope.py
fix_stats_writeback.py
check_2382.py / check_token.py / check_twii.py / check_us_price.py
check_button.py / check_dbs.py / check_inst.py / check_leos.py
debug_find.py / debug_scope.py / debug_secret_name.py
debug_send.py / debug_show.py / debug_ws.py
find_broker.py / find_fn.py / find_inst.py / find_lines.py
find_mkt.py / find_pt.py / find_send.py / find_telegram.py
commit_fix.py / patch_daily_review.py
show_form.py / show_func.py / show_pnl.py / show_scan.py
verify.py / verify_fix.py / verify_latest_data.py / verify_trends_db.py
expand_*.py  (大量 expand_db*.py / expand_us_*.py)
```

**建議：**
- 活躍腳本移入 `scripts/` 或 `teams/` 目錄
- 廢棄腳本移入 `archive/` 
- 制定命名規範（以 `_` 結尾 = 實驗/臨時）

---

### 2. Nana 版本過多

```
nana_v520.py - nana_v528.py  (9個版本，只有一個是活躍的)
nana_analysis.py / nana_rsi.py / nana_today.py
```

**建議：** 保留 v528，其餘移入 archive，確定哪個是正式版

---

### 3. 備份目錄混亂

```
backup_20260502/
backup_20260502_1704/
```
建議合併或刪除舊的

---

## 🗄️ 資料庫問題

### 空DB（0 字節 = 可能有問題）

| DB | 大小 | 更新 | 狀態 |
|:---|-----:|:-----|:-----|
| leo_stocks.db | 0 MB | 2026-05-06 | ⚠️ 空的 |
| nana_stocks.db | 0 MB | 2026-05-06 | ⚠️ 空的 |
| maggy.db | 0 MB | 2026-05-06 | ⚠️ 空的 |
| limitup.db | 0 MB | 2026-05-05 | ⚠️ 空的 |
| rsi.db | 0 MB | 2026-05-06 | ⚠️ 空的 |
| stock_trends.db | 0.2 MB | 2026-05-05 | ⚠️ 小 |
| tina_trading.db | 0 MB | 2026-05-04 | ⚠️ 空的 |
| vogel_indicators.db | 0.2 MB | 2026-04-28 | ⚠️ 小+舊 |

### 需要確認的 DB

| DB | 大小 | 更新 | 說明 |
|:---|-----:|:-----|:-----|
| finmind.db | 0.8 MB | 2026-05-03 | 落後3天，url 已換 |
| vogel.db | 0.1 MB | 2026-04-28 | 太久沒更新 |
| naver_places.db | 0.1 MB | 2026-04-28 | 太久沒更新 |

### 建議快速檢查

```python
# 檢查空DB的記錄數
import sqlite3
for db in ['leo_stocks.db','nana_stocks.db','maggy.db','limitup.db','rsi.db','tina_trading.db']:
    conn = sqlite3.connect(f'data/{db}')
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f'{db}.{t} = {cnt} rows')
    conn.close()
```

---

## ⚠️ 高優先級

1. **清理 40+ 個明顯廢棄的 debug/fix 腳本**
2. **檢查 6 個空 DB 是否正常**（可能是 table 創建了但沒寫入）
3. **確認 finmind.db 更新落後**（URL 已換新，需要更新抓取腳本）
4. **壓縮 yfinance.db（177.5 MB）** 或確認是否需要備份

---

## 低優先級（長期）

- Nana 版本合併（9個→1個）
- 備份目錄清理
- scripts/ vs teams/ vs skills/ 邊界澄清
- cron jobs 功能分類（目前38個，難以理解誰負責什麼）