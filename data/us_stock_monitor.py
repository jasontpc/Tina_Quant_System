"""
US Stock Monitor - Tina Quant System v3.12
Monitors D, BMY, SO, DXCM with daily technical/fundamental analysis
Target: Value/Growth stock screening with entry/exit signals
"""

import yfinance as yf
import sqlite3
import json
import logging
import os
from datetime import datetime, timedelta
import math

# ── Setup ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "data", "us_stocks_config.json")
DB_PATH = os.path.join(BASE_DIR, "data", "us_value_growth.db")
LOG_PATH = os.path.join(BASE_DIR, "logs", "us_stock_daily.log")

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("us_stock_monitor")


# ── Load Config ────────────────────────────────────────────────────────────────
def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


CONFIG = load_config()
TARGET_SYMBOLS = CONFIG["symbols"]


# ── Database Helpers ───────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # fundamentals
    c.execute("""
        CREATE TABLE IF NOT EXISTS fundamentals (
            symbol TEXT PRIMARY KEY,
            name_en TEXT,
            price REAL,
            market_cap REAL,
            shares_outstanding REAL,
            pe_ratio REAL,
            forward_pe REAL,
            eps REAL,
            revenue REAL,
            rev_growth REAL,
            op_margin REAL,
            roe REAL,
            debt_ratio REAL,
            div_yield REAL,
            beta REAL,
            updated_at TEXT
        )
    """)

    # technicals - check if table exists first
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='technicals'")
    tech_exists = c.fetchone() is not None

    if not tech_exists:
        c.execute("""
            CREATE TABLE technicals (
                symbol TEXT PRIMARY KEY,
                price REAL,
                volume REAL,
                vol_avg_20 REAL,
                rsi_14 REAL,
                rsi_30 REAL,
                ma5 REAL,
                ma20 REAL,
                ma60 REAL,
                bias5 REAL,
                bias20 REAL,
                bias60 REAL,
                bb_upper REAL,
                bb_lower REAL,
                bb_position REAL,
                mom_5d REAL,
                mom_20d REAL,
                mom_1m REAL,
                mom_3m REAL,
                high_52w REAL,
                low_52w REAL,
                pos_52w REAL,
                ma_align_text TEXT,
                atr_14 REAL,
                updated_at TEXT
            )
        """)
    else:
        # Add missing columns to existing table
        for col, col_type in [
            ("atr_14", "REAL"), ("ma_align_text", "TEXT"),
            ("mom_5d", "REAL"), ("mom_20d", "REAL"), ("mom_1m", "REAL"), ("mom_3m", "REAL")
        ]:
            try:
                c.execute(f"ALTER TABLE technicals ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

    # scores - check if table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores'")
    scores_exists = c.fetchone() is not None

    if not scores_exists:
        c.execute("""
            CREATE TABLE scores (
                symbol TEXT PRIMARY KEY,
                base_pass INTEGER,
                fund_pass INTEGER,
                tech_pass INTEGER,
                fund_score REAL,
                tech_score REAL,
                mom_score REAL,
                total_score REAL,
                signal TEXT,
                entry_price REAL,
                stop_loss REAL,
                profit_target REAL,
                risk_reward REAL,
                updated_at TEXT
            )
        """)
    else:
        for col, col_type in [
            ("base_pass", "INTEGER"), ("fund_pass", "INTEGER"), ("tech_pass", "INTEGER"),
            ("entry_price", "REAL"), ("stop_loss", "REAL"), ("profit_target", "REAL"), ("risk_reward", "REAL")
        ]:
            try:
                c.execute(f"ALTER TABLE scores ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

    # daily_log
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            symbol TEXT,
            price REAL,
            rsi_14 REAL,
            signal TEXT,
            score REAL,
            note TEXT
        )
    """)

    conn.commit()
    conn.close()
    log.info("Database initialized")


# ── Indicator Calculations ───────────────────────────────────────────────────
def calc_rsi(prices, period=14):
    """Calculate RSI using Wilder's method"""
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi_values = []
    for i in range(period, len(prices)):
        avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))
    return rsi_values


def calc_ma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calc_bollinger(prices, period=20, num_std=2):
    if len(prices) < period:
        return None, None, None
    ma = sum(prices[-period:]) / period
    variance = sum((p - ma) ** 2 for p in prices[-period:]) / period
    std = math.sqrt(variance)
    return ma + num_std * std, ma, ma - num_std * std


def calc_atr(highs, lows, closes, period=14):
    if len(highs) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def calc_momentum(prices, period):
    if len(prices) < period + 1:
        return None
    return (prices[-1] / prices[-period-1] - 1) * 100


def calc_bias(price, ma):
    if ma is None or ma == 0:
        return None
    return (price / ma - 1) * 100


def calc_bb_position(price, bb_upper, bb_lower):
    if bb_upper is None or bb_lower is None or bb_upper == bb_lower:
        return None
    return (price - bb_lower) / (bb_upper - bb_lower)


# ── Fetch & Process Stock ─────────────────────────────────────────────────────
def fetch_and_process(symbol):
    log.info(f"Fetching {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Get historical data (2 years for 52w + fundamentals)
        hist = ticker.history(period="2y")
        if hist.empty or len(hist) < 60:
            log.warning(f"{symbol}: Insufficient history ({len(hist)} rows)")
            return None

        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        volumes = hist["Volume"].tolist()

        latest_close = closes[-1]
        latest_volume = volumes[-1]

        # ── Technical Indicators ──────────────────────────────────────────
        rsi_14_list = calc_rsi(closes, 14)
        rsi_14 = rsi_14_list[-1] if rsi_14_list else None

        rsi_30_list = calc_rsi(closes, 30)
        rsi_30 = rsi_30_list[-1] if rsi_30_list else None

        ma5 = calc_ma(closes, 5)
        ma20 = calc_ma(closes, 20)
        ma60 = calc_ma(closes, 60)
        bias5 = calc_bias(latest_close, ma5)
        bias20 = calc_bias(latest_close, ma20)
        bias60 = calc_bias(latest_close, ma60)

        bb_upper, bb_middle, bb_lower = calc_bollinger(closes, 20)
        bb_position = calc_bb_position(latest_close, bb_upper, bb_lower)

        vol_avg_20 = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else None
        mom_5d = calc_momentum(closes, 5)
        mom_20d = calc_momentum(closes, 20)
        mom_1m = calc_momentum(closes, 21)
        mom_3m = calc_momentum(closes, 63)

        high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
        low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
        pos_52w = (latest_close - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5

        atr = calc_atr(highs, lows, closes, 14)

        # MA alignment text
        ma_align = []
        if ma5 and ma20:
            ma_align.append("ma5>ma20" if ma5 > ma20 else "ma5<ma20")
        if ma20 and ma60:
            ma_align.append("ma20>ma60" if ma20 > ma60 else "ma20<ma60")
        ma_align_text = ", ".join(ma_align) if ma_align else "neutral"

        # ── Fundamentals ───────────────────────────────────────────────────
        market_cap = info.get("marketCap")
        shares = info.get("sharesOutstanding")
        pe = info.get("trailingPE")
        fwd_pe = info.get("forwardPE")
        eps = info.get("trailingEps")
        revenue = info.get("totalRevenue")
        rev_growth = info.get("revenueGrowth")
        op_margin = info.get("operatingMargins")
        roe = info.get("returnOnEquity")
        debt_ratio = info.get("debtToEquity")
        div_yield = info.get("dividendYield")
        beta = info.get("beta")

        if div_yield and div_yield > 1:
            div_yield = div_yield / 100

        name_en = info.get("longName") or info.get("shortName") or symbol

        # ── Score & Signal ─────────────────────────────────────────────────
        stock_config = CONFIG["stocks"].get(symbol, {})
        style = stock_config.get("style", "growth")

        fund_score = 0.0
        fund_pass = 1

        # PE assessment
        pe_val = pe or 0
        if style == "pharma_value":
            if pe_val <= 14:
                fund_score += 3
            elif pe_val <= 17:
                fund_score += 2
            elif pe_val <= 20:
                fund_score += 1
        elif style in ("utility_income",):
            if 15 <= pe_val <= 20:
                fund_score += 2
            elif pe_val < 15:
                fund_score += 3
            elif pe_val > 25:
                fund_score -= 1
        else:  # growth
            if pe_val <= 25:
                fund_score += 2
            elif pe_val <= 35:
                fund_score += 1

        # Dividend yield
        dy = div_yield or 0
        if style in ("utility_income", "pharma_value"):
            if dy >= 3.5:
                fund_score += 2
            elif dy >= 2.5:
                fund_score += 1

        # Revenue growth
        rg = rev_growth or 0
        if rg >= 0.10:
            fund_score += 2
        elif rg >= 0.05:
            fund_score += 1
        elif rg < 0:
            fund_score -= 1
            fund_pass = 0

        # ROE
        r = roe or 0
        if r >= 0.15:
            fund_score += 2
        elif r >= 0.08:
            fund_score += 1
        elif r < 0:
            fund_pass = 0

        # Beta (stability for income stocks)
        b = beta or 1
        if style in ("utility_income", "pharma_value") and b > 1.2:
            fund_score -= 1

        # Technical score
        tech_score = 0.0
        tech_pass = 1

        ideal_rsi_max = stock_config.get("ideal_rsi_entry", 60)
        ideal_rsi_min = stock_config.get("ideal_rsi_entry_min", 30)
        ideal_rsi_max2 = stock_config.get("ideal_rsi_max", 70)

        if rsi_14:
            if style == "medtech_growth":
                if ideal_rsi_min <= rsi_14 <= ideal_rsi_max:
                    tech_score += 4
                elif rsi_14 < ideal_rsi_min:
                    tech_score += 5
                elif rsi_14 > ideal_rsi_max2:
                    tech_score -= 2
            else:
                if rsi_14 <= ideal_rsi_max:
                    tech_score += 3
                if rsi_14 <= 45:
                    tech_score += 2
                elif rsi_14 > ideal_rsi_max2:
                    tech_score -= 2

        # MA alignment
        if ma20 and ma60:
            if ma20 > ma60:
                tech_score += 2
            else:
                tech_score -= 1

        # 52-week position
        if pos_52w:
            if pos_52w < 0.30:
                tech_score += 2  # near 52w low - upside potential
            elif pos_52w > 0.80:
                tech_score -= 1

        # Momentum
        mom_score = 0.0
        if mom_1m is not None:
            if mom_1m > 5:
                mom_score += 2
            elif mom_1m < -5:
                mom_score -= 1

        total_score = fund_score + tech_score + mom_score

        # Signal
        if style == "medtech_growth":
            if rsi_14 and rsi_14 < 40 and tech_score >= 5:
                signal = "STRONG_BUY"
            elif rsi_14 and ideal_rsi_min <= rsi_14 <= ideal_rsi_max and tech_score >= 3:
                signal = "BUY"
            elif rsi_14 and rsi_14 > ideal_rsi_max2:
                signal = "OVERBOUGHT"
            else:
                signal = "HOLD"
        else:
            if rsi_14 and rsi_14 <= 45 and tech_score >= 4:
                signal = "STRONG_BUY"
            elif rsi_14 and rsi_14 <= ideal_rsi_max and fund_score >= 3:
                signal = "BUY"
            elif rsi_14 and rsi_14 > ideal_rsi_max2:
                signal = "OVERBOUGHT"
            else:
                signal = "HOLD"

        base_pass = 1 if signal in ("BUY", "STRONG_BUY") else 0

        # ── Entry/Exit Rules ──────────────────────────────────────────────
        atr_stop_pct = stock_config.get("atr_stop_pct", 0.05)
        profit_target_pct = stock_config.get("profit_target_pct", 0.12)

        if atr and atr > 0:
            stop_loss = latest_close * (1 - atr_stop_pct)
            profit_target = latest_close * (1 + profit_target_pct)
        else:
            stop_loss = latest_close * (1 - atr_stop_pct)
            profit_target = latest_close * (1 + profit_target_pct)

        risk = latest_close - stop_loss
        reward = profit_target - latest_close
        risk_reward = reward / risk if risk > 0 else 0

        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Store data
        conn = get_conn()
        c = conn.cursor()

        c.execute("""
            INSERT OR REPLACE INTO fundamentals
            (symbol, name_en, price, market_cap, shares_outstanding,
             pe_ratio, forward_pe, eps, revenue, rev_growth, op_margin,
             roe, debt_ratio, div_yield, beta, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, name_en, latest_close, market_cap, shares,
              pe, fwd_pe, eps, revenue, rev_growth, op_margin,
              roe, debt_ratio, div_yield, beta, updated_at))

        c.execute("""
            INSERT OR REPLACE INTO technicals
            (symbol, price, volume, vol_avg_20, rsi_14, rsi_30,
             ma5, ma20, ma60, bias5, bias20, bias60,
             bb_upper, bb_lower, bb_position,
             mom_5d, mom_20d, mom_1m, mom_3m,
             high_52w, low_52w, pos_52w, ma_align_text, atr_14, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, latest_close, latest_volume, vol_avg_20,
              rsi_14, rsi_30, ma5, ma20, ma60, bias5, bias20, bias60,
              bb_upper, bb_lower, bb_position,
              mom_5d, mom_20d, mom_1m, mom_3m,
              high_52w, low_52w, pos_52w, ma_align_text, atr, updated_at))

        c.execute("""
            INSERT OR REPLACE INTO scores
            (symbol, base_pass, fund_pass, tech_pass, fund_score, tech_score,
             mom_score, total_score, signal, entry_price, stop_loss,
             profit_target, risk_reward, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (symbol, base_pass, fund_pass, tech_pass, fund_score, tech_score,
              mom_score, total_score, signal, latest_close, stop_loss,
              profit_target, risk_reward, updated_at))

        c.execute("""
            INSERT INTO daily_log (date, symbol, price, rsi_14, signal, score, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d"), symbol, latest_close,
              rsi_14, signal, total_score, ""))

        conn.commit()
        conn.close()

        log.info(f"{symbol}: price={latest_close:.2f} RSI={rsi_14:.1f} signal={signal} score={total_score:.1f}")

        return {
            "symbol": symbol,
            "name": name_en,
            "price": latest_close,
            "rsi_14": rsi_14,
            "rsi_30": rsi_30,
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "bias20": bias20,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "bb_position": bb_position,
            "vol_avg_20": vol_avg_20,
            "mom_1m": mom_1m,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pos_52w": pos_52w,
            "atr": atr,
            "ma_align_text": ma_align_text,
            "pe": pe,
            "forward_pe": fwd_pe,
            "eps": eps,
            "div_yield": div_yield,
            "rev_growth": rev_growth,
            "roe": roe,
            "beta": beta,
            "fund_score": fund_score,
            "tech_score": tech_score,
            "mom_score": mom_score,
            "total_score": total_score,
            "signal": signal,
            "entry_price": latest_close,
            "stop_loss": stop_loss,
            "profit_target": profit_target,
            "risk_reward": risk_reward,
            "style": style,
        }

    except Exception as e:
        log.error(f"Error processing {symbol}: {e}")
        return None


# ── Build Report ──────────────────────────────────────────────────────────────
def safe_print(msg):
    """Print with ASCII fallback for Windows console"""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Replace emoji with ASCII equivalents
        replacements = {
            '\U0001f4ca': '[CHART]', '\U0001f4b0': '[$$$]',
            '\U0001f7e2': '[GREEN]', '\U0001f7e1': '[YEL]',
            '\U0001f7e0': '[ORANGE]', '\U0001f7e3': '[RED]',
            '\U0001f53d': '[PT]', '\U0001f4c8': '[CHART]',
            '\U0001f4c9': '[CHART]', '\U0001f4cc': '[PIN]',
            '\U0001f4ce': '[PIN]', '\U0001f517': '[LINK]',
            '\U0001f50d': '[MAG]', '\U0001f3af': '[TGT]',
            '\U0001f3f3': '[FL]', '\U0001f505': '[SYNC]',
            '\U0001f4b8': '[INV]', '\u2714': '[OK]',
            '\u274c': '[X]', '\u2705': '[OK]',
            '\U0001f504': '[ROT]', '\U0001f525': '[HOT]',
            '\U0001f680': '[ROCK]', '\u2600': '[SUN]',
            '\U0001f300': '[CYCL]', '\U0001f319': '[MOON]',
            '\U0001f4a1': '[IDEA]', '\U0001f4a4': '[ZZZ]',
            '\U0001f441': '[EYE]', '\U0001f4e6': '[BOX]',
            '\U0001f4e7': '[MAIL]', '\U0001f4e8': '[MAIL]',
            '\u2022': '*', '\u2013': '-', '\u2014': '--',
            '\u00a0': ' ', '|': '/', '\x92': "'",
        }
        ascii_msg = msg
        for em, asc in replacements.items():
            ascii_msg = ascii_msg.replace(em, asc)
        # Remove any remaining non-ascii chars
        ascii_msg = ascii_msg.encode('ascii', errors='replace').decode('ascii')
        print(ascii_msg)


def build_report(results):
    """Build a Telegram-friendly report from processed results"""
    if not results:
        return "❌ No data available"

    lines = []
    lines.append("📊 *US Stock Daily Report*")
    lines.append(f"__{datetime.now().strftime('%Y-%m-%d %H:%M')}__")
    lines.append("")

    for r in results:
        if r is None:
            continue

        cfg = CONFIG["stocks"].get(r["symbol"], {})

        lines.append(f"📌 *{r['symbol']}* — {r['name']}")
        lines.append(f"💰 Price: ${r['price']:.2f}")

        # Signal badge
        sig = r["signal"]
        sig_emoji = {"STRONG_BUY": "🟢🟢", "BUY": "🟢", "HOLD": "🟡", "OVERBOUGHT": "🔴"}.get(sig, "⚪")
        lines.append(f"{sig_emoji} Signal: `{sig}`")

        # Technical
        rsi = r["rsi_14"]
        lines.append(f"RSI(14): {rsi:.1f}" if rsi else "RSI(14): N/A")

        ma20 = r["ma20"]
        bias = r["bias20"]
        ma20_str = f"${ma20:.2f}" if ma20 else "N/A"
        bias_str = f"{bias:+.2f}%" if bias else "N/A"
        lines.append(f"MA20: {ma20_str} | Bias: {bias_str}")

        pos52 = r["pos_52w"]
        pos_str = f"{pos52*100:.1f}%" if pos52 else "N/A"
        lines.append(f"52W Position: {pos_str} (${r['low_52w']:.2f}–${r['high_52w']:.2f})")

        atr = r["atr"]
        atr_str = f"${atr:.2f}" if atr else "N/A"
        lines.append(f"ATR(14): {atr_str}")

        # Fundamentals
        pe = r["pe"]
        dy = r["div_yield"]
        lines.append(f"PE: {pe:.2f}" if pe else "PE: N/A")
        if dy:
            lines.append(f"Dividend: {dy*100:.2f}%")
        rg = r["rev_growth"]
        if rg:
            lines.append(f"Rev Growth: {rg*100:.1f}%")

        # Scores
        lines.append(f"Scores: F={r['fund_score']:.1f} T={r['tech_score']:.1f} M={r['mom_score']:.1f} | Total={r['total_score']:.1f}")

        # Entry/Exit Rules
        sl = r["stop_loss"]
        pt = r["profit_target"]
        rr = r["risk_reward"]
        lines.append(f"Entry: ${r['entry_price']:.2f} | SL: ${sl:.2f} | TP: ${pt:.2f}")
        lines.append(f"Risk/Reward: {rr:.2f}x")

        # Notes
        notes = cfg.get("notes", "")
        if notes:
            lines.append(f"📝 {notes}")

        # Entry zone check
        style = r.get("style", "")
        ideal_rsi_max = cfg.get("ideal_rsi_entry", 60)
        ideal_rsi_min = cfg.get("ideal_rsi_entry_min", 30)
        if style == "medtech_growth":
            if rsi and ideal_rsi_min <= rsi <= ideal_rsi_max:
                lines.append("✅ *In RSI entry zone (40-50)!*")
            elif rsi and rsi < ideal_rsi_min:
                lines.append("⚡ *Deep oversold - potential reversal setup*")
        else:
            if rsi and rsi <= ideal_rsi_max:
                lines.append("✅ *In RSI entry zone*")

        lines.append("")
        lines.append("─────────────────")
        lines.append("")

    # Summary
    buy_signals = [r for r in results if r and r["signal"] in ("STRONG_BUY", "BUY")]
    if buy_signals:
        lines.append(f"🟢 *{len(buy_signals)} BUY/STRONG_BUY signals today*")
        for r in buy_signals:
            lines.append(f"  • {r['symbol']} @ ${r['price']:.2f} (score={r['total_score']:.1f})")
    else:
        lines.append("🟡 No BUY signals today — stay patient")

    return "\n".join(lines)


# ── Telegram Push ──────────────────────────────────────────────────────────────
def push_telegram(message, chat_id=None):
    try:
        import requests
        chat_id = chat_id or CONFIG.get("telegram_chat_id", "1616824689")

        # Read bot token from .env
        env_path = os.path.join(BASE_DIR, ".env")
        bot_token = None
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        bot_token = line.split("=", 1)[1].strip()
                        break

        if not bot_token:
            log.warning("TELEGRAM_BOT_TOKEN not found in .env")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code == 200:
            log.info("Telegram message sent successfully")
            return True
        else:
            log.error(f"Telegram error: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        log.error(f"Telegram push failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def run(dry_run=False, push=True):
    log.info("=" * 60)
    log.info("US Stock Monitor — Daily Run")
    init_db()

    results = []
    for sym in TARGET_SYMBOLS:
        r = fetch_and_process(sym)
        results.append(r)

    report = build_report(results)
    safe_print("\n" + report + "\n")

    if push and not dry_run:
        push_telegram(report)

    log.info("US Stock Monitor — Run Complete")
    return results


if __name__ == "__main__":
    import sys
    dry = "--dry" in sys.argv
    run(dry_run=dry, push=not dry)