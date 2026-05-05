# Stock Strategy Daily Report
**2026-05-02 08:11**

— Tina Quant System v3.12


---

## ENTRY_WATCH (5 stocks)

| Stock | Name | Price | RSI14 | BIAS20 | VolRatio | Score | Failed |
|-------|------|-------|-------|--------|----------|-------|--------|
| 2330 | 台積電 | 2135.0 | 62.6 | 4.52 | 1.32 | 5/7 | rsi_ideal |
| 2382 | 廣達 | 312.5 | 44.9 | -1.23 | 0.81 | 6/7 | — |
| 3034 | 緯穎 | 409.0 | 58.6 | 0.97 | 0.65 | 5/7 | rsi_ideal |
| 4961 | 力旺 | 152.5 | 49.5 | -1.61 | 0.92 | 6/7 | — |
| RIVN | Rivian | 15.02 | 43.0 | -7.24 | 2.09 | 5/7 | ma_slope |

## All 27 Stocks Summary

| Stock | Name | Market | Type | Signal | Score | Price | RSI |
|-------|------|--------|------|--------|-------|-------|-----|
| 0050 | 元大台灣50 | TW | etf | NO_SIGNAL | 3/7 | 90.5 | 79.1 |
| 0056 | 元大高股息 | TW | etf | NO_SIGNAL | 4/7 | 40.9 | 74.9 |
| 00646 | 富邦S&P500 | TW | etf | NO_SIGNAL | 4/7 | 70.95 | 84.1 |
| 00713 | 元大高息低波 | TW | etf | NO_SIGNAL | 4/7 | 52.85 | 55.1 |
| 2317 | 鴻海 | TW | tech | NO_SIGNAL | 3/7 | 219.5 | 70.2 |
| 2330 | 台積電 | TW | semi | ENTRY_WATCH | 5/7 | 2135.0 | 62.6 |
| 2345 | 智邦 | TW | tech | NO_SIGNAL | 3/7 | 2280.0 | 71.9 |
| 2382 | 廣達 | TW | tech | ENTRY_WATCH | 6/7 | 312.5 | 44.9 |
| 2454 | 聯發科 | TW | semi | NO_SIGNAL | 3/7 | 2610.0 | 89.1 |
| 3017 | 奇鋐 | TW | tech | NO_SIGNAL | 3/7 | 2835.0 | 75.0 |
| 3034 | 緯穎 | TW | tech | ENTRY_WATCH | 5/7 | 409.0 | 58.6 |
| 3665 | 穎崴 | TW | tech | NO_SIGNAL | 3/7 | 2770.0 | 78.8 |
| 4961 | 力旺 | TW | tech | ENTRY_WATCH | 6/7 | 152.5 | 49.5 |
| BILL | Bill Holdings | US | fintech | NO_SIGNAL | 2/7 | 39.07 | 59.4 |
| BMY | Bristol-Myers Squibb | US | pharma | NO_SIGNAL | 4/7 | 58.22 | 50.6 |
| COIN | Coinbase | US | fintech | NO_SIGNAL | 4/7 | 191.25 | 58.3 |
| D | Dominion Energy | US | utility | NO_SIGNAL | 4/7 | 63.94 | 55.5 |
| DXCM | DexCom | US | medtech | NO_SIGNAL | 4/7 | 61.35 | 45.0 |
| ESTC | Elastic | US | cloud | NO_SIGNAL | 2/7 | 48.61 | 60.4 |
| GTLB | GitLab | US | cloud | NO_SIGNAL | 1/7 | 24.05 | 71.3 |
| NET | Cloudflare | US | cloud | NO_SIGNAL | 2/7 | 217.5 | 73.5 |
| PATH | UiPath | US | cloud | NO_SIGNAL | 3/7 | 10.67 | 58.4 |
| RIVN | Rivian | US | ev | ENTRY_WATCH | 5/7 | 15.02 | 43.0 |
| SMCI | Super Micro Computer | US | tech | NO_SIGNAL | 2/7 | 27.09 | 54.3 |
| SO | Southern Company | US | utility | NO_SIGNAL | 4/7 | 96.71 | 53.2 |
| SOFI | SoFi Technologies | US | fintech | NO_SIGNAL | 3/7 | 16.43 | 46.4 |
| U | Unity Software | US | cloud | NO_SIGNAL | 1/7 | 27.13 | 70.3 |

---

## Strategy Parameter Reference

| Stock | RSI Ideal | RSI Max | BIAS20 Max | MA Slope Min | Vol Min |
|-------|-----------|---------|------------|-------------|---------|
| 0050 | 42-58 | 65 | 5 | 0.2 | 100萬 |
| 0056 | 40-56 | 62 | 5 | 0.1 | 50萬 |
| 00646 | 40-58 | 65 | 5 | 0.2 | 20萬 |
| 00713 | 40-55 | 60 | 5 | 0.1 | 20萬 |
| 2317 | 38-55 | 62 | 8 | 0.3 | 40萬 |
| 2330 | 40-55 | 65 | 8 | 0.5 | 50萬 |
| 2345 | 36-52 | 60 | 8 | 0.3 | 15萬 |
| 2382 | 38-52 | 60 | 7 | 0.3 | 30萬 |
| 2454 | 40-54 | 63 | 7 | 0.4 | 30萬 |
| 3017 | 35-50 | 58 | 7 | 0.2 | 20萬 |
| 3034 | 38-52 | 60 | 7 | 0.3 | 10萬 |
| 3665 | 35-50 | 58 | 6 | 0.2 | 10萬 |
| 4961 | 35-50 | 58 | 6 | 0.2 | 5萬 |
| BILL | 38-54 | 62 | 8 | 0.3 | ratio |
| BMY | 38-54 | 60 | 5 | 0.1 | ratio |
| COIN | 35-52 | 60 | 10 | 0.5 | ratio |
| D | 38-55 | 60 | 5 | 0.1 | ratio |
| DXCM | 38-55 | 62 | 8 | 0.4 | ratio |
| ESTC | 38-54 | 62 | 8 | 0.3 | ratio |
| GTLB | 38-54 | 62 | 8 | 0.3 | ratio |
| NET | 38-54 | 62 | 8 | 0.4 | ratio |
| PATH | 38-54 | 62 | 8 | 0.3 | ratio |
| RIVN | 32-50 | 58 | 10 | 0.3 | ratio |
| SMCI | 38-54 | 62 | 8 | 0.4 | ratio |
| SO | 38-55 | 60 | 5 | 0.1 | ratio |
| SOFI | 35-52 | 60 | 10 | 0.3 | ratio |
| U | 38-54 | 62 | 9 | 0.3 | ratio |
