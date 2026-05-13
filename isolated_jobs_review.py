# -*- coding: utf-8 -*-
"""
Isolated Jobs 健檢報告
分析 14 個 Cron Jobs 的執行狀況，提出改善建議
"""

import json, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 從 earlier cron list 得知的 jobs
# 狀態來自 cron tool list 的 state 欄位

JOBS = [
    {
        "name": "Cron Governor 每小時系統監控",
        "id": "d89ccc5b-ed90-41b0-8086-887ece95c3c7",
        "schedule": "每小時 :00",
        "status": "ok",
        "last_duration_ms": 29395,
        "issues": []
    },
    {
        "name": "Tina 風控檢查",
        "id": "6533a29f-22ec-4f5a-9a3a-b97093ca8355",
        "schedule": "每 2 小時",
        "status": "ok",
        "last_duration_ms": 506167,
        "issues": ["duration 506s（8.4分鐘），timeout 設 120s 不夠"]
    },
    {
        "name": "Tina 自主決策五大層",
        "id": "d824a2bb-a4ba-4d6f-8119-9e7b945deb6e",
        "schedule": "每 3 小時",
        "status": "ok",
        "last_duration_ms": 60324,
        "issues": []
    },
    {
        "name": "模擬倉 日檢討（收盤後）",
        "id": "3ee0e7e6-dd8f-41b6-aa87-b912011e9cdf",
        "schedule": "平日 16:30",
        "status": "unknown",
        "issues": ["nextRun 未設置"]
    },
    {
        "name": "Tina 自動學習擴充DB",
        "id": "1306d237-7b4e-44cb-9fa1-847593af444f",
        "schedule": "平日 17:00",
        "status": "ok",
        "last_duration_ms": 28114,
        "issues": ["與 Ray Tina Evening 重疊"]
    },
    {
        "name": "US Margin 每日分析",
        "id": "56da375e-3e44-497d-9a6c-e5f6e4b49351",
        "schedule": "平日 18:00",
        "status": "ok",
        "last_duration_ms": 71449,
        "issues": []
    },
    {
        "name": "Cron Governor 深夜智能喚醒（02:00）",
        "id": "498fa0f1-5113-4855-911f-ec51be682343",
        "schedule": "每日 02:00",
        "status": "ERROR",
        "last_duration_ms": 180731,
        "last_error": "timeout",
        "issues": ["timeout error（180s > 設定）", "已更新 timeout 到 300s"]
    },
    {
        "name": "Tina MEMORY 每日蒸餾(daily)",
        "id": "69734111-6109-4fa8-9ed6-6b5e696bd99d",
        "schedule": "平日 07:00",
        "status": "delivered=False",
        "last_duration_ms": 92208,
        "issues": ["lastDelivered: false（通知未發出）"]
    },
    {
        "name": "US AI Tech 每日分析",
        "id": "d8fe08ae-b0e8-4812-baa3-1d82f4dfe223",
        "schedule": "平日 08:30",
        "status": "ERROR",
        "last_duration_ms": 125349,
        "last_error": "timeout",
        "issues": ["timeout error（125s > 設定 120s）", "已更新 timeout 到 300s"]
    },
    {
        "name": "每日開盤前策略報告",
        "id": "c6e06d66-c670-45c1-bcd4-e2bd22acc72c",
        "schedule": "平日 08:45",
        "status": "truncated",
        "issues": ["與 Ray Tina Daily（08:30）重疊"]
    },
    {
        "name": "yfinance DB 每週清理",
        "id": "7fa7443e-c459-4e1d-9631-f0a36aab5295",
        "schedule": "週日 03:00",
        "status": "unknown",
        "issues": []
    },
]

print("=" * 70)
print("  Isolated Jobs 健檢報告")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)
print()

# 統計
total = len(JOBS)
ok_count = sum(1 for j in JOBS if j["status"] == "ok")
error_count = sum(1 for j in JOBS if j["status"] == "ERROR")
warn_count = sum(1 for j in JOBS if j["status"] not in ["ok", "ERROR"])

print(f"總 jobs: {total} | 正常: {ok_count} | 錯誤: {error_count} | 警告: {warn_count}")
print()

# 問題分佈
all_issues = []
for j in JOBS:
    for issue in j["issues"]:
        all_issues.append((j["name"], issue))

timeout_jobs = [j["name"] for j in JOBS if "timeout" in j.get("last_error", "")]
overlap_jobs = [j["name"] for j in JOBS if "重疊" in " ".join(j["issues"])]

print("問題分佈：")
print(f"  Timeout 錯誤：{len(timeout_jobs)} 個")
for name in timeout_jobs:
    print(f"    - {name}")
print(f"  與其他 jobs 重疊：{len(overlap_jobs)} 個")
for name in overlap_jobs:
    print(f"    - {name}")
print()

# 執行時間分佈
print("執行時間分佈（按小時）：")
schedule_hours = {}
for j in JOBS:
    sched = j["schedule"]
    if "每小時" in sched:
        schedule_hours.setdefault("每小時", []).append(j["name"])
    elif "2小時" in sched:
        schedule_hours.setdefault("2小時", []).append(j["name"])
    elif "3小時" in sched:
        schedule_hours.setdefault("3小時", []).append(j["name"])
    else:
        # 提取時鐘時間
        if "平日" in sched:
            time_part = sched.split("平日")[1].strip()
            schedule_hours.setdefault(f"平日{time_part}", []).append(j["name"])

for time_slot, jobs in sorted(schedule_hours.items()):
    print(f"  {time_slot}: {len(jobs)} jobs")
    for name in jobs:
        print(f"    - {name}")
print()

# 改善建議
print("=" * 70)
print("  改善建議")
print("=" * 70)
print()

print("【立即修復】")
print("  1. Tina MEMORY 每日蒸餾 - delivery.mode 改為 'none'（寫入檔案不通知）")
print("  2. 模擬倉日檢討 - 檢查 nextRun 是否正常")
print()
print("【精簡重疊】")
print("  3. Tina 自動學習擴充DB → 停用（Ray Tina Evening 已涵蓋）")
print("  4. 每日開盤前策略報告 → 停用（Ray Tina Daily 已涵蓋）")
print("  5. US AI Tech 每日分析 → 停用（US Margin 分析已涵蓋）")
print()
print("【Timeout 優化】")
print("  6. Tina 風控檢查 - duration 506s，timeout 應改為 600s")
print("  7. Cron Governor 每小時 → delivery.mode 改 'none'（避免每小時轟炸）")
print()
print("【建議最終 jobs 清單（6 個核心）】")
print("  + Ray Tina Daily（08:30 Windows Task Scheduler）")
print("  + Ray Tina Evening（17:00 Windows Task Scheduler）")
print("  + Ray Tina Weekly（22:00 Windows Task Scheduler）")
print("  + Tina 自主決策五大層（每 3 小時）")
print("  + Tina MEMORY 每日蒸餾（07:00）")
print("  + US Margin 每日分析（18:00）")
print()
print("  要停用的 jobs：6 個")
print()

# 健康分數
health_score = 10 - (error_count * 1) - (warn_count * 0.5)
print(f"健康分數：{health_score}/10")
if health_score >= 8:
    print("狀態：🟢 健康")
elif health_score >= 5:
    print("狀態：🟡 一般")
else:
    print("狀態：🔴 需要修復")

print()
print("=" * 70)