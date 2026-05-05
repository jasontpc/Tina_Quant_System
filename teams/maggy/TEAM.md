# Maggy 美股AI/科技股波段交易系統

## 團隊定位
- **代號**: Maggy
- **專注**: 美股 **AI/科技股** 波段交易
- **目標**: 透過RSI均值回歸策略，追求穩定獲利
- **風格**: 數據驅動、主動學習、持續優化

## 核心策略

### RSI 均值回歸策略（已驗證）
- **進場**: RSI < 35
- **出场**: RSI > 65
- **持倉**: 最多20天
- **勝率**: 63-70%
- **平均報酬**: +1.5~+3% per trade

### 策略變形
| 策略 | 進RSI | 出RSI | 持倉 | 適用 |
|:-----|:-----:|:-----:|:----:|:-----|
| RSI_Rev_Low | <30 | >55 | 15天 | 保守 |
| **RSI_Rev_Mid** | <35 | >60 | 20天 | **主要** |
| RSI_Rev_High | <40 | >65 | 25天 | 積極 |
| RSI_Aggressive | <25 | >50 | 10天 | 超保守 |
| RSI_Breakout | <35 | >70 | 30天 | 擴展 |

## 數據庫

### 主資料庫
| 資料庫 | 大小 | 內容 |
|:-------|:----:|:-----|
| `maggy_ai_tech.db` | **9.0 MB** | 31檔AI/科技股，5年歷史 |
| `us_history.db` | **15.5 MB** | 76檔美股，3年歷史 |
| `maggy_rsi.db` | **2.0 MB** | 33檔RSI追蹤 |
| `maggy_sim_trades.db` | **256 KB** | 883筆模擬交易 |

### 數據表格
- `daily_ohlcv`: OHLCV + 技術指標（SMA/EMA/RSI/MACD/BB/ATR/KDJ）
- `stock_summary`: 當前價格/RSI/52w高低
- `sim_trades`: 模擬交易記錄
- `performance`: 策略績效

## AI/科技股池（31檔）

### 分類
| 類別 | 股票 |
|:-----|:-----|
| AI/GPU | NVDA, AMD, INTC |
| AI/雲端 | MSFT, AMZN, GOOGL |
| AI/企業 | CRM, NOW, PLTR, SNOW, NET, CRWD |
| AI/半導體 | TSM, ASML, AMAT, MU, LRCX, KLAC |
| AI/數據 | SNOW, DT, AI |
| 機器人 | TSLA, HON, IR |
| 區塊鏈 | COIN |
| AI ETF | VGT, SMH, SOXX |

## 歷史回測表現

### TOP 10 最佳股票/策略組合
| 排名 | 股票 | 策略 | 交易 | 勝率 | 總報酬 |
|:---:|:-----|:-----|:----:|:----:|:------:|
| 🥇 | COIN | RSI_Rev_Mid | 15 | 73.3% | +101.8% |
| 🥈 | UPST | RSI_Aggressive | 13 | 53.8% | +71.3% |
| 🥉 | KLAC | RSI_Rev_High | 13 | 76.9% | +59.7% |
| 4 | NOW | RSI_Breakout | 11 | 72.7% | +57.1% |
| 5 | SNOW | BB_Break | 10 | 70.0% | +54.5% |
| 6 | NET | RSI_Aggressive | 10 | 60.0% | +54.3% |
| 7 | AMAT | RSI_Rev_Mid | 11 | 81.8% | +46.3% |
| 8 | NVDA | RSI_Rev_High | 11 | 72.7% | +42.1% |
| 9 | ASML | RSI_Breakout | 11 | 63.6% | +40.2% |
| 10 | GOOGL | RSI_Rev_Mid | 12 | 83.3% | +33.8% |

## 當前市場評估（21:49）

### 進場信號
- **🔥 緊急進場**: HON (Honeywell) RSI=23.6

### 類別評估
| 狀態 | 類別 | 平均RSI |
|:-----|:-----|:-------:|
| 🟢 極佳 | Robotics | 35.0 |
| ⚪ 中性 | AI/Data, AI/Enterprise, AI/Security | 49-55 |
| 🔶 偏高 | AI/Semi Equip, Crypto/AI, Autonomous | 55-70 |
| 🔴 過熱 | AI/GPU, AI/Cloud, Tech ETF, Semi ETF | 70+ |

## 腳本工具

| 腳本 | 功能 |
|:-----|:-----|
| `build_maggy_ai_tech_db.py` | 建立AI/科技股資料庫 |
| `maggy_ai_backtest.py` | 策略回測優化 |
| `maggy_ai_screener.py` | AI股票篩選 |
| `maggy_ai_strategy.py` | 策略分析建議 |
| `maggy_sim_trading.py` | 模擬交易系統 |
| `maggy_enhanced_learning.py` | 深度學習優化 |

## 發展方向
1. 專注AI/科技股：NVDA, AMD, COIN, NOW, SNOW等
2. 持續優化RSI策略參數
3. 開發AI選股模型
4. 追蹤法人流向與市場情緒
5. 實現策略自動化