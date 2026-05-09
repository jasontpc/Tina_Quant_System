# Streamlit UI 參數修改標準作業程序 (SOP)
> 版本：v1.0 | 建立日期：2026-05-09 | 維護者：Tina

---

## 目的

確保每次修改 `streamlit_tw_stock.py` 的 UI 參數、評分系統、或功能調整，都經過有系統的流程，避免破壞現有功能或造成資料不一致。

---

## 範圍

- `streamlit_tw_stock.py` 的所有 UI 參數修改
- 評分系統權重調整
- 技術指標參數（RSI、MACD、布林帶等）
- 新功能新增
- 既有功能移除或修改

---

## 名詞定義

| 名詞 | 定義 |
|:-----|:-----|
| **參數修改** | 調整 UI 上的數值範圍、預設值、門檻 |
| **評分系統調整** | 改變評分公式的權重或條件 |
| **功能新增** | 在 Streamlit 中加入新區塊、新按鈕 |
| **功能修改** | 改變現有功能的邏輯或外觀 |

---

## 修改流程（5步驟）

### Step 1：建立修改提案（Modification Proposal）

在修改任何參數前，先建立提案：

```
格式：[streamlit_sop_proposal_YYYYMMDD_N.md]
位置：TQS/docs/streamlit_modifications/
```

提案內容：
```markdown
# 參數修改提案 — YYYYMMDD_N

## 基本資訊
- 修改者：Tina / Jo
- 日期：YYYY-MM-DD
- 修改類型：□參數調整 □評分系統 □功能新增 □功能修改

## 修改內容
### 現在（Before）
- 項目：xxx
- 目前值：yyy

### 提議（After）
- 項目：xxx
- 提議值：zzz

## 修改原因
- 為什麼要改？
- 期望達到的效果？

## 風險評估
- 可能影響的模組：
- 可能的副作用：

## 驗證方式
- 如何驗證修改成功？
- 什麼情況算失敗？

## 模擬結果（沙盤推演）
（在此填入預期的 UI 變化和資料結果）
```

### Step 2：沙盤推演（Sandbox Review）

修改前先紙上模擬：

1. **功能追蹤**：這次改動會影響哪些功能？
   - 列表排序
   - 篩選結果
   - 評級（A/B/C/D）分布
   - Telegram 發送內容

2. **資料驗證**：
   - 用已知的股票（如 2330）預測新參數下的評分
   - 確認 Tier 等級是否合理

3. **衝突檢測**：
   - 新參數是否與風控規則衝突？（例如 RSI > 85 應為警示）
   - 與 cron job 或其他腳本的假設是否一致？

4. **寫入決策日誌**：
   ```markdown
   ## 決策日誌：streamlit_YYYYMMDD_N
   
   ### 目標
   [這次修改要達到什麼]
   
   ### 選項
   - 選項 A：[描述]
   - 選項 B：[描述]
   
   ### 風險
   - 最糟情況：xxx
   
   ### 選擇
   - 選擇：選項 A/B
   
   ### 預期
   - 評分調整：xx%
   - Tier 分布變化：xxx
   - UI 變化：xxx
   ```

### Step 3：實際修改（Implementation）

**修改原則**：
- 每次只改一個參數群組
- 改完立刻驗證
- commit 時寫清楚修改內容

**修改格式（Git commit message）**：
```
feat(streamlit): 調整 RSI 上限從 100 → 85
fix(streamlit): 修正評級門檻計算錯誤
refactor(streamlit): 中文化 UI 文字
```

**修改時的防呆檢查**：
- [ ] 語法正確：`python -m py_compile streamlit_tw_stock.py`
- [ ] 沒有破壞其他模組
- [ ] 預設值合理（不會造成無資料顯示）

### Step 4：驗證（Validation）

**本地驗證項目**：

| 驗證項目 | 方法 | 預期結果 |
|:---------|:-----|:---------|
| 語法正確 | `python -m py_compile streamlit_tw_stock.py` | 無錯誤 |
| UI 正常啟動 | `streamlit run streamlit_tw_stock.py` | 頁面正常顯示 |
| 評分正確 | 輸入 2330，檢查 Score 在 600-900 區間 | 合理範圍 |
| 篩選有效 | RSI Max 調整到 60，確認過濾結果變化 | 資料減少 |
| Tier 分布 | 檢查 A/B/C/D 分布是否合理 | A 約 10-20% |

**雲端部署驗證**（如需要）：
1. 部署到 Streamlit Cloud
2. 測試 Telegram 發送
3. 確認 st.secrets 讀取正常

### Step 5：文件更新（Documentation）

修改完成後，更新以下文件：

1. **`docs/streamlit_modifications/YYYYMMDD_N.md`** — 存入修改提案
2. **`docs/streamlit_ui_guide.md`** — 更新 UI 說明（如有）
3. **`streamlit_cloud_backup_20260509/BACKUP_MANIFEST.txt`** — 更新備份說明
4. **`MEMORY.md`** — 寫入修改記錄

---

## 常見修改情境 SOP

### 情境 A：調整評分門檻（Tier 門檻）

```
修改點：calc_score() 或 Tier 等級判斷
風險：高（會影響所有股票的評級）
SOP：
1. 先用現有資料測試新舊門檻差異
2. 確認 A 級股票不超過總數 20%
3. 確認 D 級股票有合理分布
4. 沙盤推演：100 檔股票中，預期 A/B/C/D 各多少？
```

### 情境 B：調整技術指標參數

```
修改點：RSI 計算（14日 → ？）
風險：中（只影響 RSI 顯示和篩選）
SOP：
1. 確認 RSI 計算邏輯（yfinance vs 本地計算）
2. 確認快取 TTL（CACHE_TTL = 60）
3. 調整後確認 RSI 數值在合理範圍（0-100）
4. 測試篩選功能是否正常
```

### 情境 C：新增股票類別

```
修改點：TW_CATS 或 US_CATS
風險：低（只影響可選擇的股票範圍）
SOP：
1. 確認股票代碼格式（TW：數字 4-6 碼，US：英文字）
2. 測試新增的股票能否正常分析
3. 更新 BACKUP_MANIFEST.txt 的主要符號清單
```

### 情境 D：中文化 / UI 文字修改

```
修改點：st.title、st.checkbox label、st.metric label 等
風險：低（只影響顯示，不影響計算）
SOP：
1. 翻譯時保持英文關鍵字（Code、Price、RSI 等）在 DataFrame 中
2. 完成後執行 check_streamlit.py 驗證語法
3. 測試 streamlit run 是否正常啟動
4. 確認按鈕、篩選器功能正常
```

---

## 技術數據視窗說明（Tooltip / Caption 標準）

每次新增或修改技術指標顯示，需同時提供說明：

| 指標 | 說明 |
|:-----|:-----|
| RSI | 相對強弱指標，>70 過熱，<30 超賣 |
| MACD | 指數平滑異同移動平均線，>0 偏多 |
| K / D | KD 隨機指標，K > D 黃金交叉 |
| BB% | 布林通道偏離度，>70 價格偏離上軌 |
| BIAS5 | 5日乖離率，偏離 MA5 的百分比 |
| MA20/MA60 | 20日/60日均線，MA20 > MA60 多頭 |
| Vol Ratio | 量比，相對20日均量 |
| 外資 (F) | 外國機構投資人買賣超 |
| 投信 (T) | 國內投信基金買賣超 |
| 自營商 (D) | 證券商自行買賣超 |

---

## 參數對照表（當前設定）

| 參數 | 當前值 | 備註 |
|:-----|:------:|:-----:|
| RSI 期間 | 14日 | 標準設定 |
| MACD | EMA12/26, Signal9 | 標準設定 |
| 評分上限 | 1000分 | |
| Tier A 門檻 | ≥800 | |
| Tier B 門檻 | ≥600 | |
| Tier C 門檻 | ≥400 | |
| Tier D 門檻 | ≥200 | |
| Cache TTL | 60秒 | 已從 300s 調整 |
| CACHE_TTL | 60 | 快取生命週期 |
| Telegram Chat ID | 1616824689 | |
| 最大工作執行緒 | 4 | ThreadPoolExecutor |

---

## 修改履歴

| 日期 | 提案 | 修改內容 | 驗證結果 |
|:-----|:----:|:---------|:---------:|
| 2026-05-09 | SOP建立 | 建立本 SOP 文件 | ✅ |
| 2026-05-09 | 001 | UI 中文化（繁體） | 待驗證 |