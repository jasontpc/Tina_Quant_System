# ═══════════════════════════════════════
# 慢思考診斷：Gateway 啟動負載與系統穩定性
# ═══════════════════════════════════════
# 日期：2026-05-08
# 主題：Gateway 今日重啟 39 次的根本原因
# ═══════════════════════════════════════

## 一、事實陳列（無詮釋）

### 1. Gateway 重啟數據
今日共重啟 **39 次**，其中：
- 07:00-08:59：1 次（正常開機）
- 09:00-10:59：4 次（工作時段）
- 19:00-19:59：5 次（風控調整期）
- 21:00-21:59：2 次
- 22:00-22:59：3 次
- 23:00-23:59：**18 次**（Watchdog 崩潰循環）

### 2. Cron jobs 數量變化
- 07:50（開機）：82 jobs
- 09:21（第一次異常重啟）：86 jobs
- 19:00（大量更新後）：48→49 jobs
- 23:44（穩定後）：54 jobs

### 3. 單次啟動時序（正常情況）
```
T+0.0s  starting...
T+2.0s  starting HTTP server (3 plugins loaded)
T+3.6s  http server listening
T+4.7s  starting channels and sidecars
T+5.1s  gateway ready
T+6.5s  cron: started (jobs loaded)
T+6.8s  Telegram providers start
```
正常啟動耗時：5-7 秒 ✅

### 4. 健康狀態時的 EL 表現
- 工作日早晨（07:50）：EL 正常，無警告
- 午後（14:xx）：EL 開始波動，開始有 warnings
- 晚間（21:00+）：EL 峰值 14,000ms++，出現嚴重阻塞

### 5. OpenClaw 內建監控
- health-monitor：每 600 秒檢查一次
- liveness warning threshold：EL Delay 超過門檻（細節未完全掌握）
- restart policy：由 OpenClaw 自行決定

---

## 二、根本原因分析（三層）

### 第一層：架構層面的雙重保護冲突

```
┌─────────────────────────────────────────────────────┐
│  Python Watchdog          OpenClaw 內建 Health     │
│  ───────────────           ──────────────────────   │
│  Check interval: 30s       Check interval: 600s    │
│  Socket timeout: 5s         EL threshold: 不明       │
│  Cooldown: 60s              Auto-restart: 是        │
│  Action: kill+schtasks      Action: kill+restart    │
└─────────────────────────────────────────────────────┘
```

Python watchdog 每 30 秒檢查一次。如果它在 Gateway 啟動過程中（還在解析 jobs.json 時）做檢查，socket 連接會超時，Python watchdog 就會立即重啟 Gateway。

**問題：Python watchdog 不知道 Gateway 正在啟動，它只看到「port 18789 無回應」= 死了。**

### 第二層：Cron Jobs 加載的 Event Loop 壓力

Gateway 啟動時，cron 模塊需要：
1. 讀取 `jobs.json`（磁盤 I/O）
2. 解析所有 job 定義（JSON parsing，54-86 個 jobs）
3. 計算每個 job 的 nextWakeAtMs（時間計算）
4. 將所有 jobs 註冊到 scheduler（記憶體操作）

這一切都在 Node.js 的 main thread 進行。如果 event loop 當時剛好在處理其他事情（例如：同時有多個 agent session 在處理），就會造成 5-10 秒的延遲。

**但真正的問題不是啟動負載，而是：當 EL 忙碌時，watchdog 的檢查會失敗。**

### 第三層：系統承載能力 vs 工作負載的交錯

```
工作日早晨（07:50）：
  工作負載：低（只有 Telegram 連線）
  EL 狀態：大部分空閒
  結果：✅ 正常啟動

午後（14:00-18:00）：
  工作負載：中等（多個 agent sessions + jobs 在跑）
  EL 狀態：繁忙
  結果：⚠️ EL 警告，但還撐得住

晚間（21:00+）：
  工作負載：突然飆升（Leo v6.5 大量 jobs 啟動）
  EL 狀態：嚴重阻塞（14,000ms）
  結果：🔴 watchdog 誤判，開始重啟循環
```

---

## 三、為何 23:00-23:45 特別嚴重？

### 直接觸發點：風控檢查（30分→2小時）和自主決策（1小時→3小時）的 cron update 指令

當我執行 `cron update` 指令時，Gateway 需要：
1. 讀取 jobs.json
2. 找到目標 job
3. 修改 schedule 欄位
4. 寫回 jobs.json
5. 通知 cron 模塊重新加載

這個過程本身就會造成 event loop 短暫阻塞（100-500ms）。

### 為何演變成 18 次重啟？

1. **第一次變更**（風控 30分→2小時）：觸發 cron reload
2. **EL 忙碌**：還有其他 jobs 在同時運行
3. **Watchdog 30秒檢查**：發現 socket timeout，重啟
4. **新 Gateway 啟動**：又要 load jobs.json，又要計算 schedule
5. **此時系統更忙**：因為剛才的變更可能觸發了其他 jobs 的重新排程
6. **Watchdog 又發現 timeout**：再重啟
7. **迴圈**：不斷重複，次數越來越密集（20秒→10秒→5秒）

---

## 四、改善方案（分層實施）

### 第一優先：移除 Python Watchdog（5 分鐘，立即見效）

**理由：**
1. OpenClaw 已有內建 health-monitor（每 600 秒）
2. Python watchdog 的 30 秒檢查頻率與 OpenClaw 內建保護冲突
3. 30 秒太短，無法區分「忙碌中」和「真的死了」

**操作：**
- 停用 gateway_watchdog.py 的 cron job
- 停止任何正在運行的 watchdog 進程
- 觀察 24 小時，看 OpenClaw 內建保護是否足夠

**風險：**
- 如果 Gateway真的崩潰，需要等 OpenClaw 內建保護（600 秒）才會重啟
- 對於生產環境，這可能是可接受的延遲

### 第二優先：減少 Cron Jobs（30 分鐘，根本解決）

**目標：從 54 個 jobs 減少到 20 個核心 jobs**

根據 `job_registry.py` 和 `full_system_mapper.py`，建議保留：

**Macro（2 個）**
1. 晨間 Macro 快報 07:30
2. 盤後 Macro 報告 14:00

**交易策略（6 個）**
3. SP500 價值掃描（週一）
4. SP500 成長掃描（週一）
5. NDX 科技掃描（週二）
6. SOX 半導體掃描（週三）
7. TW500 價值掃描（週日）
8. TW500 成長掃描（週日）

**ETF（3 個）**
9. US ETF 高股息（週一）
10. US ETF 成長（週二）
11. TW ETF 高股息（週五）

**記憶系統（3 個）**
12. 每日輕度蒸餾 20:00
13. 每週中度蒸餾 週五 18:00
14. 每月深度蒸餾（月底週日 22:00）

**系統監控（4 個）**
15. Cron Governor 每 20 分鐘
16. 深夜智能喚醒 02:00
17. 深夜智能喚醒 03:00
18. MEMORY 每日同步（合併 AM+PM）

**風控/決策（2 個）**
19. 風控檢查（每 2 小時）
20. 自主決策（每 3 小時）

**建議移除/停用的 jobs：**
- 兩套心跳監控 → 合併為 OpenClaw 內建監控
- AM+PM 記憶同步 → 合併為 1 個 job
- 所有 "Tina ..." 前綴的測試 jobs
- 所有重複功能的 jobs（例如：同時有「心跳」和「健康監控」）

### 第三優先：Job Stagger（15 分鐘，減少峰值）

**原理：** 所有 cron jobs 都在同一個時間點計算 nextWakeAtMs，造成瞬間峰值。

**操作：** 在 cron job 建立時，自動為每個 job 加上 `staggerMs: random(0, 300000)`（最多隨機分散 5 分鐘）

這不是刪除 jobs，而是讓它們不要同時啟動。

### 第四優先：增加 Watchdog 的啟動檢測延遲（30 分鐘，深層改善）

如果必須保留 Python watchdog（Jo 特別要求），修改策略：

```python
# 當前（錯誤）：
CHECK_INTERVAL = 30      # 太短
COOLDOWN_SEC = 60        # 太短
SOCKET_TIMEOUT = 5      # 太短

# 改善後：
CHECK_INTERVAL = 120     # 2 分鐘，減少干擾
COOLDOWN_SEC = 300      # 5 分鐘，防止迴圈
SOCKET_TIMEOUT = 15      # 15 秒，允許啟動完成
STARTUP_GRACE = 60       # 啟動後 60 秒內不檢查
```

---

## 五、慢思考的核心洞察

### 洞察 1：系統存在「雙重標準」

```
OpenClaw 內建監控：600 秒，嚴謹的 health check
Python watchdog：30 秒，快速的 socket check
```

兩者同時運行，Python watchdog 會在 OpenClaw 之前發現「問題」並行動。但「問題」可能是：
- Gateway 在啟動中（還沒監聽 port）
- Gateway 在忙碌（EL 忙碌導致回應慢）
- Gateway 在重啟中（kill 後到 schtasks 生效前的空檔）

### 洞察 2：Gateway 啟動本身不是問題，EL 忙碌才是

從時序可見，Gateway 能在 5-7 秒內正常啟動。真正的問題是：
- 啟動時剛好有其他工作在進行（EL 忙碌）
- 啟動後馬上有大量 cron jobs 進入 scheduler
- 這些因素讓 socket check 在關鍵時刻失敗

### 洞察 3：39 次重啟大部分是「不必要的重啟」

如果沒有 Python watchdog，只有 OpenClaw 內建保護，預計重啟次數：
- 正常的每日重啟：1 次（開機）
- 真正的崩潰重啟：1-2 次（如果有的話）
- 總計：2-3 次/天

39 次重啟中，36+ 次是因為 watchdog 誤判造成的。

---

## 六、決策矩陣

| 方案 | 立即性 | 效果 | 風險 | 建議 |
|:-----|:------:|:-----|:-----|:-----|
| 移除 Python Watchdog | ✅ 立即 | 高 | 低（OpenClaw 內建保護）| **強烈建議** |
| 減少 Jobs 到 20 個 | 需要 30 分鐘 | 高 | 中（需要重新配置）| **建議** |
| Job Stagger | 15 分鐘 | 中 | 低 | 可選 |
| Watchdog 參數調整 | 30 分鐘 | 中 | 低（如果保留wd）| 次選 |

---

*慢思考完成時間：2026-05-08 23:55*