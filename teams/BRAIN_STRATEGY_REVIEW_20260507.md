# Tina 大腦 — 交易策略審查與改善方案
**日期：** 2026-05-07 23:10
**目標：** 全面審查現有策略、提出改善方案

---

## 📋 現有系統審查

### 波段系統（Leo v7.0）
| 參數 | 數值 | 評估 |
|:-----|:----:|:----:|
| 進場 RSI | 40-50 | ✅ 黃金區間 |
| 停利（TP）| 5-8% | ✅ 合理 |
| 停損（SL）| 8-10% | ✅ 紀律 |
| 最大持有 | 30 天 | ⚠️ **需強化** |
| RSI > 50 + 持有 > 30天 | — | 🔴 **致命組合** |

### ETF 系統（Ray）
| 參數 | 數值 | 評估 |
|:-----|:----:|:----:|
| DCA 頻率 | 每月 | ✅ 正確 |
| RSI > 70 觀望 | 是 | ✅ 紀律 |
| 殖利率篩選 | > 3% | ✅ 合理 |

### 類神經系統（Nana v5.8）
| 參數 | 數值 | 評估 |
|:-----|:----:|:----:|
| RSI 進場 | 30-45 | ✅ 保守 |
| 動量過濾 | 是 | ✅ 有效 |
| MA60 多頭 | 是 | ✅ 確認 |

---

## 🔴 策略核心問題

### 問題 1：Leo 系統 — 持有期過長

**症狀：**
- 2382 廣達：持有 > 30天 + RSI > 50 = **致命組合**
- 19 筆 excess_positions 全數由系統強制平倉

**根本原因：**
- 缺乏明確的「時間紀律」規則
- 沒有持有天數上限警告
- 沒有定期「是否續抱」再評估機制

**改善方案：**
```python
# 持有紀律規則（新增）
MAX_HOLDING_DAYS = 20          # 強制檢視（不等於賣出）
HOLDING_WARNING_DAYS = 15      # RSI > 50 時，15天預警
HOLDING_FORCE_REVIEW = 20      # 20天，無論如何必須複檢
RSI_HOT_WARNING = 50           # RSI 超過此值 + 持有 > 15天 = 警告
```

---

### 問題 2：Leo 系統 — RSI 進場門檻過窄

**症狀：**
- 只在 RSI 40-50 進場，錯過很多機會
- 但 RSI 35-40（真正黃金區）反而勝率 100%

**改善方案：**
```python
# RSI 分層進場
RSI_GOLDEN_ZONE = (35, 40)    # 100% 勝率區間 → 可增加部位
RSI_GOOD_ZONE = (40, 50)       # 正常進場區間
RSI_WATCH_ZONE = (50, 65)      # 需強烈確認動能
```

---

### 問題 3：Leo 系統 — 缺乏分類市場環境適配

**症狀：**
- TWII RSI 80-100 時，仍在進場（高風險）
- 沒有根據大盤環境調整倉位大小

**改善方案：**
```python
# 大盤環境適配（新增）
TWII_RSI_OVERBOUGHT = 80       # TWII RSI > 80 → 倉位減半
TWII_RSI_DANGER = 85           # TWII RSI > 85 → 全數觀望
VIX_ELEVATED = 20              # VIX > 20 → 謹慎進場
```

---

### 問題 4：Paper Trading 孤島化

**症狀：**
- `tina_paper_trading.py` 存在但**從未與 Leo/Nana 整合**
- 沒有任何腳本呼叫它
- XP 系統無人使用

**改善方案：**
```python
# Leo 進場時同步寫入 paper_trades
from scripts.tina_paper_trading import TinaPaperTrader
paper = TinaPaperTrader()
paper.open_position(symbol, entry_price, strategy="leo_v7", entry_rsi=rsi)
```

---

## ✅ 改善方案清單（優先順序）

### P0 — 立即執行

| # | 改善 | 檔案 | 負責 |
|:-:|:-----|:-----|:-----|
| 1 | **Leo 持有天數警告系統** | `leos_v65.py` | Tina |
| 2 | **Leo 整合 Paper Trading** | `leos_daily_review.py` | Tina |
| 3 | **TWII RSI 環境過濾** | `leos_v65.py` | Tina |

### P1 — 本週執行

| # | 改善 | 檔案 | 負責 |
|:-:|:-----|:-----|:-----|
| 4 | RSI 分層進場（35-40 黃金區）| `leos_v65.py` | Tina |
| 5 | Paper Trading 寫入 `data/etf_signals.json` | `scripts/etf_analysis.py` | Tina |
| 6 | 模擬交易每週報告 Cron | `tina_weekly_reflection.py` | Tina |

### P2 — 下週評估

| # | 改善 | 檔案 | 負責 |
|:-:|:-----|:-----|:-----|
| 7 | Nana 與 Leo 策略參數共享 | `nana_v5.py` | Tina |
| 8 | 經驗 Ledger 自動讀取進場前 | `leos_v65.py` | Tina |

---

## 📐 新一代 Leo 策略框架（v8.0 概念）

```python
class LeoStrategyV8:
    """Leo v8 — 環境感知 + 分層進場 + 時間紀律"""

    # RSI 分層
    RSI_GOLDEN = (35, 40)    # 100% 勝率
    RSI_GOOD = (40, 50)       # 正常
    RSI_WATCH = (50, 65)      # 需確認

    # 大盤環境
    TWII_RSI_SAFE = 70        # < 70 安全
    TWII_RSI_HALF = 80        # > 80 倉位減半
    TWII_RSI_STOP = 85        # > 85 全數觀望

    # 時間紀律
    HOLD_REVIEW_15 = 15       # 持有 15 天預警
    HOLD_REVIEW_20 = 20       # 持有 20 天強制複檢
    HOLD_MAX = 30             # 持有 30 天無條件檢視

    # 進場流程
    def should_enter(self, symbol, rsi, twii_rsi, holding_days):
        # Step 1: 大盤環境檢查
        if twii_rsi >= self.TWII_RSI_STOP:
            return False, "TWII RSI 過熱"

        # Step 2: RSI 進場區間
        if self.RSI_GOLDEN[0] <= rsi <= self.RSI_GOLDEN[1]:
            size = 1.0  # 滿倉
        elif self.RSI_GOOD[0] <= rsi <= self.RSI_GOOD[1]:
            size = 0.8
        elif self.RSI_WATCH[0] <= rsi <= self.RSI_WATCH[1]:
            if holding_days > 0:
                return False, "已有倉位且 RSI 偏熱"
            size = 0.5  # 小部位嘗試
        else:
            return False, f"RSI {rsi} 不在進場區間"

        # Step 3: 持有天數警告
        if holding_days >= self.HOLD_REVIEW_15 and rsi > 50:
            return False, f"持有 {holding_days} 天 + RSI {rsi} → 危險"

        return True, f"進場 size={size}"

    # 持有中檢查
    def should_hold(self, position, current_rsi, current_price):
        holding_days = position['holding_days']
        entry_rsi = position['entry_rsi']

        # 致命組合：持有 > 30天 + RSI > 50
        if holding_days >= self.HOLD_MAX and current_rsi > 50:
            return False, "持有期滿 + RSI 偏熱，強制檢視"

        # 移動停損：MA5 跌破
        if current_price < position['ma5']:
            return False, "跌破 MA5 移動停損"

        return True, "續抱"
```

---

## 🎯 行動承諾

| 時間 | 行動 |
|:-----|:-----|
| 明天 | 為 Leo v65 加入「持有天數警告」|
| 明天 | 將 Leo 進場寫入 `TinaPaperTrader`|
| 本週 | TWII RSI 環境過濾整合至 Leo |

---

_報告：Tina Brain v3 — 2026-05-07 23:10_