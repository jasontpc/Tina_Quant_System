"""
Institutional Flow Analyzer
分析法人資金流向：三大法人連續買賣超、主力區域、機構倉位變化
"""
import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = "./data/macro_institutional.db"
CONFIG_PATH = "./configs/macro_config.json"

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_institutional_summary(date_str):
    """取得特定日期的法人買賣超彙總"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            COALESCE(SUM(foreign_net), 0) as foreign_net,
            COALESCE(SUM(trust_net), 0) as trust_net,
            COALESCE(SUM(dealer_net), 0) as dealer_net,
            COALESCE(SUM(total_net), 0) as total_net,
            COUNT(*) as stock_count
        FROM institutional_daily
        WHERE date = ?
    """, (date_str,))
    
    row = cur.fetchone()
    conn.close()
    
    return {
        "date": date_str,
        "foreign_net": row[0] or 0,
        "trust_net": row[1] or 0,
        "dealer_net": row[2] or 0,
        "total_net": row[3] or 0,
        "stock_count": row[4] or 0
    }

def get_consecutive_days(date_str, field="foreign_net", direction="buy", days=30):
    """計算法人連續買/賣超天數"""
    conn = get_connection()
    cur = conn.cursor()
    
    operator = ">=" if direction == "buy" else "<"
    threshold = 0
    
    dates = []
    for i in range(days):
        d = datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        
        cur.execute(f"""
            SELECT COALESCE(SUM({field}), 0) FROM institutional_daily
            WHERE date = ?
        """, (d_str,))
        net = cur.fetchone()[0]
        
        if (direction == "buy" and net > 0) or (direction == "sell" and net < 0):
            dates.append((d_str, net))
        else:
            break
    
    conn.close()
    return dates

def get_top_sectors(date_str, top_n=5, field="foreign_net"):
    """取得資金流向最強/最弱的產業"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute(f"""
        SELECT sector, SUM({field}) as net
        FROM sector_flow
        WHERE date = ?
        GROUP BY sector
        ORDER BY net DESC
        LIMIT ?
    """, (date_str, top_n))
    
    top = cur.fetchall()
    cur.execute(f"""
        SELECT sector, SUM({field}) as net
        FROM sector_flow
        WHERE date = ?
        GROUP BY sector
        ORDER BY net ASC
        LIMIT ?
    """, (date_str, top_n))
    
    bottom = cur.fetchall()
    conn.close()
    
    return {"top": top, "bottom": bottom}

def get_margin_summary(date_str):
    """取得融資融券彙總"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            SUM(margin_balance) as total_margin,
            SUM(short_balance) as total_short,
            SUM(margin_balance_value) as total_value
        FROM margin_balance
        WHERE date = ?
    """, (date_str,))
    
    row = cur.fetchone()
    conn.close()
    
    return {
        "date": date_str,
        "total_margin": row[0] or 0,
        "total_short": row[1] or 0,
        "total_value": row[2] or 0
    }

def get_recent_trend(days=5):
    """取得最近 N 天的法人趨勢"""
    conn = get_connection()
    cur = conn.cursor()
    
    rows = []
    for i in range(days):
        d = datetime.now() - timedelta(days=i+1)
        d_str = d.strftime("%Y-%m-%d")
        
        cur.execute("""
            SELECT 
                COALESCE(SUM(foreign_net), 0),
                COALESCE(SUM(trust_net), 0),
                COALESCE(SUM(dealer_net), 0),
                COALESCE(SUM(total_net), 0)
            FROM institutional_daily
            WHERE date = ?
        """, (d_str,))
        
        row = cur.fetchone()
        if row:
            rows.append({
                "date": d_str,
                "foreign": row[0] or 0,
                "trust": row[1] or 0,
                "dealer": row[2] or 0,
                "total": row[3] or 0
            })
    
    conn.close()
    return rows

def analyze_flow(date_str):
    """完整法人資金流向分析"""
    summary = get_institutional_summary(date_str)
    foreign_streak = get_consecutive_days(date_str, "foreign_net", "buy")
    trust_streak = get_consecutive_days(date_str, "trust_net", "buy")
    sectors = get_top_sectors(date_str)
    margin = get_margin_summary(date_str)
    trend = get_recent_trend(5)
    
    # 情緒判斷
    vix_val = get_latest_macro("VIX")
    total_net = summary["total_net"]
    
    if vix_val and vix_val > 25:
        sentiment = "RISK_OFF"
    elif total_net > 5_000_000_000:
        sentiment = "RISK_ON"
    elif total_net < -5_000_000_000:
        sentiment = "RISK_OFF"
    else:
        sentiment = "NEUTRAL"
    
    return {
        "date": date_str,
        "summary": summary,
        "foreign_streak": len(foreign_streak),
        "trust_streak": len(trust_streak),
        "sectors": sectors,
        "margin": margin,
        "trend": trend,
        "sentiment": sentiment
    }

def get_latest_macro(indicator):
    """取得最新的宏觀指標值"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT value FROM macro_indicators
        WHERE indicator = ?
        ORDER BY date DESC LIMIT 1
    """, (indicator,))
    
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def format_billion(val):
    """轉換為億單位"""
    return round(val / 1_000_000_000, 2)

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    date_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    
    result = analyze_flow(date_arg)
    print(f"=== Institutional Flow Analysis {date_arg} ===")
    print(f"Foreign: {format_billion(result['summary']['foreign_net'])}億 (streak: {result['foreign_streak']} days)")
    print(f"Trust: {format_billion(result['summary']['trust_net'])}億 (streak: {result['trust_streak']} days)")
    print(f"Dealer: {format_billion(result['summary']['dealer_net'])}億")
    print(f"Total: {format_billion(result['summary']['total_net'])}億")
    print(f"Sentiment: {result['sentiment']}")
    print(f"VIX: {get_latest_macro('VIX')}")
