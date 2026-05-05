# Ray 台股ETF定期定額團隊 — 索引文檔
> 最後更新：2026-04-26 20:50

## 📁 團隊結構

```
teams/ray/
├── scripts/
│   ├── ray_dca_portfolio.py      # DCA 組合建議
│   ├── dca_backtest.py          # DCA 回測系統
│   ├── ray_wfa.py               # WFA 參數優化
│   ├── ray_backtest.py           # 獨立回測
│   ├── ray_sim_trade.py          # DCA 模擬追蹤
│   └── ...
├── reports/
│   ├── dca_market_brief.json     # 每日市場簡報
│   ├── dca_portfolio_plan.json  # 組合計劃
│   ├── ray_wfa_results.json     # WFA 結果
│   └── ...
├── dca_market_brief.py           # 輕量市場分析（Cron使用）
├── ray_autonomous_develop.py     # 自主開發腳本
└── INDEX.md                     # 本索引
```

## 🎯 策略版本

| 版本 | 檔案 | 功能 |
|:-----|:-----|:-----|
| **當前** | `dca_market_brief.py` | 輕量版（Cron 使用，60秒完成）|
| 組合版 | `ray_dca_portfolio.py` | 完整 DCA 組合建議 |

## 📊 當前 DCA 組合

| 配置 | ETF | 現價 | 位置 |
|:-----|:----|-----:|-----:|
| 核心（70%）| 0050 元大台灣50 | $89.95 | 100% |
| 核心（70%）| 00646 富邦S&P500 | $70.35 | 100% |
| 衛星（20%）| 00878 國泰永續高息 | $25.00 | 98.5% |
| 衛星（20%）| 00919 群益台灣精選 | $23.50 | 92% |
| 現金（10%）| 2618 航空雙雄 | $33.75 | — |

## 📈 回測結果

| ETF | 總報酬 | Sharpe | MaxDD |
|:----|------:|-------:|------:|
| 0050 | +13,052% | 1.97 | -23.6% |
| 0056 | +8,056% | 1.80 | -20.4% |
| 00878 | +7,687% | 1.83 | -18.7% |
| 00919 | +5,831% | 1.97 | -18.8% |

## 🔧 Cron 排程

| Job | 排程 | 腳本 | 頻率 |
|:----|:-----|:-----|:-----:|
| Ray DCA 市場分析 | `0 16 * * *` | `dca_market_brief.py` | 1次/天 |
| Ray 每週DCA檢視 | `0 3 * * 1` | — | 1次/週 |

## ⚠️ 當前市場狀態

- TWII RSI ~93（OVERBOUGHT）
- 全部 DCA 暫停（HOLD x0）
- 等待市場回調至 RSI < 70

---

_Last Updated: 2026-04-26 20:50 GMT+8_