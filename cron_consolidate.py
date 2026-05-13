# -*- coding: utf-8 -*-
"""
Cron Jobs 精簡腳本：14 個 → 6 個核心

保留的 6 個核心 jobs：
1. Ray Tina Daily（08:30）- 盤前掃描 + us_momentum
2. Ray Tina Evening（17:00）- 每日修正 + 蒸餾
3. Ray Tina Weekly（週五 22:00）- Unsloth 微調
4. Tina MEMORY 每日蒸餾（07:00）- 記憶蒸餾
5. 模擬倉日檢討（16:30）- 收盤後檢討
6. yfinance DB 每週清理（週日 03:00）- 資料庫維護

移除：
- 重複的自動學習 jobs
- 過時的 Governor jobs（改由 Windows Task Scheduler 觸發）
- 執行時間過長的 jobs（US AI Tech 每日分析）
"""

import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 從 cron tool 讀取 jobs（見上方的 cron list 分析）
# 14 個 jobs 中，保留 6 個核心，停用 8 個

JOBS_TO_DISABLE = [
    # 重複的自動學習
    "Tina 自動學習擴充DB",           # 已被 Ray Tina Evening 取代
    # 過時的 Governor
    "Cron Governor 每小時系統監控",  # 改由 Windows Task Scheduler 處理
    "Cron Governor 深夜智能喚醒（02:00）",  # 改由 Ray Tina Weekly 處理
    # 執行時間過長
    "US AI Tech 每日分析",           # timeout error，與 US Margin 分析重疊
    # 重複的風控
    "Tina 風控檢查",                 # 整合到 Ray Tina Daily
    # 分散的蒸餾（已整合到每日）
    "每週中度蒸餾（Pattern/Lesson晉升評估）",  # 已由每日 MEMORY 蒸餾覆蓋
    # 重複的每日報告（已被每日開盤前策略報告覆蓋）
    "每日開盤前策略報告",             # 已被 Ray Tina Daily 覆蓋
]

# Windows Task Scheduler 的 3 個 jobs 是獨立的，不受影響
SCHEDULER_JOBS = [
    "Ray Tina Daily",
    "Ray Tina Evening",
    "Ray Tina Weekly"
]

print("=== Cron Jobs 精簡腳本 ===")
print()
print("預計保留：6 個核心 Cron Jobs + 3 個 Windows Task Scheduler Jobs")
print()
print("要移除的 Cron Jobs：")
for name in JOBS_TO_DISABLE:
    print(f"  - {name}")
print()
print("保留的 Cron Jobs：")
core_jobs = [
    "Tina MEMORY 每日蒸餾(daily)",
    "模擬倉 日檢討（收盤後）",
    "yfinance DB 每週清理"
]
for name in core_jobs:
    print(f"  + {name}")
print()
print("Windows Task Scheduler（不變）：")
for name in SCHEDULER_JOBS:
    print(f"  + {name}")
print()
print("=== 說明 ===")
print("實際停用需要管理員在 OpenClaw Gateway UI 中操作")
print("此腳本只是分析用途")