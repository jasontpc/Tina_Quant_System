"""
Macro Weekly Report Generator
產出每週資金流向總結
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = "./data/macro_institutional.db"
REPORT_DIR = "./reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def get_connection():
    return sqlite3.connect(DB_PATH)

def format_billion(val):
    return f"{round(val/1e9, 2)}億"

def get_weekly_data(week_end_str):
    """取得最近一週的法人資料"""
    end = datetime.strptime(week_end_str, "%Y-%m-%d")
    start = end - timedelta(days=6)
    
    conn = get_connection()
    cur = conn.cursor()
    
    daily = []
    for i in range(7):
        d = start + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        
        cur.execute("""
            SELECT 
                COALESCE(SUM(foreign_net), 0),
                COALESCE(SUM(trust_net), 0),
                COALESCE(SUM(dealer_net), 0),
                COALESCE(SUM(total_net), 0)
            FROM institutional_daily WHERE date = ?
        """, (d_str,))
        
        row = cur.fetchone()
        daily.append({
            "date": d_str,
            "foreign": row[0] or 0,
            "trust": row[1] or 0,
            "dealer": row[2] or 0,
            "total": row[3] or 0
        })
    
    # 本週總計
    total_foreign = sum(d["foreign"] for d in daily)
    total_trust = sum(d["trust"] for d in daily)
    total_dealer = sum(d["dealer"] for d in daily)
    total_total = sum(d["total"] for d in daily)
    
    # 上週對比
    prev_start = start - timedelta(days=7)
    prev_end = end - timedelta(days=7)
    
    prev_total = 0
    for i in range(7):
        d = prev_start + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        cur.execute("SELECT COALESCE(SUM(total_net), 0) FROM institutional_daily WHERE date = ?", (d_str,))
        prev_total += cur.fetchone()[0]
    
    # 產業流向
    cur.execute("""
        SELECT sector, SUM(total_net) as net
        FROM sector_flow
        WHERE date BETWEEN ? AND ?
        GROUP BY sector
        ORDER BY net DESC
        LIMIT 10
    """, (start.strftime("%Y-%m-%d"), week_end_str))
    sectors = cur.fetchall()
    
    # 宏觀指標（取最後一天）
    macro = {}
    for ind in ["VIX", "DXY", "US10Y", "US2Y"]:
        cur.execute("""
            SELECT value FROM macro_indicators
            WHERE indicator = ? ORDER BY date DESC LIMIT 1
        """, (ind,))
        row = cur.fetchone()
        macro[ind] = row[0] if row else None
    
    conn.close()
    
    return {
        "week_start": start.strftime("%Y-%m-%d"),
        "week_end": week_end_str,
        "daily": daily,
        "totals": {
            "foreign": total_foreign,
            "trust": total_trust,
            "dealer": total_dealer,
            "total": total_total
        },
        "prev_week_total": prev_total,
        "sectors": sectors,
        "macro": macro
    }

def generate_weekly_report(week_end_str):
    """產出每週回報"""
    data = get_weekly_data(week_end_str)
    
    if data["totals"]["total"] == 0:
        return None, None
    
    # 週變化
    change = data["totals"]["total"] - data["prev_week_total"]
    change_pct = (change / abs(data["prev_week_total"]) * 100) if data["prev_week_total"] != 0 else 0
    
    lines = [
        f"📊 宏觀法人每週回報 {data['week_start']} ~ {data['week_end']}",
        "",
        "【本週三大法人合計】",
        f"• 外資：{format_billion(data['totals']['foreign'])}",
        f"• 投信：{format_billion(data['totals']['trust'])}",
        f"• 自營：{format_billion(data['totals']['dealer'])}",
        f"• 週合計：{format_billion(data['totals']['total'])}",
        f"• 較上週：{'+' if change >= 0 else ''}{format_billion(change)} ({'+' if change_pct >= 0 else ''}{change_pct:.1f}%)",
        "",
        "【每日明細】",
    ]
    
    for d in data["daily"]:
        if d["total"] != 0:
            sign = "+" if d["total"] >= 0 else ""
            lines.append(f"• {d['date']}：{sign}{format_billion(d['total'])} (外:{sign if d['foreign']>=0 else ''}{round(d['foreign']/1e9,1)}億)")
    
    lines.extend([
        "",
        "【產業資金流向】",
    ])
    
    for sec, net in data["sectors"]:
        sign = "+" if net >= 0 else ""
        lines.append(f"• {sec}：{sign}{format_billion(net)}")
    
    vix_val = data["macro"].get("VIX")
    yield_10y = data["macro"].get("US10Y")
    yield_2y = data["macro"].get("US2Y")
    
    lines.extend([
        "",
        "【宏觀指標】",
        f"• VIX：{vix_val:.2f}" if vix_val else "• VIX：N/A",
        f"• 10Y殖利率：{yield_10y:.3f}%" if yield_10y else "• 10Y殖利率：N/A",
        f"• 2Y殖利率：{yield_2y:.3f}%" if yield_2y else "• 2Y殖利率：N/A",
    ])
    
    # 結論
    total = data["totals"]["total"]
    vix_sentiment = "恐懼" if vix_val and vix_val > 25 else ("中性" if vix_val and vix_val > 18 else "貪婪") if vix_val else ""
    
    lines.extend([
        "",
        "【本週結論】",
        f"• 法人本週{'淨買超' if total >= 0 else '淨賣超'}格局",
        f"• VIX {vix_sentiment} ({vix_val:.2f})" if vix_val else "",
    ])
    
    if total > 20_000_000_000:
        lines.append("• 趨勢：偏多，持續關注美股連動")
    elif total < -20_000_000_000:
        lines.append("• 趨勢：偏空，謹慎操作")
    else:
        lines.append("• 趨勢：整理，等待突破方向")
    
    report = "\n".join(lines)
    
    report_file = f"{REPORT_DIR}/macro_weekly_report_{week_end_str}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    return report, report_file

if __name__ == "__main__":
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    report, path = generate_weekly_report(date_arg)
    if path:
        print(f"Report saved: {path}")
        print("---")
        print(report)
    else:
        print("No data available for this week")
