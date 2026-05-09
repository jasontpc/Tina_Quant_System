
## 2026-05-09 系統整頓決策

### 目標
全團隊腳本索引與整合，消除重複、提升效率、降低系統負載

### 考量因素
1. 430+ 腳本中大量重疊（nana 8 版本、leo 45 個、backtest 25 個）
2. Gateway 08:00 峰値 14 個 jobs 同時競爭
3. FinMind 600/hr rate limit 無 cache
4. 17 個 jobs agentId=? 導致 main 超載

### 選項
- A: 只做排程分散（快速但表面）
- B: 只刪廢腳本（安全但不徹底）
- C: 全部執行（徹底但需要驗證）

### 決策
執行 A+C+D+E（排程+清理+Archive+Macro調整），共 7 項改造

### 執行結果
- P0: INST_CACHE 30min
- P1: 刪除 15 個廢腳本
- P2: sync_margin_data.py 建立
- P3: Archive 91 個腳本
- A: 08:00 jobs 14→4
- C: Universe 掃描→02:00
- D: 15 agentId=?→tina-reports

### 代價
- Archive 後需要時間驗證核心腳本完整性
- 部分舊版本可能仍被少量 jobs 引用

### 結果
✅ Gateway 啟動負載降低
✅ FinMind rate limit 問題緩解
✅ 腳本數從 430+ 降至 ~330
✅ 主系統更清晰易維護
