# -*- coding: utf-8 -*-
"""
Tina Brain - 決策資料庫 v1.0
============================
建立結構化決策資料庫，記錄所有分析決策、推理過程、執行結果
讓 Tina 能從過去決策中學習，避免重蹈覆轍
"""
import sqlite3, json, sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
DB = DATA / "tina_decisions.db"


def init_db():
    """初始化決策資料庫"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        category TEXT NOT NULL,
        symbol TEXT,
        action TEXT NOT NULL,
        decision_text TEXT NOT NULL,
        reasoning TEXT NOT NULL,
        evidence TEXT,
        constraints TEXT,
        outcome TEXT,
        pnl_pct REAL,
        score INTEGER,
        tags TEXT,
        source TEXT DEFAULT 'manual'
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS learnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        category TEXT NOT NULL,
        lesson TEXT NOT NULL,
        evidence TEXT,
        decision_id INTEGER,
        times_applied INTEGER DEFAULT 0,
        last_applied TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS strategy_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        team TEXT NOT NULL,
        strategy_name TEXT NOT NULL,
        params TEXT,
        win_rate REAL,
        total_trades INTEGER,
        avg_gain REAL,
        avg_loss REAL,
        pf REAL,
        sharpe_ratio REAL,
        max_drawdown REAL
    )""")

    conn.commit()
    conn.close()


def think(situation: str, conflict: str, plan: str,
          evidence: str = "", constraints: str = "") -> str:
    """Chain-of-Thought 慢思考機制"""
    chain = f"""【Chain-of-Thought 推理鏈】
1. 情境建模：{situation}
2. 衝突檢測：{conflict}
3. 邏輯推演：{plan}"""
    if evidence:
        chain += f"\n4. 支撐證據：{evidence}"
    if constraints:
        chain += f"\n5. 約束條件：{constraints}"
    return chain


def decide(category: str, symbol: str, action: str,
           decision_text: str, reasoning: str,
           evidence: str = "", constraints: str = "",
           tags: List[str] = None,
           source: str = "manual") -> int:
    """寫入決策記錄"""
    if tags is None:
        tags = []

    conn = sqlite3.connect(str(DB))
    c = conn.cursor()

    c.execute("""INSERT INTO decisions
        (ts, category, symbol, action, decision_text, reasoning, evidence, constraints, tags, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
         category, symbol, action, decision_text, reasoning,
         evidence, constraints, ','.join(tags), source))

    decision_id = c.lastrowid
    conn.commit()
    conn.close()
    return decision_id


def update_outcome(decision_id: int, outcome: str, pnl_pct: float, score: int):
    """更新決策結果"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    c.execute("UPDATE decisions SET outcome=?, pnl_pct=?, score=? WHERE id=?",
              (outcome, pnl_pct, score, decision_id))
    conn.commit()
    conn.close()


def record_learning(category: str, lesson: str, evidence: str = "", decision_id: int = None):
    """記錄學習教訓"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    c.execute("""INSERT INTO learnings (ts, category, lesson, evidence, decision_id)
        VALUES (?, ?, ?, ?, ?)""",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), category, lesson, evidence, decision_id))
    conn.commit()
    conn.close()


def query_decisions(symbol: str = None, category: str = None,
                    action: str = None, limit: int = 20) -> List[tuple]:
    """查詢歷史決策"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()

    q = "WHERE 1=1"
    args = []
    if symbol:   q += " AND symbol=?";   args.append(symbol)
    if category: q += " AND category=?"; args.append(category)
    if action:   q += " AND action=?";   args.append(action)

    c.execute(f"""SELECT id, ts, category, symbol, action, decision_text, outcome, pnl_pct, score, tags
        FROM decisions {q} ORDER BY ts DESC LIMIT ?""", (*args, limit))

    rows = c.fetchall()
    conn.close()
    return rows


def print_database_summary():
    """列印資料庫摘要"""
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM decisions")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM decisions WHERE outcome IN ('win','loss')")
    resolved = c.fetchone()[0]

    c.execute("SELECT AVG(score) FROM decisions WHERE score IS NOT NULL")
    avg_score = c.fetchone()[0] or 0

    c.execute("SELECT category, COUNT(*) FROM decisions GROUP BY category")
    by_cat = c.fetchall()

    c.execute("SELECT action, COUNT(*) FROM decisions GROUP BY action")
    by_action = c.fetchall()

    c.execute("SELECT COUNT(*) FROM learnings")
    total_learnings = c.fetchone()[0]

    conn.close()

    res_pct = round(resolved/total*100, 1) if total > 0 else 0
    print(f"""
============================================================
  Tina Brain - 決策資料庫摘要
  {datetime.now().strftime('%Y-%m-%d %H:%M')}
============================================================
  總決策數：{total}
  已結案：  {resolved} ({res_pct}%)
  平均品質：{round(avg_score, 1)}/10

  【決策類別】""")
    for cat, cnt in by_cat:
        print(f"    {cat:<15} {cnt}")
    print(f"""
  【動作類別】""")
    for act, cnt in by_action:
        print(f"    {act:<15} {cnt}")
    print(f"""
  【學習記錄】{total_learnings} 條
============================================================""")


def seed_sample_decisions():
    """寫入示範決策"""
    samples = [
        {
            'category': 'entry', 'symbol': '2359.TW', 'action': 'watch',
            'decision_text': 'RSI 56.9 + MACD +0.76 + 量能 3.9x → 觀望等回調',
            'reasoning': think('RSI 56.9（觀望區），MACD多頭(+0.76)，量能放大3.9x',
                'RSI在觀望區不建議追高，但量能強勢',
                '等RSI回調至50以下，目標價$110-$115，MA20支撐進場',
                'MACD>0多頭確認，5日動能+8.7%，ATR $6(5.1%)',
                '單筆最大虧損-8%，停損$108'),
            'evidence': 'SMA20 $114 < $119現價, ATR $6, 52w區間$105-$176',
            'constraints': '不入原因：RSI 56.9在觀望區，量能3.9x追高風險大',
            'tags': ['rsi','macd','volume'],
            'outcome': 'pending', 'pnl_pct': 0, 'score': 8,
        },
        {
            'category': 'strategy', 'symbol': None, 'action': 'optimize',
            'decision_text': 'LEO 進場條件優化：RSI 25-40 + 量能>1.5x → 勝率83.3%',
            'reasoning': think('LEO 勝率19.7%，交易66筆，策略失效',
                'RSI<35過嚴，市場多頭導致很少觸發',
                '擴大RSI範圍25-40，加入量能過濾確認動能',
                'tested RSI 25-40 + vol>1.5x: 83.3% WR (6 trades)',
                '需保持min_trades>=5確保統計顯著'),
            'evidence': 'optimize_entry_conditions.py 測試結果',
            'constraints': '需保持min_trades>=5',
            'tags': ['rsi','volume','optimize'],
            'outcome': 'win', 'pnl_pct': 0, 'score': 9,
        },
        {
            'category': 'strategy', 'symbol': None, 'action': 'optimize',
            'decision_text': 'NANA 進場條件優化：RSI 35-50 + MA20>MA60 → 勝率71.4%',
            'reasoning': think('NANA 無法觸發（RSI<35太嚴格）',
                '市場多頭環境，RSI很少低於35',
                '放寬RSI至35-50，加入MA多頭排列確認趨勢',
                'tested RSI 35-50 + ma20_above_ma60: 71.4% WR (7 trades)',
                'MA60計算需要60日數據'),
            'evidence': 'optimize_entry_conditions.py 測試結果',
            'constraints': 'MA60需要60日數據',
            'tags': ['rsi','ma','optimize'],
            'outcome': 'win', 'pnl_pct': 0, 'score': 9,
        },
        {
            'category': 'stock', 'symbol': '2359.TW', 'action': 'analyze',
            'decision_text': '所羅門(2359)：現價$119，RSI 56.9，量能3.9x，MACD+0.76',
            'reasoning': think('52週區間$105-$176，處於20%位置，量能今日放大',
                '價格接近52週高點，RSI 56.9不低',
                '動能正面但估值偏高，等待回調',
                'SMA20($114)<現價($119)，MACD+0.76多頭，ATR $6(5.1%)',
                '不入原因：RSI 56.9在觀望區，量能3.9x追高風險大'),
            'evidence': 'MACD>0, SMA20 $114, ATR $6',
            'constraints': '單筆最大虧損-8%',
            'tags': ['rsi','macd','sma','volume','analyze'],
            'outcome': 'pending', 'pnl_pct': 0, 'score': 7,
        },
    ]

    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    for d in samples:
        c.execute("""INSERT INTO decisions
            (ts, category, symbol, action, decision_text, reasoning, evidence, constraints, tags, source, outcome, pnl_pct, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'seed', ?, ?, ?)""",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), d['category'], d['symbol'],
             d['action'], d['decision_text'], d['reasoning'],
             d.get('evidence',''), d.get('constraints',''),
             ','.join(d['tags']), d['outcome'], d['pnl_pct'], d['score']))
    conn.commit()
    conn.close()


def main():
    init_db()
    print_database_summary()
    seed_sample_decisions()

    print()
    print("【最新決策鏈範例】")
    print("="*60)

    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    c.execute("""SELECT id, ts, category, symbol, action, decision_text, reasoning, score
        FROM decisions WHERE category='entry' ORDER BY ts DESC LIMIT 1""")
    row = c.fetchone()
    conn.close()

    if row:
        print(f"#{row[0]} ({row[1]}) | {row[2]}: {row[3]} [{row[4]}]")
        print()
        print(row[6])
        print(f"  → Score: {row[7]}/10")


if __name__ == '__main__':
    main()