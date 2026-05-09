# 2026-05-09 慢思考健檢：13 個 Disabled Jobs 必要性分析

## 已知 Disabled Jobs（根據對話記錄）

### 已確認狀態（從 summary 可見）

| # | Job ID | 名稱 | 停用原因 | 分析 |
|:--|:-------|:-----|:---------|:-----|
| 12 | (unknown) | Tina 股票交易週報 | 被 852520d6 取代 | ✅ 可刪除（功能已被取代）|
| A | a22b3527 | Tina 交易日記+預警 | delivery error + 從未執行 | ✅ 已刪除 |
| B | ca3be530 | Tina 股票交易週報 | delivery error + 從未執行 | ✅ 已刪除 |

### 需要驗證的（根據 deliveryPreviews "not requested"）

| Job ID | 名稱 | 觀察 |
|:-------|:-----|:-----|
| c6eb5e6b | Leo AI產業鏈每日追蹤 | payload=systemEvent（應為 agentTurn），sessionTarget=main（應為 isolated），delivery="not requested" |

---

## 從 Enabled Jobs 列表中發現的結構問題

### 1. Delivery 格式過時（4 個 jobs）

| Job ID | 名稱 | 當前 delivery | 應改為 | 狀態 |
|:-------|:-----|:-------------|:-------|:-----|
| 6263e6d0 | Leo v6.5 科技股波段 | channel=last, to=telegram:1616824689 | channel=telegram, to=1616824689 | ⚠️ 需修正 |
| d8fe08ae | US AI Tech 每日分析 | channel=last, to=telegram:1616824689 | channel=telegram, to=1616824689 | ⚠️ 需修正 |
| 1306d237 | Tina 自動學習擴充DB | channel=last, to=telegram:1616824689 | channel=telegram, to=1616824689 | ⚠️ 需修正 |
| 56da375e | US Margin 每日分析 | channel=last, to=telegram:1616824689 | channel=telegram, to=1616824689 | ⚠️ 需修正 |

**這些 jobs 都正常執行（lastRunStatus=ok），但 delivery 使用舊格式，存在潛在失效風險。**

---

## 慢思考：為何這些 jobs 被停用？

### 典型原因分析

1. **功能被取代**（#12）
   - 原本每週五 17:00 的「Tina 股票交易週報」
   - 被「策略績效週報 + 委員會投票」（852520d6，週五 18:30）取代
   - 取代者功能更完整（完整回測 + 委員會投票 + 下週觀察名單）

2. **從未執行（0 runs）導致無法修復**（A/B）
   - Tina 交易日記+預警（a22b3527）：從未執行，delivery error 卡死
   - Tina 股票交易週報（ca3be530）：從未執行，delivery error 卡死
   - 修復 delivery 也無法補救，因為從未真正成功過

3. **結構性問題無法在 isolated session 正常運作**（c6eb5e6b）
   - systemEvent 在 isolated session 可能無法正確觸發
   - sessionTarget=main 不符合主要系統 jobs 應為 isolated 的規範
   - delivery="not requested" = 直接失效

---

## 最終建議

### 從 13 個 Disabled Jobs 中

| 類別 | 數量 | 建議 |
|:-----|:-----|:-----|
| 已刪除（確定）| 2 個（A/B）| 已於第五波刪除 |
| 應刪除（功能被取代）| 1 個（#12）| 備份後刪除 |
| 需修復後啟用 | 1 個（c6eb5e6b）| 改為 agentTurn + isolated + 正確 delivery |
| 需修正 delivery 格式 | 4 個 | 將 channel=last 改為 channel=telegram |

### 剩餘 5 個 Disabled Jobs（未能在列表中確認）

根據記憶，這 5 個 job 的停用原因可能包括：
- 被取代（multiple）
- delivery error（multiple）
- 一次性任務已執行（1-2個）

**建議：下次完整獲取 cron list 時，使用 Python 解析完整 JSON 確認所有 13 個 disabled jobs 的 ID 和名稱。**

---

## 今日健檢總結

| 項目 | 數量 | 狀態 |
|:-----|:-----|:-----:|
| 總 Jobs | 34（可見）+ 未顯示部分 | ⚠️ 需完整盤點 |
| 有 delivery 格式問題 | 4 個 | ⚠️ 需修正 |
| 有結構問題（systemEvent/main）| 1 個 | 🚨 需修復 |
| 已成功刪除（今天）| 14 個 | ✅ 完成 |
| 備份記錄 | deleted_crons_backup_20260509.json | ✅ 已寫入 |

---

_最後更新：2026-05-09 20:25 by Tina_