# Leo 科技股波段團隊 — 索引文檔
> 最後更新：2026-04-26 16:13

## 📁 團隊結構

```
teams/leadtrades/leos/
├── leos_v65.py              # 主策略（v6.5）
├── leos_light.py            # 輕量版（Cron 使用）
├── leos_v70.py             # 整合版（v7.0，進場+停利/停損+法人）
├── leo_analysis.py         # 每日主動分析報告（v7.0）
├── leo_backtest.py         # 歷史回測系統（v7.0）
├── leo_sim_trade.py        # 模擬交易系統
├── leo_autonomous.py      # 主動分析學習系統（WFA 參數優化）
├── leo_institutional_flow.py # 法人資金流向追蹤
├── leos_trades.json        # 交易記錄
├── leos_analysis_report.json  # 分析報告
├── leos_backtest_report.csv  # 回測報告
└── INDEX.md                # 本索引
```

## 🎯 策略版本

| 版本 | 檔案 | 功能 | 執行頻率 |
|:----|:-----|:-----|:---------|
| v6.5 | `leos_v65.py` | 完整分析（RSI 45-70進場，15%停利，10%停損）| 按需 |
| 輕量版 | `leos_light.py` | Cron 快速掃描（60秒完成）| 每天5次 |

## 📊 當前持倉

| 代碼 | 名稱 | 進場價 | RSI | 狀態 |
|:----:|:-----|------:|----:|:-----:|
| 2379 | 瑞昱 | $539 | 64.4 | Open |
| 3034 | 緯穎 | $418 | 64.6 | Open |
| 2382 | 廣達 | $323 | 59.1 | Open |

## 📈 法人追蹤

| 代碼 | 名稱 | 法人總計 | RSI | 評分 |
|:----:|:-----|--------:|----:|-----:|
| 2330 | 台積電 | +47 | 81 OB | 33 |
| 2454 | 聯發科 | +26 | 90 OB | 28 |
| 2382 | 廣達 | -1 | 59 | 23 |

## 🔧 Cron 排程

| Job | 排程 | 腳本 | 頻率 |
|:----|:-----|:-----|:-----:|
| Leo v6.5 科技股波段 | `0 0,8,12,16,20` | `leos_light.py` | 5次/天 |
| Leo 法人資金流向 | `0 9,15` | `leo_institutional_flow.py` | 2次/天 |
| Leo v7.0 每日分析報告 | `0 10 * * *` | `leo_analysis.py` | 1次/天 |
| Leo v7.0 歷史回測 | `0 3 * * 0`（週日） | `leo_backtest.py` | 1次/週 |

## 📋 主要腳本說明

### leos_v65.py（完整版）
- 8檔科技股完整分析
- RSI 45-70 寬鬆進場
- 15% 停利 / 10% 停損
- 動量過濾 + MA20 偏離審查
- 分批進場（20%+20%）

### leos_light.py（輕量版）
- Cron 快速執行（<60秒）
- 8檔基本掃描
- 適合每20分鐘執行

### leo_institutional_flow.py（法人追蹤）
- 法人三大法人模擬
- Foreign / Investment Trust / Dealer 分項
- 結合 RSI + 動量 + MA 排列
- 生成進場推薦

## ⚠️ 當前市場狀態

- TWII RSI ~93（OVERBOUGHT）
- 全市場觀望，暫停新進場
- 等待 RSI 降至 70 以下

---

_Last Updated: 2026-04-26 16:13 GMT+8_