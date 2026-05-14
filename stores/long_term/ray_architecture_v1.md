# Ray v3.5 系統架構藍圖
> 建立：2026-05-13 16:25

---

## 🏗️ 一、 系統核心架構 (The Core)

| 組件 | 名稱 | 職責 | 運行資源 |
|---|---|---|---|
| 實戰指揮官 | ray-v3.5 | 每日 05:00 固化重組，負責台美股實戰決策。 | 4B (2.7GB VRAM) |
| 智力總參謀 | qwen2.5:7b | 負責歷史蒸餾、大師對齊、盤前宏觀。 | 7B (4.7GB VRAM) |
| 深度歸因官 | ray-deep-v1 | 負責 Phase1 失敗分析、美股長線策略。 | 7B (4.7GB VRAM) |
| 終極仲裁者 | MiniMax 2.7 | 雲端備援，僅在「信心值 < 0.7」時介入。 | 雲端 API (節流模式) |

---

## 🕒 二、 24 小時暴力訓練與執行排程

| 時間 | 動作 | 執行腳本 | 核心模型 |
|---|---|---|---|
| 05:00 | 物理灌頂 | ray_distiller_auto.py | 4B (固化寫入) |
| 09:00 | 台股實戰 | ray_brain.py | ray-v3.5 (4B) |
| 14:00 | 邏輯蒸餾 | ray_knowledge_distiller.py | qwen2.5:7b |
| 14:05 | 失敗歸因 | ray_logic_distiller.py | ray-deep-v1 |
| 15:00 | 美股分析 | ray_us_strategy_analysis.py | ray-deep-v1 |
| 17:00 | 產業鏈對齊 | ray_web_collector.py | qwen2.5:7b |
| 21:00 | 宏觀接管 | ray_us_premarket_macro.py | qwen2.5:7b |
| 21:30 | 美股實戰 | ray_brain.py / us_scan_live.py | ray-v3.5 (4B) |

---

## 📜 三、 五大大師天條 (Axioms) 整合

系統每日將以下重點固化至 Ray-v3.5.Modelfile：

1. **Nassim Taleb (反脆弱)**：嚴禁肥尾風險，IV 異常時優先現金為王。
2. **Edward Thorp (凱利公式)**：信心值直接決定倉位，單筆虧損必限 1%。
3. **Jim Simons (模式識別)**：只在具備統計優勢的 Regime 交易，過濾雜訊。
4. **Larry Connors (均值回歸)**：RSI(2) 極端修正作為主觸發因子。
5. **Ray Dalio (多樣化)**：追蹤上下游產業鏈，檢查標的相關性，避免風險集中。

---

## ⚡ 四、 連網與 Token 優化方案 (Token Diet)

- **MiniMax 保衛戰**：21:00 的美股盤前新聞由本地 7B 接管，預計節省 40% API 配額。
- **CPU 暴力過濾**：利用 i9-13900H 在連網階段先剔除 80% 垃圾內容，不浪費 Token。
- **32GB RAM 快取**：將產業鏈映射、144 筆歷史修正存入 RAM，實現「檢索即決策」，無需 LLM 重複推理。

---

## 🛠️ 五、 自我修正與防禦系統 (Self-Fixer)

- **物理清理協議**：任何腳本切換模型前，強制執行 ollama stop 並冷卻 5 秒。
- **自動修正資料庫**：建立 system_fault_logs 與 logic_corrections 閉環。
- **產業鏈暴力追蹤**：17:00 生成 JSON 字典，供 4B 隔日直接查表（TSMC -> 上下游廠商清單）。

---

## 🚀 下一步執行清單 (To-Do)

| # | 項目 | 狀態 |
|---|---|:---:|
| 1 | 建立 `ray_us_strategy_analysis.py` (15:00 美股分析) | ✅ 已存在 |
| 2 | 建立 `ray_us_premarket_macro.py` (21:00 宏觀接管) | ✅ 已存在 |
| 3 | 更新 `llm_router.py`：信心值降級門檻上調至 **0.8** | ✅ 已設定 |
| 4 | 所有 7B 任務加入 `clear_vram()` 邏輯 | ✅ 已內建 |

---

_建立：2026-05-13 16:25_
_更新：2026-05-13 16:32_