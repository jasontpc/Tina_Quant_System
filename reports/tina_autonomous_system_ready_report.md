# Tina 自主決策系統就緒報告

**執行時間：** 2026-05-02 12:03  
**系統版本：** v3.12  
**狀態：** ✅ 就緒

---

## 已建立的檔案結構

### 核心腳本（scripts/）

| 檔案 | 功能 |
|:-----|:-----|
| `tina_autonomous_monitor.py` | 自主監控觸發器（每24小時檢查） |
| `tina_auto_patch.py` | 自動修正引擎（分析→驗證→執行） |
| `tina_decision_logger.py` | 決策日誌產生器 |
| `tina_backtest_validator.py` | 回測驗證模組（勝率>55%，獲利因子>1.2） |

### 設定檔（configs/）

| 檔案 | 功能 |
|:-----|:-----|
| `autonomous_config.json` | 觸發條件門檻、驗證標準、Safety Rails |
| `decision_rules.json` | 決策邊界、允許/禁止修改的參數 |

### 策略檔案（strategies/）

| 檔案 | 功能 |
|:-----|:-----|
| `tina_v1_base.py` | 原始策略（保留，絕不修改） |
| `tina_v2_auto_patch.py` | 第一版自動修正策略 |

---

## 核心流程

```
[每日 00:00 — 執行 tina_autonomous_monitor.py]
         |
         v
[檢查：5連虧 OR 單筆>-10% OR 環境失效]
         |
    [是] | [否]
    v          v
啟動自主模式   繼續監控
         |
         v
[分析近3日5分K線] → [計算新RSI區間] → [建立新策略腳本]
                                              |
                                              v
                              [100根K線回測驗證]
                                              |
                              [勝率>55% AND 獲利因子>1.2?]
                                 |                    |
                               [是]                  [否]
                                |                    |
                     切換新策略+Telegram通知  放棄修改+通知Jo人工介入
```

---

## Safety Rails（安全防線）

| 規則 | 說明 |
|:-----|:-----|
| ❌ 禁止修改 main.py | 永遠不直接修改生產策略 |
| ✅ 新策略另存新檔 | `tina_v{N}_auto_patch.py` |
| ✅ 回測未通過不執行 | 勝率>55% 且 獲利因子>1.2 |
| ✅ 每次決策即時報告 | 所有動作通知 Jo |
| ✅ 保留舊版策略 | 新策略失敗可隨時回滾 |

---

## 觸發條件

| 條件 | 閾值 | 嚴重性 |
|:-----|:-----|:-------|
| 連續虧損 | 5 筆 | HIGH |
| 單筆虧損 | -10% | CRITICAL |
| RSI 系統失敗 | 10 次 | HIGH |

---

## 回測驗證標準

- **勝率：** > 55%
- **獲利因子：** > 1.2
- **最少交易筆數：** 100 筆

---

## 技術說明

### 資料來源
- **5 分鐘 K 線：** FinMind API（TaiwanCorpTFEX）
- **日 K 線備用：** `tw_history.db` → `daily_ohlcv` 表

### 資料庫 Schema
- `trade_archive.db`（需有 `trades` 表）→ 目前無資料
- `tw_history.db` → `daily_ohlcv`（symbol, date, open, high, low, close, volume）

### 當 前狀態
- 目前 trade_archive.db 無交易資料（0 筆）
- tw_history.db 僅有近 2 日資料（不足 RSI 計算所需 15+ 筆）
- **系統就緒，等待實際交易資料累積後自動生效**

---

## Cron Job 設定

建議新增（每日 00:00 執行）：
```json
{
  "name": "Tina 自主決策監控",
  "schedule": "0 0 * * *",
  "script": "python scripts/tina_autonomous_monitor.py",
  "description": "每日午夜檢查是否需要啟動自動策略修正"
}
```

---

## 使用方式

### 1. 執行監控檢查（手動）
```bash
python scripts/tina_autonomous_monitor.py
```

### 2. 執行完整自動修正（手動觸發）
```bash
python scripts/tina_auto_patch.py
```

### 3. 僅執行回測驗證
```bash
python scripts/tina_backtest_validator.py
```

### 4. 產生決策報告
```bash
python scripts/tina_decision_logger.py
```

---

## 系統特點

1. **完全自動化**：從監控到執行無需人工介入
2. **嚴格 Safety Rails**：禁止直接修改生產代碼
3. **回測驗證**：未通過不回測不實際交易
4. **透明報告**：所有決策即時通知 Jo
5. **版本管理**：每次修正產生新策略檔，保留所有版本

---

*此報告由 Tina AI 自動產生 | 2026-05-02*