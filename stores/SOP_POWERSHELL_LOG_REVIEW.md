# PowerShell Log 檢討與改善方案
**日期：** 2026-05-11 17:15
**分析範圍：** 7個關鍵日誌檔

---

## 🔴 問題分級（專家委員會）

### 🔴 P0 — 立即修復

| # | 問題 | 日誌 | 根因 |
|:-:|:-----|:-----|:-----|
| 1 | **Shioaji Too Many Connections (451)** | streamlit_debug.log | 同時多個 Streamlit session 或多個腳本使用同一帳號登入 |
| 2 | **FinMind URL encoding error** | streamlit_debug.log | Token 放在 URL query string 中有空白的 Python dict 字面量，應用 quote() 編碼 |
| 3 | **Gateway restart timeout** | gateway_monitor.log | `openclaw gateway start` 超時 10s，啟動時間 >10s |
| 4 | **tina_ps.log DRY RUN** | tina_ps.log | Log Review 腳本沒有實際寫入記憶，沒有真正淨化 |

### 🟠 P1 — 盡快修復

| # | 問題 | 日誌 | 根因 |
|:-:|:-----|:-----|:-----|
| 5 | cloudflared version outdated | cloudflared_error.txt | 2025.8.1 落後，建議升級 2026.3.0 |
| 6 | Streamlit port 8501 refused | cloudflared_error.txt | Streamlit 沒啟動但 cloudflared 嘗試連接 |
| 7 | FinMind 400 errors | errors.log | 法人/融資融券資料索取 2026-05-02 等日期，資料還沒更新 |
| 8 | TED SPREAD / TEDETF delisted | errors.log | yfinance 抓不到，已下市應從 watch list 移除 |
| 9 | `table technicals has no column named atr_14` | errors.log | us_stock_daily.py 寫入一個 schema 沒有 atr_14 的資料庫 |

### 🟡 P2 — 優化建議

| # | 問題 | 日誌 | 根因 |
|:-:|:-----|:-----|:-----|
| 10 | TWSE T86 garbled text | errors.log | 編碼問題（\ufffd），finmind token v2 可能需指定 encoding |
| 11 | 大量重複 WARNING 轰炸 | errors.log | 每次重試都寫一行，佔空間且無有效警報 |
| 12 | 日誌檔案無輪替 | 所有 | streamlit_debug.log 498KB，無自動壓縮/分割 |

---

## 一、緊急修復腳本

### Fix-1: Shioaji 連線限制
```python
# 問題：多個 session 同時 login，造成 451 Too Many Connections
# 解法：全局 login semaphore，確保同時只有 1 個 session 登入
import threading
_shioaji_lock = threading.Lock()

def safe_login(sj):
    with _shioaji_lock:
        if not sj.status.is_login:
            sj.login(...)
```

### Fix-2: FinMind URL Encoding（已確認根因）
```python
# 問題：token dict 字面量放 URL，空格造成 URL 語法錯誤
# 錯誤："?token={'finmind_token': 'xxx'}"  ← 有空白和單引號
# 解決：用 urlencode 或把 token 放 Header

import urllib.parse
# Option A: URL encode
url = f"...?token={urllib.parse.quote(token_dict_str)}"

# Option B: 放 Header（推薦）
headers = {"Authorization": f"Bearer {token}"}
```

### Fix-3: Gateway Restart Timeout
```powershell
# 問題：timeout 10s 不夠，openclaw gateway start 需要更久
# 解決：timeout 改 30s
# 在 gateway_monitor.ps1 或 cron job 設定
```

### Fix-4: tina_ps.log DRY RUN 模式
```python
# 問題：memory_distiller.py --level light 一直 DRY RUN
# 解決：移除 --dry-run 或修正 flag
# 預設應為 dry_run=False
```

---

## 二、Log 輪替與管理 SOP

### SOP-LOG-001：日誌輪替標準

| 檔案 | 最大大小 | 保留天數 | 壓縮 |
|:-----|-------:|--------:|:----:|
| streamlit_debug.log | 10MB | 7天 | .gz |
| errors.log | 5MB | 14天 | .gz |
| gateway_monitor.log | 5MB | 14天 | .gz |
| cloudflared_error.txt | 10MB | 7天 | .gz |
| macro_fetcher.log | 5MB | 7天 | .gz |

### SOP-LOG-002：警報分級標準

```
🔴 CRITICAL：直接影響交易
  - Gateway DOWN
  - 資料庫 lock / corruption
  - 停損被觸發

🟠 WARNING：需要關注
  - FinMind 400 / 404（非預期日期）
  - Shioaji 451（還可工作但效率降）
  - Timeout（網路問題）

🟡 INFO：正常資訊
  - 連線成功
  - 任務完成
  - DRY RUN（應盡快移除）

✅ DEBUG：開發用（正式環境關閉）
  - [UI] Page setup complete（太頻繁，應移除）
```

---

## 三、自動化日誌檢視 Cron（改善後）

### 新增 Job：Log Health Check（每4小時）

```
職責：
1. 檢查 errors.log 最新30行是否有 P0/P1 錯誤
2. 計算 error rate（每小時 error 行數）
3. 若一小時 >20 行 ERROR → 發出 Telegram 警示
4. 若發現新的 P0（Shioaji 451 / URL encoding）→ 立即通知
5. 自動清理 14天+ 舊日誌（超過 10MB 自動壓縮）

日誌寫入格式（標準化）：
[TIMESTAMP] [LEVEL] [SOURCE] [CODE] MESSAGE
  LEVEL: ERROR/WARNING/INFO/DEBUG
  CODE:  Err-XX（内部錯誤代碼）
  MESSAGE: 簡潔描述 + 具體數值

不再這樣：
  [WARNING] FinMind TaiwanStockInstitutionalInvestorsBuySell attempt 1 failed: 400

改為這樣：
  [WARNING] [FinMind] [FM-400] TaiwanStockInstitutionalInvestorsBuySell attempt 1/3 failed (date=2026-05-02, status=400)
```

---

## 四、日誌現況總表

| 檔案 | 大小 | 最後寫入 | 緊急程度 | 行動 |
|:-----|-----:|:---------|:--------:|:-----|
| streamlit_debug.log | 499KB | 2026-05-09 | 🔴 P0 | Fix Shioaji semaphore + URL encoding |
| cloudflared_error.txt | 15KB | 2026-05-11 | 🟠 P1 | 升級 cloudflared + 檢查 Streamlit 進程 |
| errors.log | 9KB | 2026-05-09 | 🟠 P1 | 修復 FinMind URL + 移除 delisted symbols |
| gateway_monitor.log | 4KB | 2026-05-03 | 🟡 P2 | timeout 已修復，持續監控 |
| tina_ps.log | 589B | 2026-05-09 | 🟡 P2 | 移除 DRY RUN mode |
| macro_fetcher.log | 12KB | 2026-05-10 | 🟡 P2 | FinMind 400 日前資料還沒更新，正常 |
| leverage_etf_update.log | 20KB | 2026-05-03 | ✅ OK | 正常，無 action |

---

## 五、立即可執行的 5 行修復（不需重寫架構）

```powershell
# 1. 移除 DRY RUN（2行）
# 在 memory_distiller.py 或 Invoke-LogReview.ps1 搜尋 "DRY RUN"
# 確認有實際寫入記憶的程式碼，移除 --dry-run flag

# 2. 清理 14天前日誌（PowerShell）
Get-ChildItem "logs\" -Filter "*.log" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) } | Remove-Item -WhatIf

# 3. 檢查並重啟 Streamlit（如果 8501 沒回應）
netstat -ano | Select-String ":8501.*LISTENING"

# 4. 升級 cloudflared（1行）
# 下載 2026.3.0 並替換 binary

# 5. 從 watch list 移除 TED SPREAD / TEDETF（1行）
# 在 macro_indicators.py 或相關腳本移除這兩個 symbol
```

---

_本報告由 Tina 大腦 v3.6 慢思考引擎產出_
_下次檢討：2026-05-12 17:00_