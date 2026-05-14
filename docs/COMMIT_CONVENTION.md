# Tina Quant System - Git 提交規範

## 為什麼要規範化？

- 快速定位每次變更的性質
- Debugger 能快速找出 feat/fix 記錄
- Backtester 能快速找到 bt: 回測 commit

---

## 提交格式

```
<前綴>: <簡短描述>

[可選: 詳細說明]
```

---

## 前綴參考

| 前綴 | 類別 | 範例 |
|:-----|:-----|:-----|
| `feat:` | 新功能 | `feat: add VIF filter to v3.13` |
| `fix:` | Bug修復 | `fix: handle API timeout in twse_api` |
| `bt:` | 回測紀錄 | `bt: 2025 full year stress test` |
| `docs:` | 文件更新 | `docs: update WORK_INDEX.md` |
| `refactor:` | 重構 | `refactor: extract filters to module` |
| `perf:` | 效能優化 | `perf: optimize backtest speed` |
| `sre:` | 運維變更 | `sre: add daily backup cron` |
| `chore:` | 瑣事更新 | `chore: clean up old scripts` |

---

## 實際範例

```
# 新功能
feat: add RegimeFilter to v3.13 filters

# 修復錯誤
fix: resolve JSON decode error in watchlist.json

# 回測結果
bt: v3.12 full year - 67.8% WR, +3.22% avg

# 文件
docs: update WORK_INDEX with new task list
```

---

## 提交前檢查清單

- [ ] 代碼有測試過嗎？
- [ ] 文件有更新嗎？
- [ ] 已經 pull 最新版本了嗎？

---

## SRE 每日任務

每日 23:00 自動執行:
```bash
git add .
git commit -m "sre: daily backup - $(date +%Y%m%d)"
git push origin main
```
