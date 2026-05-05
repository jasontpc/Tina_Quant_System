"""
Tina Strategy Meeting - 策略面談系統
觸發條件：連續三次交易虧損
產出面談報告，等待 Jo 回覆
"""

import sqlite3
import json
import os
from datetime import datetime


REASONS = {
    '1': '市場盤整，RSI 鈍化失效',
    '2': '法人換手，趨勢逆轉',
    '3': '參數過度擬合，需要重新校準',
    '4': '產業輪動，策略不適用',
    '5': '其他（請說明）',
}


class StrategyMeeting:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.base_dir = base_dir
        self.data_dir = os.path.join(base_dir, 'data')
        self.reports_dir = os.path.join(base_dir, 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)

        self.learning_db = os.path.join(self.data_dir, 'tina_learning.db')
        self.trade_history_db = os.path.join(self.data_dir, 'tina_trade_history.db')
        self.check_time = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ──── 取得連續虧損交易 ────
    def get_recent_losses(self, count=3):
        conn = sqlite3.connect(self.learning_db)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT stock, entry_date, exit_date, pnl_pct, hold_days,
                       entry_rsi, exit_rsi, strategy_used, lesson_learned, tags
                FROM trades
                WHERE pnl_pct IS NOT NULL
                ORDER BY exit_date DESC LIMIT ?
            """, (count * 2,))  # 取更多筆以便過濾
        except Exception as e:
            conn.close()
            return []
        rows = cur.fetchall()
        conn.close()

        losses = []
        for r in rows:
            try:
                pnl = float(r[3]) if r[3] else None
                if pnl is not None and pnl < 0:
                    losses.append({
                        'stock': r[0], 'entry_date': r[1], 'exit_date': r[2],
                        'pnl_pct': pnl, 'hold_days': r[4],
                        'entry_rsi': r[5], 'exit_rsi': r[6],
                        'strategy': r[7], 'lesson': r[8], 'tags': r[9]
                    })
                    if len(losses) >= count:
                        break
            except (ValueError, TypeError):
                pass
        return losses

    # ──── 產出面談報告 ────
    def generate_meeting_report(self, losses):
        date_str = datetime.now().strftime('%Y%m%d_%H%M')
        report_path = os.path.join(
            self.reports_dir,
            f"tina_meeting_request_{date_str}.md"
        )

        # 計算平均虧損
        avg_loss = sum(l['pnl_pct'] for l in losses) / len(losses)
        max_loss = min(l['pnl_pct'] for l in losses)
        total_loss = sum(l['pnl_pct'] for l in losses)

        md = f"""# Tina 策略面談要求 ⚠️

**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  
**分析師**: Tina 🎯  
**緊急程度**: 🔴 HIGH

---

## 🚨 觸發原因

系統連續 **{len(losses)} 筆交易虧損**，需要檢討策略有效性。

| 項目 | 數值 |
|------|------|
| 虧損筆數 | {len(losses)} |
| 平均虧損 | {avg_loss:+.2f}% |
| 最大單筆虧損 | {max_loss:+.2f}% |
| 累計虧損 | {total_loss:+.2f}% |

---

## 📋 虧損交易明細

"""

        for i, l in enumerate(losses, 1):
            md += f"""### {i}. {l['stock']} — {l['pnl_pct']:+.2f}%

| 項目 | 內容 |
|------|------|
| 進場日 | {l['entry_date'] or 'N/A'} |
| 出場日 | {l['exit_date'] or 'N/A'} |
| 進場 RSI | {l['entry_rsi'] or 'N/A'} |
| 出場 RSI | {l['exit_rsi'] or 'N/A'} |
| 持有天數 | {l['hold_days'] or 'N/A'} 天 |
| 策略 | {l['strategy'] or 'N/A'} |
| 教訓 | {l['lesson'] or '無記錄'} |

"""

        md += f"""---

## 🤔 可能失效原因（請 Jo 選擇）

**請回覆數字（1-5）告訴我主要原因，我會調整策略。**

"""

        for k, v in REASONS.items():
            md += f"{k}. {v}\n"

        md += f"""

---

## 💡 建議調整（預設方案）

1. **下調 RSI 進場區間** — 提高進場精準度（40-45 → 35-40）
2. **增加 MA 確認條件** — 過濾假突破（MA20 趨勢向上才進場）
3. **縮短最大持有天數** — 降低風險暴露（20天 → 12天）
4. **提高 ATR 止損敏感度** — 1.5x → 1.0x ATR
5. **暫停新倉** — 等待市場盤整結束

---

## 📈 數據佐證

"""
        # 加入 RSI 統計（如果可取得的話）
        rsi_vals = [l['entry_rsi'] for l in losses if l.get('entry_rsi')]
        if rsi_vals:
            avg_rsi = sum(float(r) for r in rsi_vals) / len(rsi_vals)
            md += f"- 平均進場 RSI：{avg_rsi:.1f}（理想區間 35-45）\n"
            md += f"- 進場 RSI {'偏高' if avg_rsi > 45 else '正常' if avg_rsi > 35 else '過低'}\n"

        md += f"""
---

## 📬 請求回覆

Jo，請回覆數字（1-5）告訴我主要原因：

> 1 = 市場盤整，RSI 鈍化失效  
> 2 = 法人換手，趨勢逆轉  
> 3 = 參數過度擬合，需要重新校準  
> 4 = 產業輪動，策略不適用  
> 5 = 其他（請說明）

Tina 會根據您的回覆，自動調整策略參數並產出新的版本。

---

*此報告由 Tina 量化系統 v3.12 自動產生*
*Tina 🎯*
"""

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"[StrategyMeeting] 面談報告已儲存：{report_path}")
        return report_path

    # ──── 格式化 Telegram 訊息 ────
    def format_telegram_message(self, losses):
        avg_loss = sum(l['pnl_pct'] for l in losses) / len(losses)
        lines = [
            "🔴 *Tina 策略面談要求*",
            "",
            f"系統連續 **{len(losses)} 筆虧損**（平均 {avg_loss:+.2f}%）",
            "",
            "*可能原因（請回覆數字 1-5）：*",
            "1️⃣ 市場盤整，RSI 鈍化失效",
            "2️⃣ 法人換手，趨勢逆轉",
            "3️⃣ 參數過度擬合，需重新校準",
            "4️⃣ 產業輪動，策略不適用",
            "5️⃣ 其他（請說明）",
            "",
            f"📋 面談報告：tina_meeting_request_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        ]
        return "\n".join(lines)

    # ──── 主流程 ────
    def run(self):
        losses = self.get_recent_losses(count=3)
        if len(losses) < 3:
            print(f"[StrategyMeeting] 連續虧損不足 3 筆（僅 {len(losses)} 筆），不觸發面談")
            return None

        report_path = self.generate_meeting_report(losses)
        return {
            'losses': losses,
            'report_path': report_path,
            'telegram_msg': self.format_telegram_message(losses),
        }


if __name__ == '__main__':
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meeting = StrategyMeeting(base_dir=base)
    result = meeting.run()
    if result:
        print("\n" + result['telegram_msg'])