# Tina 量化系統 — 推廣方案

## 現況評估（2026-05-07）

### 系統規模
| 元件 | 規模 |
|:-----|-----:|
| streamlit_tw_stock.py | 2,391 行 / 96KB |
| 團隊腳本總數 | ~196 支 |
| Leo paper trades | 106 口（全部 open） |

### 現有團隊分工
| 團隊 | 功能 | 腳本數 |
|:-----|:-----|-------:|
| **Nana** | 波段操作（個股） | 67 |
| **Leo** | 科技股波段 AI | 33 |
| **Ray** | 台股/美股 ETF DCA | 32 |
| **Sherry** | 主觀/消息面 | 9 |
| **Maggy** | 數據分析 | 28 |
| **Automation** | 排程/通知 | 5 |

### 核心能力（已驗證）
- ✅ Yahoo Finance 即時股價
- ✅ FinMind 法人資料
- ✅ Streamlit Cloud 部署
- ✅ Telegram 推播
- ✅ 波段策略回測（勝率 67-82%）
- ✅ 每日自動化 Cron 排程

---

## 推廣方案：MVP 版本（目標：3-5 個團隊使用）

### 策略一：API 即服務（推薦）

**做法：** 將 Tina 系統重構為一套 **REST API + 前端**，其他團隊可透過 API 調用核心功能（分析、篩選、推播）。

**優點：**
- 其他團隊無需自己架基礎設施
- 維護簡單（一份代碼）
- 可收費或當作 SaaS

**缺點：**
- 需要穩定托管環境
- 涉及資料安全/隱私

### 策略二：GitHub 模板（簡單）

**做法：** 把 Tina 系統打包成 **GitHub Template**，其他團隊一鍵 fork 後修改參數即可用。

**優點：**
- 最快上手
- 無需托管

**缺點：**
- 每個團隊各自維護一份 fork
- 更新困難（要手動 merge）

### 策略三：Streamlit Cloud 多租戶

**做法：** 將前端改為 **多團隊版本**（切換組織），用同一個 App 服務多個團隊。

**優點：**
- 統一維護
- 即時更新

**缺點：**
- 需要處理資料隔離
- 需付費升級 Streamlit Cloud

---

## 推薦：策略一（API SaaS）

### 第一階段：系統整理（1-2週）
1. 提取核心分析函數（`analyze()`, `screen()`, `backtest()`）為獨立的 Python library
2. 建立 FastAPI 包裝成 REST API
3. 串接 LINE / Discord 推播（其他團隊可能不在 Telegram）
4. 寫一份 API 文件

### 第二階段：部署與推廣（2-4週）
1. 部署到 Render.com 或 Railway（免費 tier）
2. 整理 GitHub README / 使用手冊
3. 聯繫其他團隊試用
4. 根據回饋修正

---

## 大腦優化建議

現有腳本最大問題是 **缺乏統一架構**，每個團隊各自為政。建議：

```
tina_core/
├── api/                  # FastAPI endpoints
├── analyzers/           # 分析引擎（各團隊共享）
│   ├── base.py          # 統一介面
│   ├── nana.py          # Nana 分析邏輯
│   ├── leo.py           # Leo 分析邏輯
│   └── ray.py           # Ray 分析邏輯
├── data/                # 資料來源
│   ├── yfinance.py
│   └── finmind.py
├── reports/             # 報告生成
└── cli/                 # 指令列工具
```

**立即可執行的事：**
1. 把 `streamlit_tw_stock.py` 的 `analyze()` 抽出成獨立模組
2. 建立 `requirements.txt` 統一依賴
3. 寫 `README.md` 讓其他團隊看得懂怎麼用

---

## 需要 Jo 決策的事

1. **目標對象：** 哪些團隊？想推給量化社群還是特定產業？
2. **商業模式：** 免費？月費？一次性？
3. **托管意願：** 願意花時間維護 API 服務嗎？
4. **優先順序：** 現有 Streamlit Cloud 的 bug（SEND TELEGRAM）和這個推廣案，哪個優先？

建議先專心修完 Send Telegram bug，再開始推廣規劃。