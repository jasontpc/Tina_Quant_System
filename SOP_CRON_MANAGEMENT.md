# Cron Job SOP — Tina 量化系統

**版本：** v1.0
**建立日期：** 2026-05-09
**適用範圍：** 所有 Tina 系統的 Cron Job 建立/更新/刪除

---

## 0. 核心原則

1. **Delivery 優先** — 沒有 delivery 的 job = 無法通知 = 失效
2. **Timeout 寧可多** — Cold Start + 模型推理需要足夠時間
3. **Isolation 保護** — 主要系統用 isolated session，避免被干擾
4. **最小化原則** — 同功能的 job 只留一個，刪除重複

---

## 1. 新建 Job 檢查清單

每次建立新 cron job 前，必須確認以下欄位：

| 欄位 | 預設值 | 最低要求 |
|:-----|:-------|:---------|
| `delivery.mode` | — | 必須是 `announce`，嚴禁 `none` |
| `delivery.to` | — | 必須是 `1616824689`，嚴禁留空 |
| `timeoutSeconds` | 30 | 分析類 >= 60s，複雜類 >= 120s |
| `sessionTarget` | main | 必須是 `isolated`，主要系統 jobs |
| `enabled` | false | 預設 false，完成測試後再改 true |

---

## 2. Timeout 參考標準

| 腳本類型 | 預設 timeout | 範例 |
|:---------|:------------|:-----|
| 簡單通知/查詢 | 30s | 天氣、小檢查 |
| 一般分析腳本 | 60s | 單一股票分析、簡報生成 |
| 複雜分析腳本 | 120s | 多股票掃描、完整市場分析 |
| 資料庫大量寫入 | 180s | 蒸餾、回測、DB 更新 |
| 非常規任務 | 300s | TW500 回測、Macro 掃描 |
| 全市場掃描 | 600s | 500 檔全面掃描 |

**原則：** Cold Start (~20s) + 模型推理 (~30-60s) + 腳本執行 = 總 timeout

---

## 3. Session Target 原則

| sessionTarget | 適用場景 | 風險 |
|:--------------|:---------|:-----|
| `isolated` | 主要系統 jobs（Tina/Leo/Nana/Ray）| 低風險，隔離執行 |
| `main` | 簡單、快速、一句話回覆 | 中風險，可能干擾主 session |

**規定：** 主要系統 jobs（每日分析、每日蒸餾、健檢）一律使用 `isolated`

---

## 4. Delivery 問題緊急修復流程

Step 1: 確認 job 是否仍需要
  -> 不需要：刪除
  -> 需要：Step 2

Step 2: 檢查 delivery 欄位
  -> mode=none：改為 `announce`
  -> 缺少 to：加上 `1616824689`

Step 3: 更新並重新啟用

---

## 5. 每週 Audit 清單（週日執行）

- [ ] 檢查所有 jobs 的 delivery 欄位是否正確
- [ ] 檢查有 error 的 jobs（連續 3 次即需修復/停用）
- [ ] 檢查 timeout 是否足夠
- [ ] 檢查是否有重複功能的多個 jobs

---

## 6. 常見錯誤與修正

| 錯誤 | 修正方式 |
|:-----|:---------|
| mode=none | -> announce，加 to:1616824689 |
| timeoutSeconds: 30（複雜腳本）| -> 120 或 180 |
| sessionTarget: main（主要系統）| -> isolated |

---

_最後更新：2026-05-09 by Tina_