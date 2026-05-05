# -*- coding: utf-8 -*-
"""
DB 落後原因分析報告
分析為何這些 DB 落後，並提供改善建議
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

report = """
## 🧠 DB 落後原因分析 | 2026-05-05 17:48

---

### 🔴 Maggy DB — 落後 8 天（2026-04-27）

**原因：**
- Cron `f57996ce`「Maggy 每日DB收盤更新」（16:00）→ 存在但可能失敗
- 檢查：Maggy 美股每日檢查（18:00）正常運行（10h ago）
- 但 DB 更新 cron 可能因為 API 変更/路徑錯誤/權限問題 而靜默失敗

**對策：**
- 檢查 `maggy_db_updater.py` 是否存在且正常
- 建議：合併到「Maggy 美股每日檢查」18:00 的同一腳本中
- 或刪除獨立的 DB 更新 cron，統一由分析腳本負責更新

---

### 🔴 tina_master.db — 落後 11 天（2026-04-24）

**原因：**
- **根本原因：沒有任何 cron job 負責更新這個 DB**
- Tina Master DB 是早期設計的 RSI 資料庫，目前主要系統已改用 yfinance.db
- yfinance.db 已有完整 RSI（今天 backfill 完成，2026-05-05 最新）
- tina_master.db 是備用/舊系統，沒有維護者

**對策：**
- 選項A：建立 cron 負責更新 tina_master.db
- 選項B：**棄用 tina_master.db**，全面使用 yfinance.db（已完整）
- 建議：選項B（yfinance.db 已是主要 DB，tina_master 是 legacy）

---

### 🔴 Reddit Sentiment — 落後 999 天

**原因：**
- 之前刪除了「Reddit 社群情緒每日更新」（18:00）cron job
- 刪原因：與 StockTwits/Tavily 重疊，整合成一個 job
- **但整合後忘了建立新的單一社群情緒 cron**

**對策：**
- 建立統一股群情緒 cron（18:00）
- 合併 Reddit + StockTwits + Tavily → 一個 job 三個來源

---

### ✅ 正常 DB 分析

| DB | 狀態 | 原因 |
|:---|:-----|:-----|
| yfinance.db | ✅ 最新 | 每日 08:00 Tina 歷史DB更新 |
| ETF DB | ✅ 最新 | 每日 16:00 Yahoo ETF 更新 |
| TW歷史 | ✅ 落後1天 | 每日更新機制正常 |
| 法人數據 | ✅ 落後3天 | 每日更新但剛好周末 |
| 融資券 | ✅ 落後3天 | 每日更新但剛好周末 |

---

## 📋 改善 Action Items

| 優先 | 項目 | 負責 | 執行 |
|:----:|:-----|:----:|:----:|
| 🔴 P1 | 修復 Maggy DB 更新（檢查 cron 或合併） | Tina | 今天 |
| 🔴 P1 | 建立社群情緒 cron（Reddit+Tavily+StockTwits） | Tina | 今天 |
| 🟡 P2 | 決定是否保留 tina_master.db | Jo | 本週 |
| 🟡 P2 | 為 tina_master 建立維護 cron 或棄用 | Tina | 本週 |
"""

print(report)
import json, urllib.request
token = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
chat = '1616824689'
url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({'chat_id': chat, 'text': report, 'parse_mode': 'Markdown'}).encode()
try:
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10): pass
except: pass