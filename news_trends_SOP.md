# News Trends Database — 標準作業程序

> 建立各國財經新聞趨勢資料庫，每日更新，追蹤市場情緒與產業動態。

---

## 📁 檔案結構

```
Tina_Quant_System/
├── data/news_trends.db          ← 主資料庫
└── scripts/
    ├── news_trends/
    │   ├── init_news_trends_db.py      ← 初始化資料庫
    │   ├── crawler_base.py              ← 爬蟲基底類
    │   ├── news_tw.py                   ← 台灣新聞
    │   ├── news_us.py                   ← 美國新聞
    │   ├── news_jp.py                   ← 日本新聞
    │   ├── news_kr.py                   ← 韓國新聞
    │   ├── news_cn.py                   ← 中國新聞
    │   ├── news_eu.py                   ← 歐洲新聞
    │   ├── news_aggregator.py           ← 彙整腳本（每日更新）
    │   └── news_trends_report.py       ← 分析報告
    └── news_trends_cron.py              ← Cron 驅動主程式
```

---

## 🗄️ 資料庫 Schema

### Table: `news_articles`
| 欄位 | 型別 | 說明 |
|:-----|:-----|:-----|
| id | INTEGER PRIMARY KEY | 自動遞增 |
| country | TEXT | TW/US/JP/KR/CN/EU |
| date | TEXT | YYYY-MM-DD |
| datetime | TEXT | YYYY-MM-DD HH:MM:SS |
| category | TEXT | 產業/總經/個股/央行 |
| headline | TEXT | 新聞標題 |
| content | TEXT | 摘要內容 |
| sentiment | REAL | -1.0 ~ +1.0 |
| sentiment_score | INTEGER | 複雜度評分 1-5 |
| source | TEXT | 新聞來源 |
| url | TEXT | 原文連結 |
| related_stocks | TEXT | 相關股票代碼（逗號分隔）|
| fetched_at | TEXT | 抓取時間 |

### Table: `daily_trends`
| 欄位 | 型別 | 說明 |
|:-----|:-----|:-----|
| country | TEXT | 國別 |
| date | TEXT | YYYY-MM-DD |
| avg_sentiment | REAL | 當日平均情緒 |
| article_count | INTEGER | 文章數量 |
| hot_categories | TEXT | 最熱門類別（JSON）|
| hot_stocks | TEXT | 最熱門股票（JSON）|
| trend_direction | TEXT | bullish/bearish/neutral |

### Table: `sources`
| 欄位 | 型別 | 說明 |
|:-----|:-----|:-----|
| country | TEXT | 國別 |
| source_name | TEXT |來源名稱 |
| source_url | TEXT | 來源首頁 |
| priority | INTEGER | 優先級 1-3 |
| last_fetch | TEXT | 上次抓取時間 |

---

## 🌐 各國新聞來源

### 🇹🇼 台灣 (TW)
| source | URL | 說明 |
|:-------|:----|:-----|
| yfinance | yfinance | 個股新聞（已有）|
| UDN | udn.com | 經濟日報系 |
| cnyes | cnyes.com | 鉅亨網 |
| money.udn | money.udn.com |  Money |

### 🇺🇸 美國 (US)
| source | URL | 說明 |
|:-------|:----|:-----|
| yfinance | yfinance | 個股新聞（已有）|
| Benzinga | benzinga.com | 財經新聞網 |
| Reuters | reuters.com | 路透社 |
| Seeking Alpha | seekingalpha.com | 分析平台 |

### 🇯🇵 日本 (JP)
| source | URL | 說明 |
|:-------|:----|:-----|
| Yahoo Finance JP | finance.yahoo.co.jp | 首位 |
| Nikkei | nikkei.com | 日經 |

### 🇰🇷 韓國 (KR)
| source | URL | 說明 |
|:-------|:----|:-----|
| Naver Finance | finance.naver.com | 首位 |
| Yonhap | yonhapnews.co.kr | 韓聯社 |

### 🇨🇳 中國 (CN)
| source | URL | 說明 |
|:-------|:----|:-----|
| Sina Finance | finance.sina.com.cn | 新浪財經 |
| Tencent Finance | finance.qq.com | 騰訊財經 |

### 🇪🇺 歐洲 (EU)
| source | URL | 說明 |
|:-------|:----|:-----|
| Yahoo Finance UK | uk.finance.yahoo.com | 英國 |
| Euronext | euronext.com | 歐交所 |

---

## 📊 情緒分析演算法

### 關鍵字法（基礎）
```python
POSITIVE = ['漲','突破','新高','利多','成長','優於','買進','看好','大漲','強勁','beats','bullish','upgrade','gain','rally','soar']
NEGATIVE = ['跌','跌破','新低','利空','衰退','不如','賣出','虧','看淡','大跌','疲弱','miss','bearish','downgrade','fall','drop','plunge']
```

### 加權計算
- 基礎分：正面 +0.15/關鍵字，負面 -0.15/關鍵字
- 範圍：-1.0 ~ +1.0
- 複合標題加強情緒（如「大漲」+ 「突破新高」→ 更高）

### 行業分類標籤
- `semiconductor`: 台積電、輝達、AI相關
- `banking`: 金融銀行
- `energy`: 能源
- `retail`: 零售消費
- `macro`: 央行、GDP、CPI
- `earnings`: 財報相關

---

## 🔄 更新頻率

| 排程 | 時間 | 說明 |
|:-----|:-----|:-----|
| Morning | 08:00 | 各國晨間新聞 |
| Afternoon | 14:00 | 盤中快報 |
| Evening | 20:00 | 盤後總結 |

---

## ⚙️ Cron Job 設定

```bash
# news_trends_cron.py - 各國新聞更新
0 8,14,20 * * * python C:\Users\USER\.openclaw\workspace\Tina_Quant_System\scripts\news_trends_cron.py

# 設定 timeout: 120s（網路抓取需要時間）
```

---

## 📋 產出報告

### 每日情緒報告（news_trends_report.py）
- 各國市場情緒分數
- 熱門股票/產業
- 趨勢方向（看漲/看跌/中立）
- 與前日比較

### 每週摘要（每週日 22:00）
- 本週情緒趨勢圖
- 重大新聞回顧
- 產業輪動分析

---

## 🔧 維護項目

| 項目 | 頻率 | 說明 |
|:-----|:-----|:-----|
| 資料庫清理 | 每週 | 刪除 >90天 新聞 |
|來源有效性檢查|每月|確認URL仍可訪問|
|情緒模型調整|每季|根據準確度回測更新|

---

_建立日期: 2026-05-08_
_版本: v1.0_