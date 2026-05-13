=== Ray Tina System SOP 總結 ===

## 已建立的檔案

1. RAY_SOP.md          — 完整標準作業程序文件
2. tina_ray_daily.ps1  — 日間自動化腳本（每日 08:30-18:30）
3. tina_ray_weekly.ps1 — 每週蒸餾腳本（週五 22:00）
4. ray_scheduler_setup.ps1 — Windows 任務排程器設定（PowerShell 語法問題待修復）

## 每日排程

| 任務 | 時間 | 功能 |
|------|------|------|
| Ray Tina Morning | 平日 08:30 | 盤前掃描（us_momentum） |
| Ray Tina Evening | 平日 17:00 | 蒸餾 + 權重更新 |
| Ray Tina Weekly | 週五 22:00 | Unsloth 微調 |

## 效能瓶頸與改善

1. 7B 冷啟動 ~32-43s → 每日 07:50 預熱
2. backtest_reports = 0 → 門檻放寬（日間模式 Sharpe > 0.8）
3. wisdom_logs 無 symbol → 已有 LEFT JOIN 補償

## 手動執行

powershell -ExecutionPolicy Bypass -File C:\Users\USER\.openclaw\agents\ray\tina_ray_daily.ps1

## 已完成的整合

- ray_engine.py: RSI/RSI2 指標 ✅
- ray_evolution.py: RSI2 康諾斯策略 ✅  
- ray_brain.py: deep_model → ray-deep-v1 ✅
- ray_self_correct.py: 雙層 LLM（1.5B + 7B）✅
- wisdom_corrections: 10 筆已寫入