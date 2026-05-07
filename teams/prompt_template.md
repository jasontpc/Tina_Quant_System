# Tina Trading Prompt Template — Lessons 加強版
**版本：** v1.0
**日期：** 2026-05-07
**用途：** 增強 Tina 交易判斷，自動引用 Lessons 庫

---

## 教訓引用格式（每筆進場決策前必讀）

### 失敗案例（losses/）— 避免犯同樣錯誤
```
每次進場決策前，先問：
1. 這檔股票是否曾出現在 losses/ 目錄？
2. 上次虧損原因：持有過長？ RSI 過熱？ 沒有停損？
3. 這次進場條件是否比上次更嚴格？
```

### 成功案例（wins/）— 複製成功模式
```
每次進場決策前，先問：
1. 這檔股票是否曾出現在 wins/ 目錄？
2. 上次進場條件：RSI 多少？ 持有多久？ 停利多少？
3. 這次條件是否匹配或優於上次？
```

---

## Lessons 引用觸發條件

| 情況 | 自動引用 |
|:-----|:---------|
| 進場 Leo 個股 | 查 `lessons/2382*` → 避免相同錯誤 |
| RSI > 70 仍想進場 | 引用 `losses/rsi_overbought_profit*` |
| 持有 > 20 天 | 引用 `losses/holding_too_long*` |
| Nana buy_b 信號 | 查 `lessons/buy_b*` wins |
| TWII RSI > 85 | 引用 `losses/TWII_overbought*` |

---

## Prompt 注入格式

當 Tina 收到進場分析請求時，在專家委員會之前自動注入：

```
【Lessons 活化檢查】
$LESSONS_DIR = memory/lessons/

讀取 recent losses (last 5):
  [自動列出最近的虧損 lesson 摘要]

讀取 recent wins (last 5):
  [自動列出最近的獲利 lesson 摘要]

針對 [$SYMBOL] 的風險：
  [對比 lessons，找出相似教訓]

决策加成：避免重蹈覆轍，複製成功模式
```

---

## 關鍵 Lessons 沉積規則

### 必須寫入 losses 的條件
- 停損執行（任何原因）
- 持有 > 20 天 + RSI > 50
- RSI > 80 追高被套
- excess_positions 強制平倉
- 違反 MA20 移動停損

### 必須寫入 wins 的條件
- RSI 35-50 黃金區間進場 → 獲利了結
- Golden Cross + MACD 多頭 → 成功
- 嚴守停利目標（TP 到達）
- 持有 < 10 天 + RSI < 60 → 快速獲利

---

## 自動觸發腳本

```python
# leos_daily_review.py — 每筆平倉自動寫入
_write_trade_lesson(t, entry, cur, net_pnl, reason, market, days_held, rsi)

# tina_memory_sync.py — 每日 MEMORY.md 更新
# 每日 07:00 + 22:00 自動執行
```

---

## Lessons 目錄結構

```
memory/lessons/
├── wins/
│   ├── 2382_20260504_win.md    ← 黃金區間進場成功
│   ├── 3034_20260502_win.md    ← Golden Cross 確認後進場
│   └── ...
├── losses/
│   ├── 2382_20260507_loss.md   ← 持有過長 + RSI>50 止損
│   ├── TSLA_20260503_loss.md   ← RSI>90 追高被套
│   └── ...
└── INDEX.md                    ← Lessons 索引（自動生成）
```

---

_模板版本：v1.0 — 2026-05-07_