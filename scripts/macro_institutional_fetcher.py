import requests, sqlite3, os, json, time, logging
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "./data/macro_institutional.db"
CONFIG_PATH = "./configs/macro_config.json"
LOG_DIR = "./logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(filename=f"{LOG_DIR}/macro_fetcher.log", level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_connection():
    return sqlite3.connect(DB_PATH)

# ====== TWSE T86: 三大法人買賣超 ======
def fetch_twse_institutional(date_str):
    """
    TWSE T86 API: 每位股票的三大法人買賣超（以股數為單位）
    資料延遲發布，通常下午 16:30 後才可用
    """
    date_code = date_str.replace("-", "")
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_code}&response=json&selectType=ALL"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120", "Referer": "https://www.twse.com.tw"}

    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                logger.warning(f"TWSE T86 HTTP {resp.status_code}")
                time.sleep(5 * (attempt + 1))
                continue

            # Content is Big5 encoded
            raw_text = resp.content.decode('big5', errors='replace')
            data = json.loads(raw_text)

            if data.get("stat") != "OK":
                logger.warning(f"TWSE T86 stat={data.get('stat')}")
                time.sleep(5)
                continue

            fields = data.get("fields", [])
            rows = data.get("data", [])
            logger.info(f"  TWSE T86: {len(rows)} rows fetched")

            if not rows:
                return 0

            # Field mapping (Big5 encoded labels):
            # 0: stock_id, 1: stock_name
            # 2: foreign buy (shares), 3: foreign sell, 4: foreign net
            # 5: trust buy, 6: trust sell, 7: trust net
            # 8: dealer buy, 9: dealer sell, 10: dealer net
            # ...remaining fields are various sub-categories
            #
            # We store net values for the 3 main categories (indices 4, 7, 10)

            def parse_num(val):
                if val == '--' or val == '':
                    return 0
                return int(str(val).replace(',', ''))

            conn = get_connection()
            cur = conn.cursor()
            saved = 0

            for row in rows:
                if len(row) < 11:
                    continue
                try:
                    stock_id = str(row[0]).strip()
                    stock_name = str(row[1]).strip() if len(row) > 1 else ''
                    foreign_net = parse_num(row[4]) if len(row) > 4 else 0
                    trust_net = parse_num(row[7]) if len(row) > 7 else 0
                    dealer_net = parse_num(row[10]) if len(row) > 10 else 0

                    cur.execute("""
                        INSERT OR REPLACE INTO institutional_daily
                        (date, stock_id, stock_name, foreign_net, trust_net, dealer_net, total_net)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (date_str, stock_id, stock_name,
                          foreign_net, trust_net, dealer_net,
                          foreign_net + trust_net + dealer_net))
                    saved += 1
                except Exception as e:
                    continue

            conn.commit()
            conn.close()
            logger.info(f"  TWSE institutional: {saved} records saved for {date_str}")
            return saved

        except Exception as e:
            logger.error(f"TWSE T86 error (attempt {attempt+1}): {e}")
            time.sleep(5 * (attempt + 1))

    return 0

# ====== TWSE 融資融券 ======
def fetch_twse_margin(date_str):
    """TWSE 融資融券餘額"""
    date_code = date_str.replace("-", "")
    url = f"https://www.twse.com.tw/rwd/zh/margin/FU/{date_code}?response=json"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.twse.com.tw"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        raw_text = resp.content.decode('big5', errors='replace')
        data = json.loads(raw_text)

        if data.get("stat") != "OK":
            logger.warning(f"TWSE margin stat={data.get('stat')}")
            return 0

        rows = data.get("data", [])
        conn = get_connection()
        cur = conn.cursor()
        saved = 0

        for row in rows:
            if len(row) < 5:
                continue
            try:
                stock_id = str(row[0]).strip()
                stock_name = str(row[1]).strip() if len(row) > 1 else ''
                margin = int(str(row[2]).replace(',', '').replace('--', '0')) if row[2] != '--' else 0
                short = int(str(row[3]).replace(',', '').replace('--', '0')) if len(row) > 3 and row[3] != '--' else 0
                change = int(str(row[4]).replace(',', '').replace('--', '0')) if len(row) > 4 and row[4] != '--' else 0

                cur.execute("""
                    INSERT OR REPLACE INTO margin_balance
                    (date, stock_id, stock_name, margin_balance, short_balance, balance_change)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (date_str, stock_id, stock_name, margin, short, change))
                saved += 1
            except:
                continue

        conn.commit()
        conn.close()
        logger.info(f"  TWSE margin: {saved} records for {date_str}")
        return saved

    except Exception as e:
        logger.error(f"TWSE margin error: {e}")
        return 0

# ====== yfinance 美股資金流 ======
def fetch_us_fund_flow(date_str):
    """yfinance: 美股常見ETF報價變化作為資金流向代理"""
    symbols_sectors = [
        ("QQQ", "科技"), ("XLK", "科技"), ("XLF", "金融"),
        ("XLE", "能源"), ("XLV", "醫療"), ("XLY", "消費"),
        ("XLP", "消費"), ("SMH", "半導體"), ("ARKK", "創新"),
        ("GLD", "黃金"), ("TLT", "長債"), ("LQD", "投資級債"),
        ("IWM", "小型股"), ("SPY", "大盤"), ("DIA", "道瓊"),
    ]

    conn = get_connection()
    cur = conn.cursor()
    saved = 0

    for sym, sector in symbols_sectors:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5d", auto_adjust=True)
            if hist.empty or len(hist) < 2:
                continue

            price_now = hist["Close"].iloc[-1]
            price_prev = hist["Close"].iloc[-2]
            pct_chg = (price_now - price_prev) / price_prev * 100 if price_prev else 0
            volume_b = hist["Volume"].iloc[-1] / 1e9 if len(hist) else 0

            # Net flow direction: compare volume to 5-day average
            if len(hist) >= 5:
                avg_vol = hist["Volume"].iloc[-5:].mean()
                vol_ratio = hist["Volume"].iloc[-1] / avg_vol if avg_vol else 1
            else:
                vol_ratio = 1

            # Estimate net flow sign based on price direction + volume
            flow_direction = 1 if pct_chg > 0 else -1
            est_flow = vol_ratio * flow_direction  # relative unit

            cur.execute("""
                INSERT OR REPLACE INTO us_fund_flow
                (date, symbol, sector, price_change, volume_billion)
                VALUES (?, ?, ?, ?, ?)
            """, (date_str, sym, sector, pct_chg, volume_b))
            saved += 1

        except Exception as e:
            continue

    conn.commit()
    conn.close()
    logger.info(f"  US fund flow: {saved} symbols for {date_str}")
    return saved

# ====== Sector Flow ======
def compute_sector_flow(date_str):
    """根據個股法人資料彙總為產業流向"""
    conn = get_connection()
    cur = conn.cursor()

    # Simple sector mapping based on stock ID prefix
    sector_map = {
        '23': '半導體', '24': '半導體', '25': '半導體',
        '30': '電子', '31': '電子', '32': '電子', '33': '電子',
        '26': '光電', '27': '光電',
        '28': '通信', '29': '通信',
        '34': '通路',
        '58': '金融', '61': '金融', '62': '金融',
        '71': '壽險', '72': '壽險', '73': '壽險',
        '20': '鋼鐵', '21': '鋼鐵', '22': '鋼鐵',
        '15': '航運', '16': '航運', '17': '航運',
        '11': '化學', '12': '化學',
        '41': '生技', '42': '生技',
        '81': '油電', '82': '油電',
    }

    cur.execute("""
        SELECT stock_id, foreign_net, trust_net, dealer_net, total_net
        FROM institutional_daily
        WHERE date = ?
    """, (date_str,))

    sector_totals = {}
    for row in cur.fetchall():
        sid = row[0]
        prefix = sid[:2] if sid and len(sid) >= 2 else '00'
        sector = sector_map.get(prefix, '其他')
        if sector not in sector_totals:
            sector_totals[sector] = {'foreign': 0, 'trust': 0, 'dealer': 0, 'total': 0}
        sector_totals[sector]['foreign'] += row[1] or 0
        sector_totals[sector]['trust'] += row[2] or 0
        sector_totals[sector]['dealer'] += row[3] or 0
        sector_totals[sector]['total'] += row[4] or 0

    for sector, vals in sector_totals.items():
        cur.execute("""
            INSERT OR REPLACE INTO sector_flow
            (date, sector, foreign_net, trust_net, dealer_net, total_net)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (date_str, sector, vals['foreign'], vals['trust'], vals['dealer'], vals['total']))

    conn.commit()
    conn.close()
    return len(sector_totals)

# ====== Main fetch ======
def fetch_all(date_str=None):
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    results = {"date": date_str, "inst": 0, "margin": 0, "us_flow": 0, "sectors": 0, "errors": []}

    # TWSE institutional
    try:
        results["inst"] = fetch_twse_institutional(date_str)
        if results["inst"] > 0:
            results["sectors"] = compute_sector_flow(date_str)
    except Exception as e:
        logger.error(f"Inst fetch error: {e}")
        results["errors"].append(f"inst: {e}")

    # TWSE margin
    try:
        results["margin"] = fetch_twse_margin(date_str)
    except Exception as e:
        results["errors"].append(f"margin: {e}")

    # US fund flow
    try:
        results["us_flow"] = fetch_us_fund_flow(date_str)
    except Exception as e:
        results["errors"].append(f"us_flow: {e}")

    logger.info(f"fetch_all({date_str}): {results}")
    return results

if __name__ == "__main__":
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    result = fetch_all(date_arg)
    print(f"Result: {result}")
