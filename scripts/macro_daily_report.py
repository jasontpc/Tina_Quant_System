"""
Macro Daily Report Generator
產出格式化的每日 Telegram 回報
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "./data/macro_institutional.db"
CONFIG_PATH = "./configs/macro_config.json"
CONFIG_ALERTS = "./configs/institutional_alerts.json"
REPORT_DIR = "./reports"
os.makedirs(REPORT_DIR, exist_ok=True)

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def load_alerts():
    with open(CONFIG_ALERTS) as f:
        return json.load(f)

def format_billion(val):
    """轉換為億單位，帶正負號"""
    b = round(val / 1_000_000_000, 2)
    return f"+{b}億" if b >= 0 else f"{b}億"

def get_vix_sentiment(vix):
    if vix is None: return "未知"
    if vix >= 25: return "恐慌"
    if vix >= 20: return "恐懼"
    if vix >= 15: return "中性"
    return "貪婪"

def get_institutional_summary(date_str):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            COALESCE(SUM(foreign_net), 0),
            COALESCE(SUM(trust_net), 0),
            COALESCE(SUM(dealer_net), 0),
            COALESCE(SUM(total_net), 0)
        FROM institutional_daily
        WHERE date = ?
    """, (date_str,))
    
    row = cur.fetchone()
    conn.close()
    return {"foreign": row[0] or 0, "trust": row[1] or 0, "dealer": row[2] or 0, "total": row[3] or 0}

def get_consecutive_days(date_str, field="foreign_net", direction="buy"):
    conn = get_connection()
    cur = conn.cursor()
    
    for i in range(30):
        d = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        
        cur.execute(f"SELECT COALESCE(SUM({field}), 0) FROM institutional_daily WHERE date = ?", (d_str,))
        net = cur.fetchone()[0]
        
        if (direction == "buy" and net > 0) or (direction == "sell" and net < 0):
            continue
        else:
            return i
    
    conn.close()
    return 30

def get_sector_flow(date_str):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT sector, SUM(total_net) as net
        FROM sector_flow
        WHERE date = ?
        GROUP BY sector
        ORDER BY net DESC
        LIMIT 6
    """, (date_str,))
    
    rows = cur.fetchall()
    conn.close()
    return rows

def get_margin_summary(date_str):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT SUM(margin_balance), SUM(margin_balance_value)
        FROM margin_balance WHERE date = ?
    """, (date_str,))
    
    row = cur.fetchone()
    conn.close()
    return {"balance": row[0] or 0, "value": row[1] or 0}

def get_macro_indicators():
    conn = get_connection()
    cur = conn.cursor()
    
    indicators = ["VIX", "DXY", "US10Y", "US2Y", "YIELD_SPREAD_2Y10Y"]
    result = {}
    
    for ind in indicators:
        cur.execute("""
            SELECT value, change_pct FROM macro_indicators
            WHERE indicator = ? ORDER BY date DESC LIMIT 1
        """, (ind,))
        row = cur.fetchone()
        result[ind] = {"value": row[0], "change": row[1]} if row else {"value": None, "change": None}
    
    conn.close()
    return result

def get_us_fund_flow(date_str):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT symbol, sector, net_flow_billion, price_change
        FROM us_fund_flow
        WHERE date = ?
        ORDER BY ABS(net_flow_billion) DESC
        LIMIT 5
    """, (date_str,))
    
    rows = cur.fetchall()
    conn.close()
    return rows

def generate_daily_report(date_str):
    """產出每日回報 markdown"""
    inst = get_institutional_summary(date_str)
    margin = get_margin_summary(date_str)
    sectors = get_sector_flow(date_str)
    macro = get_macro_indicators()
    us_flow = get_us_fund_flow(date_str)
    
    foreign_days = get_consecutive_days(date_str, "foreign_net", "buy")
    trust_days = get_consecutive_days(date_str, "trust_net", "buy")
    sell_days = get_consecutive_days(date_str, "foreign_net", "sell")
    
    # VIX 情緒
    vix_val = macro.get("VIX", {}).get("value")
    vix_sentiment = get_vix_sentiment(vix_val)
    
    # 市場情緒
    total_net = inst["total"]
    vix_s = vix_val or 20
    
    if total_net > 10_000_000_000 and vix_s < 18:
        sentiment = "RISK ON 📈 法人偏多"
    elif total_net < -10_000_000_000 or vix_s > 25:
        sentiment = "RISK OFF 📉 法人偏空"
    else:
        sentiment = "NEUTRAL ⚖️ 震盪整理"
    
    # 殖利率利差
    spread = macro.get("YIELD_SPREAD_2Y10Y", {}).get("value")
    spread_txt = f"{spread:.4f}" if spread else "N/A"
    
    # ===== 產出文字 ======
    lines = [
        f"📊 宏觀法人每日回報 {date_str}",
        "",
        "【三大法人買賣超】",
        f"• 外資：{format_billion(inst['foreign'])} (連續{foreign_days}天買超)" if foreign_days > 0 else f"• 外資：{format_billion(inst['foreign'])} (連續{sell_days}天賣超)",
        f"• 投信：{format_billion(inst['trust'])} (連續{trust_days}天買超)" if trust_days > 0 else f"• 投信：{format_billion(inst['trust'])}",
        f"• 自營：{format_billion(inst['dealer'])}",
        f"• 合計：{format_billion(inst['total'])}",
        "",
        "【產業資金流向】",
    ]
    
    if sectors:
        for sec, net in sectors:
            sign = "+" if net >= 0 else ""
            lines.append(f"• {sec}：{sign}{round(net/1e9, 2)}億")
    else:
        lines.append("• 暫無資料")
    
    lines.extend([
        "",
        "【ETF 持股追蹤】",
        "• 0050/0056 持股資料請見完整系統",
        "",
        "【融資融券】",
        f"• 融資餘額：{round(margin['balance']/1e8, 1)}萬口",
        f"• 融資总值：{round(margin['value']/1e8, 1)}億",
        "",
        "【美股資金流】",
    ])
    
    if us_flow:
        for sym, sec, flow, chg in us_flow:
            sign = "+" if flow >= 0 else ""
            lines.append(f"• {sym}：{sign}{flow:.2f}億 ({sec})")
    else:
        lines.append("• 請執行美股資金流抓取腳本")
    
    lines.extend([
        "",
        "【宏觀指標】",
        f"• VIX：{vix_val:.2f} ({vix_sentiment})" if vix_val else "• VIX：N/A",
        f"• DXY：{macro.get('DXY',{}).get('value','N/A')}",
        f"• 10Y殖利率：{macro.get('US10Y',{}).get('value', 'N/A'):.3f}%" if macro.get('US10Y',{}).get('value') else "• 10Y殖利率：N/A",
        f"• 2Y殖利率：{macro.get('US2Y',{}).get('value', 'N/A'):.3f}%" if macro.get('US2Y',{}).get('value') else "• 2Y殖利率：N/A",
        f"• 2Y-10Y利差：{spread_txt}",
        "",
        "【資金流向結論】",
        f"• {sentiment}",
        f"• 法人偏向：{'買超' if inst['total'] >= 0 else '賣超'}格局",
    ])
    
    # 簡單建議
    if inst["foreign"] > 5_000_000_000 and vix_val and vix_val < 20:
        lines.append("• 建議：偏多操作，留意美股連動")
    elif inst["foreign"] < -5_000_000_000 or (vix_val and vix_val > 25):
        lines.append("• 建議：保守操作，降低槓桿")
    else:
        lines.append("• 建議：區間操作，等待突破")
    
    report = "\n".join(lines)
    
    # 存檔
    report_file = f"{REPORT_DIR}/macro_daily_report_{date_str}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    return report, report_file

if __name__ == "__main__":
    import sys, io, codecs
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    date_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    result = generate_daily_report(date_arg)
    print(f"Report saved to: {result[1]}")
