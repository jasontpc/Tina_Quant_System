# -*- coding: utf-8 -*-
"""
Tina Brain - 團隊 cron 調度分配器 v2
====================================
每個團隊分配：
  A. 每日 DB 更新（收盤後）
  B. 每週學習（自主研究）
  C. 每日快報（輸出）
  D. 每週檢討（成效）

Jo 指令：每個團隊都要更新自己的 DB，學習並產生獲利。
"""
import sys
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")

# ===== 團隊 cron 分配表 =====
# fmt: (team, cron_id_or_NEW, schedule, script, description)
TEAM_CRON_ASSIGNMENTS = [
    # === NANA 波段（個股）===
    ("NANA", "faf759b4-4ee6-40ff-8152-2c552be19816", "0 8,10,13,15,17 * * 1-5",  # 已存在
     "nana_v68.py", "Nana 波段v6.4（盤中即時）"),
    ("NANA", "NEW", "0 16 * * 1-5",
     "nana_db_update.py", "Nana 每日DB收盤更新（yfinance + limitup）"),
    ("NANA", "NEW", "0 10 * * 1",  # 週一
     "nana_backtest.py", "Nana 每週一回測（優化參數）"),
    ("NANA", "NEW", "0 17 * * 5",  # 週五
     "nana_weekly_review.py", "Nana 每週五檢討（學習成效）"),

    # === RAY DCA（ETF）===
    ("RAY", "f051f79e-dc9e-4d9e-9235-fde5987643d9", "0 16 * * 1-5",  # 已存在
     "ray_dca_brief.py", "Ray DCA 市場快報"),
    ("RAY", "NEW", "0 17 * * 1",  # 週一
     "ray_etf_learning.py", "Ray 每週學習（ETF 價值分析）"),

    # === LEO 科技股波段 ===
    ("LEO", "6263e6d0-1ca4-4f26-ae7c-626943fa0747", "0 8,11,14,17,21 * * 1-5",  # 已存在
     "leo_analysis.py", "Leo v6.5 科技股波段分析"),
    ("LEO", "NEW", "0 16 * * 1-5",
     "leo_db_update.py", "Leo 每日DB收盤更新"),
    ("LEO", "NEW", "0 3 * * 0",  # 週日深夜
     "leo_autonomous.py", "Leo 每週自主學習（法人流向+回測）"),

    # === MAGGY 美股AI選股 ===
    ("MAGGY", "86c248ce-ab92-490e-a4ce-d6ea6c44f584", "0 8 * * 1-5",  # 已存在
     "maggy_daily_check.py", "Maggy 美股每日檢查"),
    ("MAGGY", "NEW", "0 16 * * 1-5",
     "maggy_db_update.py", "Maggy 每日DB收盤更新（US stocks）"),
    ("MAGGY", "NEW", "0 3 * * 0",  # 週日深夜
     "maggy_ai_learning.py", "Maggy 每週自主學習（US AI Tech）"),

    # === SHERKY ETF DCA ===
    ("SHERKY", "885a72fa-644c-41e4-aba6-f11e50684306", "0 8 * * 1-5",  # 已存在
     "sherry_daily_check.py", "Sherry ETF DCA 每日檢查"),
    ("SHERKY", "NEW", "0 9 * * 0",  # 週日
     "sherry_autonomous.py", "Sherry 每週自主學習（ETF觀察名單）"),

    # === VOGEL 台指期 ===
    ("VOGEL", "NEW", "0 9 * * 0",  # 週日
     "vogel_autonomous.py", "Vogel 每週自主學習（BB/RSI/MACD）"),
    ("VOGEL", "NEW", "0 16 * * 1-5",
     "vogel_db_update.py", "Vogel 每日DB收盤更新（^TWII）"),
    ("VOGEL", "NEW", "0 20 * * 5",  # 週五
     "vogel_weekly_review.py", "Vogel 每週策略檢討"),

    # === Tina Brain 系統 ===
    ("TINA_BRAIN", "facc1550-ce47-4c5a-9a3c-04720d443b7b", "0 16 * * 1-5",  # 已存在
     "daily_db_update.py", "Tina 每日DB收盤更新"),
    ("TINA_BRAIN", "0c847110-5447-466b-acb0-b2a77d704b6b", "0 8 * * 1-5",  # 已存在
     "tina_daily_brief.py", "Tina 每日市場快報"),
    ("TINA_BRAIN", "4c863cbf-7606-4ebe-9d23-aaf4243e9e12", "0 9 * * 1-5",  # 已存在
     "tina_brain_scheduler.py", "Tina 大腦-團隊排程管理"),
    ("TINA_BRAIN", "NEW", "0 17 * * 5",  # 週五
     "tina_weekly_review.py", "Tina 每週回顧（全團隊整合）"),
    ("TINA_BRAIN", "NEW", "0 9 * * 0",  # 週日
     "tina_weekly_learning.py", "Tina 每週自主學習（擴充DB）"),
    ("TINA_BRAIN", "8cfc071c-c23a-4e32-a7b9-552cad8d31d0", "0 9 * * 0",  # 已存在
     "vogel_autonomous.py", "Vogel 自主學習"),
    ("TINA_BRAIN", "85b3eee5-99a6-44fe-9586-f51590bfd82c", "0 9 * * 0",  # 已存在
     "sherry_autonomous.py", "Sherry 自主學習"),
    ("TINA_BRAIN", "38fc8dba-b098-487b-83e7-ae20e7de372b", "0 7 * * 1-5",  # 已存在
     "reddit_sentiment.py", "Reddit 社群情緒更新"),
    ("TINA_BRAIN", "e361dc2e-cd2e-4194-a739-1711f0544902", "0 7 * * 1-5",  # 已存在
     "stocktwits_sentiment.py", "StockTwits 多空情緒更新"),
    ("TINA_BRAIN", "de4b8223-a376-46bd-bb36-97a2f7e8d29a", "30 7 * * 1-5",  # 已存在
     "social_sentiment.py", "Tavily 社群情緒更新"),
    ("TINA_BRAIN", "529d3c7c-ba5e-4979-afa0-1bf261088eb4", "0 16 * * 1-5",  # 已存在
     "twse_limitup.py", "漲停板每日掃描"),
    ("TINA_BRAIN", "d0ed774e-e2b2-43b1-a39c-070b5798f873", "0 * * * *",  # 已存在
     "gateway_quick_check.py", "Gateway 後台監控"),
    ("TINA_BRAIN", "1c5349f9-df2b-49b6-b64b-da722cc123d6", "0 8,16,22 * * *",  # 已存在
     "rsi_audit.py", "RSI 數值覆核"),
]

def print_dispatch():
    print("=" * 65)
    print("  Tina Brain - 團隊 cron 調度分配")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 65)
    print()

    # Group by team
    teams = {}
    for team, cid, sched, script, desc in TEAM_CRON_ASSIGNMENTS:
        if team not in teams:
            teams[team] = []
        teams[team].append((cid, sched, script, desc))

    for team, crons in sorted(teams.items()):
        print(f"[{team}] {'─' * (55 - len(team))}")
        for cid, sched, script, desc in crons:
            status = "✅" if cid != "NEW" else "🆕"
            print(f"  {status} {sched:22} {desc}")
        print()

    print("─" * 65)
    print("調度原則：")
    print("  每個團隊 A/B/C/D 四個學習階段：")
    print("  A. 每日 DB 更新（收盤 16:00）")
    print("  B. 每週自主學習（週日 09:00）")
    print("  C. 每日快報（盤前 08:00）")
    print("  D. 每週檢討（週五 17:00）")
    print()
    print("  Tina 大腦負責協調、監督、整合")
    print("=" * 65)


if __name__ == "__main__":
    print_dispatch()
