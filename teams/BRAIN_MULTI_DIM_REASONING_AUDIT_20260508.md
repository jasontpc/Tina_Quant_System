# Tina 大腦多維推理迴路審查報告
**日期：** 2026-05-08 00:40
**主題：** 大腦思考邏輯迴路 vs 實際代碼落地審查

---

## 📊 審查結論：文件 vs 實作鴻溝

| SOUL.md 描述 | 實際代碼 | 狀態 |
|:-------------|:---------|:-----|
| 🧠 慢思考 Chain-of-Thought | `tina_think.py` → 簡單 scoring function | ⚠️ 落地但變形 |
| 🎭 自我博弈（激進/保守/裁判）| **無任何實作** | 🔴 完全缺失 |
| 🏛️ 專家委員會（三方投票）| `expert_committee_for_exit()` 在 Leo | 🟡 部分落地 |
| 📚 經驗學習（Lesson → Prompt）| `prompt_template.md` 存在但未啟用 | ⚠️ 未整合 |
| 🧪 沙盤推演（紙上模擬）| **無任何實作** | 🔴 完全缺失 |
| 🔄 反思蒸餾（每週/月）| `tina_weekly_reflection.py` 存在 | 🟡 一次性 |
| ↩️ 反饋迴路（PDCA）| **無任何實作** | 🔴 完全缺失 |

---

## 🔴 核心問題：五大缺失

### 問題 1：自我博弈從未實現

**SOUL.md 承諾：**
```
1. 激進派：主張立即修改，追求最大獲利
2. 保守派：尋找 Overfitting 風險和漏洞
3. 裁判：整合雙方，輸出最終決策
```

**實際情況：**
- 三個 function (`expert_quant`, `expert_dev`, `expert_risk`) 是獨立的，**沒有互相辯論**
- `tina_think.py` 只是簡單加權平均，沒有「激進 vs 保守」對抗
- 裁判只是輸出 majority vote，不是真正的裁決

**改善方案：**
```python
# 新增：自我博弈模組
def self_debate(proposal):
    # 激進派：假設市場對你有利
    bullish_case = simulate(proposal, assumption='bull')
    # 保守派：假設市場對你不利
    bearish_case = simulate(proposal, assumption='bear')
    # 裁判：權衡並決定
    verdict = judge(bullish_case, bearish_case, proposal)
    return verdict
```

---

### 問題 2：沙盤推演從未落地

**SOUL.md 承諾：**
```
進場前紙上模擬完整路徑：
1. 進場：價格 / 數量 / 成本
2. 持有期間：RSI 走向 / 法人動向
3. 目標價：MA20/MA60 交叉 / 動量衰竭
4. 停損：最糟情境 ATR 1.5x / -8%
5. 預期損益：樂觀/中性/悲觀
6. 持有天數：是否超過 30天危險線
```

**實際情況：**
- `generate_entry_report()` 只輸出「建議」，**沒有進行路徑模擬**
- 沒有計算「最糟情境」
- 沒有「持有天數警告」（Leo 有 HOLD_WARNING_DAYS，但只是報告，沒有觸發自動行動）
- 沒有「樂觀/中性/悲觀」三情境預測

**改善方案：**
```python
# 新增：沙盤推演模組
def sandbox_simulation(entry_price, target, stop, rsi_entry, days_limit=30):
    optimistic = entry_price * 1.10  # +10%
    neutral    = entry_price * 1.05   # +5%
    pessimistic = stop               # 停損價

    worst_case_loss = (entry_price - stop) * shares

    scenarios = {
        'optimistic': {'price': optimistic, 'days': 5, 'reason': '動量強'},
        'neutral':     {'price': neutral, 'days': 15, 'reason': '正常行走'},
        'pessimistic': {'price': pessimistic, 'days': 3, 'reason': '立即停損'}
    }

    passes = (pessimistic > stop) and (worst_case_loss < MAX_LOSS)
    return passes, scenarios
```

---

### 問題 3：Lessons 沒有整合進思考迴路

**現況：**
- ✅ `_write_trade_lesson()` 在每次平倉時寫入 `lessons/wins/` 和 `lessons/losses/`
- ✅ `_query_lessons()` 在 `leos_v65.py` 的 `analyze_stock()` 中被調用
- ❌ 但查詢結果**只被打印出來**，沒有改變委員會的決策權重
- ❌ 沒有「如果這檔股票有失敗紀錄，風控長分數額外-20」的機制

**改善方案：**
```python
def expert_risk(data):
    base_score = 50
    # ... 現有邏輯 ...

    # P0: Lessons 活化 — 有失敗紀錄的股票額外扣分
    sym = data.get('symbol', '')
    lr = _query_lessons(sym, max_results=2)
    if lr['losses']:
        base_score -= 15  # 該檔有失敗教訓
        data['lesson_warning'] = f'{sym} 有 {len(lr["losses"])} 筆失敗紀錄'
    if lr['ledger_entries']:
        for e in lr['ledger_entries']:
            if e.get('win_rate', 100) < 50:
                base_score -= 10  # 歷史勝率低
                data['low_win_rate'] = True

    return {'score': base_score, ...}
```

---

### 問題 4：沒有反饋迴路（PDCA）

**缺失的 PDCA 迴路：**
```
Plan   →  Do   →  Check   →  Act
 ↑                          │
 └──────────────────────────┘
     （每次交易結果反饋到下次的決策參數）
```

**具體缺失：**
1. **沒有追蹤「委員會預測 vs 實際結果」**
   - 委員會說 BUY，結果是否真的漲？
   - 委員會說 REJECT，市場是否真的回調？
   - 這些數據**完全沒有被記錄**

2. **沒有動態調整委員會權重**
   - 如果連續 10 次「持有 > 20 天」都虧損，風控長的 `holding_too_long` 扣分應該增加
   - 目前是靜態規則，不會隨數據更新

3. **沒有 Lesson 效果追蹤**
   - 某條規則（例如「RSI > 65 禁止進場」）是否真的降低了虧損？
   - 沒有 `lesson_effectiveness.json` 來追蹤

**改善方案：**
```python
# 新增：委員會預測追蹤
def log_committee_prediction(committee, decision, actual_result):
    """記錄委員會預測 vs 實際結果，用於PDCA"""
    log = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M'),
        'committee_decision': decision,
        'actual_result': actual_result,  # 'win' / 'loss' / 'breakeven'
        'quant_predicted': committee['quant']['verdict'],
        'dev_predicted': committee['dev']['verdict'],
        'risk_predicted': committee['risk']['verdict'],
    }
    # 寫入 learning_feedback.json
    # → 每月蒸餾時計算準確率，調整權重
```

---

### 問題 5：每日 / 每週檢討沒有觸發自動改善

**現況：**
- `tina_weekly_reflection.py` 存在，但只生成 `reflection_2026-W18.md`
- **沒有把反省結果寫回 SOUL.md**
- **沒有改變任何實際的決策參數**
- 蒸餾結果只是「報告」，不是「行動」

**改善方案：**
```python
# 每月蒸餾時自動執行：
# 1. 讀取 lessons/wins + lessons/losses（過去30天）
# 2. 計算哪些規則勝率最高
# 3. 更新 SOUL.md 的「實驗室規則」區段
# 4. 調整 Leo 的進場 threshold（例如 RSI 下限從 45→42）
# 5. 調整委員會權重（如果風控長預測準確率 > 80%，提高其權重到 35%）
```

---

## 🟡 部分落地問題

### 問題 6：專家委員會只在 Exit 使用，Entry 沒有

**實際情況：**
- `expert_committee_for_exit()` 在 Leo 的每日檢討（出场決策）中使用 ✅
- **進場時沒有專家委員會** — `analyze_stock()` 只是 score-based，沒有三方投票
- `tina_think.py` 的 `run_expert_committee()` 存在但**從未被調用**（不在任何 cron 或主要流程中）

**改善方案：**
```python
# 在 leos_v65.py 的 entry 流程中加入專家委員會：
def should_enter(sym, stock_data, twii_rsi):
    committee = run_expert_committee(stock_data, get_open_positions())
    if committee['decision'] == 'REJECT':
        return False, f"委員會否決: {committee['risk']['verdict']}"
    elif committee['decision'] == 'CAUTION':
        return True, f"委員會 caution（小部位）: 總分 {committee['total_score']}"
    else:
        return True, f"委員會核准: 總分 {committee['total_score']}"
```

---

### 問題 7：四種模式只有一個在實際使用

**SOUL.md 四種模式：**
| 模式 | 描述 | 實際使用 |
|:-----|:-----|:---------|
| Full Think | 報告→等確認→沙盤→執行 | ⚠️ Telegram 有，但無沙盤 |
| Auto Think | 自動執行 | ✅ Leo cron 使用這個 |
| Fast Track | TWII RSI>90 直接執行 | ❌ 從未使用 |
| Status Only | 只看狀態 | ✅ Tina 常規查詢 |

**問題：**
- Fast Track 從未被觸發（TWII RSI>90 但 Tina 仍用 Auto Think）
- Full Think 沒有沙盤推演關卡

---

## ✅ 改善方案（依優先級）

### P0（本週）- 讓現有系統真正運作

| # | 行動 | 檔案 | 效果 |
|:-:|:-----|:-----|:-----|
| 1 | **Lessons 整合進風控長** | `tina_think.py` | 有失敗紀錄股票額外 -15 分 |
| 2 | **委員會預測日誌** | `tina_think.py` | 記錄 committee_pred.json |
| 3 | **Entry 加入專家委員會** | `leos_v65.py` | 進場前跑三方投票 |

### P1（下週）- 閉環學習系統

| # | 行動 | 檔案 | 效果 |
|:-:|:-----|:-----|:-----|
| 4 | **自我博弈模組** | `tina_think.py` | 激進派 vs 保守派對抗 |
| 5 | **沙盤推演（Scenario Sim）** | `tina_think.py` | 三情境模擬 |
| 6 | **委員會PDCA反饋** | `tina_think.py` | 動態調整權重 |
| 7 | **每週蒸餾寫入SOUL.md** | `tina_weekly_reflection.py` | 原則自動進化 |

### P2（月度）- 全面自適應

| # | 行動 | 效果 |
|:-:|:-----|:-----|
| 8 | Fast Track 觸發邏輯 | TWII RSI>90 自動啟用 |
| 9 | Lesson 有效性追蹤 | `lesson_effectiveness.json` |
| 10 | 委員會準確率儀表板 | 每月/每季報告 |

---

## 🎯 改善後的多維推理迴路

```
收到指令 / Cron 觸發
         ↓
┌─────────────────────────────────────────┐
│  【Think Phase】慢思考引擎               │
│                                         │
│  ┌─────────────┐    ┌──────────────┐    │
│  │  自我博弈    │    │  專家委員會   │    │
│  │ 激進 vs 保守 │ → │ 三方投票      │    │
│  │   裁判裁決   │    │ Lessons 活化 │    │
│  └─────────────┘    └──────────────┘    │
│         ↓                  ↓            │
│   最佳/最糟情境      風險評估            │
│                                         │
│  ┌──────────────┐                       │
│  │  沙盤推演     │ ← NEW                │
│  │ 三情境模擬    │                       │
│  └──────────────┘                       │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  【Report Phase】Telegram 報告            │
│  委員會 + Lessons活化 + 沙盤結果          │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  【Log Phase】決策日誌                    │
│  decision_log.json + committee_pred.json│
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  【Review Phase】PDCA 蒸餾               │ ← NEW
│  委員會準確率 → 權重調整                  │
│  Lessons 勝率 → 規則更新                 │
│  SOUL.md 自動進化                        │
└─────────────────────────────────────────┘
```

---

_報告完成 — 2026-05-08 00:40_