# 系統健檢報告 2026-05-14

## 1. DB 狀態

### 已刪除（0-byte 空DB）
| DB | 大小 | 動作 |
|:---|-----:|:-----:|
| `macro_db/macro.db` | 0 MB | ✅ 已刪除 |
| `us_financial/us_financial.db` | 0 MB | ✅ 已刪除 |
| `us_fund_flow/us_fund_flow.db` | 0 MB | ✅ 已刪除 |
| `tw_financial/tw_financial.db` | 0 MB | ✅ 已刪除 |

### 主資料庫現況（正常）
| DB | 大小 | 狀態 | 備註 |
|:---|-----:|:----:|:-----|
| `data/yfinance.db` | 113.2 MB | ✅ 正常 | 主力價格DB |
| `data/us_history.db` | 27.5 MB | ✅ 正常 | 美股歷史 |
| `data/leverage_etf.db` | 20.1 MB | ✅ 正常 | 槓桿/反向ETF |
| `data/sherry_etf.db` | 10.8 MB | ✅ 正常 | Sherry分析 |
| `data/macro_institutional.db` | 10.4 MB | ✅ 正常 | 法人資料 |
| `data/tw_history.db` | 9.5 MB | ✅ 正常 | 台股歷史 |
| `data/etf.db` | 7.1 MB | ✅ 正常 | ETF報價 |
| `data/finmind.db` | 0.8 MB | ✅ 正常 | FinMind API |
| `data/tw_margin.db` | 1.5 MB | ✅ 正常 | 信用交易 |
| `data/us_sim_trades.db` | 0.5 MB | ✅ 正常 | 模擬倉 |
| `teams/data/rsi_verification.db` | 3.7 MB | ✅ 正常 | RSI驗證 |
| `data/master_backtest.db` | 0.3 MB | ✅ 正常 | 主回測系統 |

### 待確認
| DB | 大小 | 建議 |
|:---|-----:|:-----|
| `yuan_zheng2.db` (0.1MB) | 0.1 MB | 確認 `yuan_zheng2_tracker.py` 是否仍在使用 |
| `tw_stock_registry.db` (0.2MB) | 0.2 MB | 確認是否被 `batch_backtest_500.py` 引用 |

---

## 2. 腳本缺陷

### 高優先修復
| 腳本 | 缺陷 | 嚴重性 | 狀態 |
|:-----|:-----|:------:|:-----:|
| `scripts/batch_backtest_500.py` | `urllib` 在 function 內 local import（非頂層）→ 可能在某些情況下 NameError | 🟡 中 | 已知：行85/91有 local import，不影響主要流程但代碼品質不佳 |
| `scripts/trinity_analysis.py` | FutureWarning: `Series.__getitem__ treating keys as positions`（已知的 pandas 未來版本相容性） | 🟢 低 | 裝飾器有問題，但可正常運行 |
| `scripts/tw_trinity_scan.py` | 之前掃描結果為 0（TWII RSI nan，MA60 len=0） | 🔴 高 | 已修正：改用 `period='6mo'` 獲取足夠數據 |

### Archive 清理（131個過時腳本）
- `archive/cleanup/` 共有 **131 個腳本**
- 大量 `build_*`、`ray_*`、`nana_*` 歷史版本
- 建議：建立 `archive/cleanup/TO_DELETE/` 分類，90天後確認無引用後批量刪除

### Scripts 現況（273個腳本）
- `scripts/` 目錄包含大量一次性分析腳本（`analyze_2454.py`、`analyze_2492.py`等）
- 建議：建立 `scripts/active/` vs `scripts/archive/` 分類

---

## 3. 健檢制度缺陷分析（Jo 的觀察）

### 系統性問題（來自 Jo 的整合藍圖）

| 標籤 | 問題 | 根本原因 | 建議修復 |
|:-----|:-----|:--------|:---------|
| `[VRAM_LEAK]` | 4050 6GB VRAM 不足導致 timeout | `ollama` 進程未正確釋放 | 強化 `@ray_singleton` 的 `ollama stop --all` |
| `[STALE_LOGIC]` | 舊固化規則不再適用 | 144筆修正等歷史數據包袱 | 05:00 蒸餾時清理勝率<50%的規則 |
| `[LOCK_TIMEOUT]` | 持有 lock 超過30分鐘 | 某些腳本長期佔用資源 | 10分鐘死鎖自動判定 [STUCK_PROCESS] |
| `[MARKET_OPEN_BLOCK]` | 開盤期間執行重任務 | `@market_safe_guard` 漏網 | 確認所有回測/Cron Job 都已註冊 decorator |
| `[IO_WRITE_FAIL]` | Edit failed / 寫入失敗 | `io_singleton` 未正確保護 | 確認所有日誌寫入都經過 `@io_singleton` |

---

## 4. Cron Job Log 摘要

| Job | 排程 | 錯誤次數 | 最後錯誤 | 修復建議 |
|:----|:-----|:--------:|:---------|:---------|
| Tina 自主決策五大層 | 11:00 | 2次 timeout | cold start + 模型推理 185s | ✅ 已修正：timeout 300→450s |
| Phase2 7B蒸餾 | 05:00 | 0 | 正常 | 持續監控 |
| Ray 全語意固化重生 | 05:00 | 0 | 正常 | — |

---

## 5. Jo 的整合藍圖 → 執行追蹤

### 已實現 ✅
| 項目 | 說明 |
|:-----|:-----|
| `@market_safe_guard` | ✅ 已實作：台股 08:55-13:35 / 美股 21:25-04:05 禁區 |
| `@ray_singleton` | ✅ 已實作：VRAM 30分鐘死鎖 + 60秒破門（08:30預載）|
| `@io_singleton` | ✅ 已實作：I/O 5分鐘死鎖保護 |
| 三位一體標籤化 | ✅ 已實作：MA/MACD/KDJ 三層篩選 |
| Archive清理 | ⚠️ 131個檔案待清理 |

### 待實現 🔲
| 項目 | 說明 |
|:-----|:-----|
| 健康股標籤化（VOL_BREAKOUT / INSTITUTIONAL_SUPPORT）| 尚未整合進 `streamlit_tw_stock.py` |
| 7B滾動回測（移除144筆束縛）| 尚未實作 |
| 4B決策選單（[1]執行 [2]略過 [3]深度）| Modelfile 已有，需對接 Cron |
| VRAM 10分鐘死鎖報警 | 尚未實作 |
| 崩潰日誌自動歸因（NETWORK_LATENCY / API_LIMIT_CRASH）| 尚未實作 |

---

## 6. 立即執行的修復

- ✅ 刪除 4 個 0-byte 空DB
- 🔲 `tw_trinity_scan.py` 已修正（`period='6mo'`）
- 🔲 `trinity_analysis.py` FutureWarning 待修（pandas 版本相容性）

_Report generated: 2026-05-14 by Tina health_check agent_