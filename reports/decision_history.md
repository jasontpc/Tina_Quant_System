# Tina 決策歷史 (Decision History)

## 格式說明
每次決策記錄結構：`[Stock_Code] > [Old_Params] > [New_Params] > [Reason]`

---

## 2026-05-02 系統升級

### 13:00 - 個股獨立策略模式升級

**主題**: 從「通用參數模式」升級為「個股獨立策略模式」

**新增功能**:
- `scripts/tina_stock_aware_brain.py` - 個股感知大腦
- `scripts/strategy_hot_reload.py` - 策略熱啟動監控器
- `scripts/tina_self_play.py` - 自我博弈系統
- `reports/experience_ledger.md` - 經驗學習文件庫
- `reports/decision_history.md` - 決策歷史記錄

**新增字段（每個股票 JSON）**:
- `stock_character` - 個股特徵（label, bias, atr_multiplier, noise_level, suitable_strategy）
- `brain_instructions` - 大腦思考指令（think_context, avoid_mistakes, special_notes）
- `volatility_tier` - 波動性等级（low/medium/high）

---

## 個股決策記錄（嚴格格式）

### 2330 台積電
```
2330 > {} > {stock_character: {label: "藍籌權值股", atr_multiplier: 1.0}, brain_instructions: {...}} > 系統升級建立完整配置
```

### 2382 廣達
```
2382 > {} > {volatility_tier: "high", atr_multiplier: 1.2, stock_character: {label: "AI伺服器龍頭", bias: "高波動高動能"}} > 系統升級建立高波動配置
```

### 2454 聯發科
```
2454 > {} > {volatility_tier: "high", atr_multiplier: 1.3, stock_character: {label: "IC設計高階晶片", bias: "高波動景氣循環"}} > 系統升級建立景氣循環配置
```

### 2881 富邦金
```
2881 > {volatility_tier: "unknown"} > {volatility_tier: "low", atr_multiplier: 0.8, stock_character: {label: "金控龍頭", bias: "穩健價值", noise_level: "low"}} > 系統升級建立金融股配置
```

### 2884 玉山金
```
2884 > {volatility_tier: "unknown"} > {volatility_tier: "low", atr_multiplier: 0.8, stock_character: {label: "銀行信用卡", bias: "穩健成長", noise_level: "low"}} > 系統升級建立金融股配置
```

### 3231 緯創
```
3231 > {volatility_tier: "unknown"} > {volatility_tier: "high", atr_multiplier: 1.2, stock_character: {label: "AI伺服器", bias: "高動能", suitable_strategy: "動能驅動"}} > 系統升級建立AI伺服器配置
```

---

## 安全防線記錄

### 異常修改警示（待實作）
| 股票 | 原因 | 狀態 |
|:-----|:-----|:----:|
| - | - | - |

---

## 自主學習效果評估（每週）

| 股票 | 學習效果 | 建議 |
|:-----|:---------|:-----|
| 2330 台積電 | 待評估 | 需要交易資料 |
| 2382 廣達 | 待評估 | 需要交易資料 |
| 2454 聯發科 | 待評估 | 需要交易資料 |

---

_Last updated: 2026-05-02 13:02_