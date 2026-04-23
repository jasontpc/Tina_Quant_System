# Tina + Nana 團隊共享協議
> 更新時間: 2026-04-23

---

## 📡 共享架構

```
┌─────────────────────────────────────────────┐
│          Tina + Nana 共享資料層             │
│              team_shared.py                 │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐     ┌─────────────┐       │
│  │   Tina      │ ←→  │   Nana      │       │
│  │  Team       │     │  Team       │       │
│  └──────┬──────┘     └──────┬──────┘       │
│         │                    │              │
│         ↓                    ↓              │
│  ┌─────────────────────────────────────┐   │
│  │         共享資料區 (shared/)         │   │
│  │                                     │   │
│  │  market_snapshot.json   市場快照     │   │
│  │  tina_signals.json      Tina訊號    │   │
│  │  nana_signals.json      Nana訊號    │   │
│  │  watchlist.json         觀察名單    │   │
│  │  alerts.json            警報        │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

---

## 📁 共享資料說明

### 1. market_snapshot.json
市場概況 (兩團隊都能讀寫)

| 欄位 | 說明 |
|:-----|:-----|
| twii | 台股加權指數 |
| sp500 | S&P 500 |
| vix | VIX 恐慌指數 |
| market_status | 'bull' / 'bear' / 'normal' |
| sector_rotation | 類股輪動狀態 |

### 2. tina_signals.json
Tina 團隊寫入的分析訊號

| 欄位 | 說明 |
|:-----|:-----|
| score | 評分 (0-100) |
| signal | 'buy' / 'sell' / 'watch' |
| rsi | RSI 值 |
| atr_pct | ATR% |

### 3. nana_signals.json
Nana 團隊寫入的分析訊號

| 欄位 | 說明 |
|:-----|:-----|
| score | 評分 (0-100) |
| signal | 'buy' / 'sell' / 'watch' |
| f_consec | 外資連續買超天數 |
| t_consec | 投信連續買超天數 |

### 4. watchlist.json
共用追蹤觀察名單

### 5. alerts.json
系統警報

---

## 🔄 運作流程

### Tina 團隊
```python
from team_shared import TeamShared

shared = TeamShared()

# 分析後寫入
shared.write_tina_signal('2330', {
    'score': 85,
    'signal': 'buy',
    'rsi': 65
})
```

### Nana 團隊
```python
# 讀取 Tina 訊號
tina = shared.get_tina_signals()

# 自己的分析
shared.write_nana_signal('2330', {
    'score': 80,
    'signal': 'buy'
})

# 產生聯合報告
joint = shared.get_joint_report()
```

---

## 🎯 聯合決策

| Tina | Nana | 結論 |
|:-----|:-----|:-----|
| 買進 | 買進 | ✅ 強力買進 |
| 買進 | 觀望 | ⚠️ 確認後進場 |
| 觀望 | 買進 | ⚠️ 需要更多證據 |
| 不買 | 任意 | ❌ 不進場 |

---

## 📊 共識範例 (2026-04-23)

```
🔥 共識買進 (Tina + Nana 同步)
  2330 | Tina 85 + Nana 80 = AVG 82
```

---

## 使用方式

```python
from team_shared import TeamShared

shared = TeamShared()

# 產出完整聯合報告
shared.print_joint_report()

# 取得 JSON 格式
report = shared.get_joint_report()
```