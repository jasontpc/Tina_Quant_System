"""
Tina 台股成長股篩選器 - 廣泛版本 v2
三層過濾：基礎條件 -> 基本面 -> 技術面
股價 < 100 TWD 之優質成長股

用法: python tw_growth_screener_unlimited.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import time
import sys
import os

# 設定區
BASE_DIR = r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System"
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

BATCH_SIZE = 20
OUTPUT_FILE = os.path.join(DATA_DIR, "tw_growth_under_100_full.csv")

# 擴大股票池（手動驗證過的有潛力候選）
STOCK_POOL = [
    # 電子/半導體（股價低於100的）
    "2377.TW", "2399.TW", "2428.TW", "2465.TW", "2492.TW",
    "2441.TW", "2449.TW", "2481.TW", "2495.TW", "2497.TW",
    "3033.TW", "3037.TW", "3044.TW", "3045.TW", "3056.TW",
    "3229.TW", "3231.TW", "3257.TW", "3311.TW", "3312.TW",
    "3380.TW", "3416.TW", "3437.TW", "3443.TW", "3450.TW",
    "3481.TW", "3504.TW", "3515.TW", "3530.TW", "3532.TW",
    "3545.TW", "3552.TW", "3559.TW", "3563.TW", "3570.TW",
    "3596.TW", "3607.TW", "3623.TW", "3628.TW", "3646.TW",
    "3653.TW", "3661.TW", "3663.TW", "3673.TW", "3680.TW",
    "3706.TW", "3711.TW", "3714.TW", "4938.TW", "4952.TW",
    "5388.TW", "5469.TW", "5471.TW",
    # 網通/光電
    "2344.TW", "2345.TW", "2356.TW", "2363.TW", "2371.TW",
    "2412.TW", "2434.TW", "2451.TW", "2458.TW",
    "2618.TW", "2625.TW",
    # 傳產/價值
    "1102.TW", "1504.TW", "1708.TW", "1721.TW",
    "2002.TW", "2006.TW", "2017.TW", "2022.TW", "2027.TW", "2028.TW",
    "2101.TW", "2103.TW", "2104.TW", "2106.TW", "2108.TW",
    "2201.TW", "2204.TW", "2207.TW", "2208.TW", "2211.TW",
    "2221.TW", "2227.TW", "2231.TW", "2233.TW", "2236.TW",
    "2504.TW", "2515.TW",
    # 金融（放寬檢查）
    "2801.TW", "2812.TW", "2816.TW", "2855.TW",
    "2881.TW", "2882.TW", "2883.TW", "2884.TW",
    "2885.TW", "2886.TW", "2891.TW", "2892.TW",
    # 綠能/基建
    "2610.TW", "2615.TW", "2633.TW", "3023.TW", "3031.TW",
    "3515.TW", "3665.TW", "5505.TW", "6164.TW",
    # 生技
    "3171.TW", "4123.TW", "4102.TW", "4164.TW", "4737.TW",
    "4912.TW", "4991.TW", "6703.TW",
    # 其他人氣股
    "4119.TW", "4152.TW", "4532.TW", "4720.TW", "4764.TW",
    "4906.TW", "4919.TW", "4924.TW", "4947.TW", "4958.TW",
    "4976.TW", "5212.TW", "5213.TW", "5234.TW", "5305.TW",
    "6116.TW", "6139.TW", "6153.TW", "6223.TW", "6227.TW",
    "6240.TW", "6241.TW", "6281.TW", "6283.TW", "6285.TW",
    "6404.TW", "6416.TW", "6457.TW", "6477.TW", "6492.TW",
    "6494.TW", "6523.TW", "6548.TW", "6552.TW", "6573.TW",
    "6579.TW", "6590.TW", "6702.TW", "6706.TW", "6712.TW",
    "6752.TW", "6770.TW",
    "8016.TW", "8021.TW", "8038.TW", "8050.TW",
    "8070.TW", "8081.TW", "8092.TW", "8104.TW", "8112.TW",
    "8213.TW", "8249.TW", "8261.TW",
    "8411.TW", "8464.TW", "8478.TW",
    "9904.TW", "9907.TW", "9910.TW", "9914.TW", "9917.TW",
    "9919.TW", "9921.TW", "9925.TW", "9931.TW", "9934.TW",
    "9938.TW", "9941.TW", "9945.TW",
]

# 去重
STOCK_POOL = list(dict.fromkeys(STOCK_POOL))
print(f"[INIT] Stock pool: {len(STOCK_POOL)} stocks")


def log(msg):
    print(f"  {msg}", flush=True)


def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    closes = np.array(prices, dtype=float)
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def calc_score(row):
    score = 0
    # 基本面 (40分)
    rev = row.get("revenue_yoy", -999)
    if rev >= 20:
        score += 15
    elif rev >= 10:
        score += 10
    elif rev >= 5:
        score += 5

    pe = row.get("pe", 999)
    if 0 < pe <= 15:
        score += 10
    elif 15 < pe <= 20:
        score += 7
    elif 20 < pe <= 30:
        score += 4

    roe = row.get("roe", 0)
    if roe >= 15:
        score += 8
    elif roe >= 10:
        score += 5
    elif roe >= 5:
        score += 2

    opm = row.get("op_margin", 0)
    if opm >= 15:
        score += 4
    elif opm >= 10:
        score += 3
    elif opm >= 5:
        score += 1

    # 技術面 (30分)
    rsi = row.get("rsi", 50)
    if 35 <= rsi <= 55:
        score += 10
    elif 30 <= rsi < 35 or 55 < rsi <= 70:
        score += 5

    ma_status = row.get("ma_status", "N/A")
    if ma_status in ["MA20下方", "接近MA20"]:
        score += 10
    elif ma_status == "MA20上方":
        score += 4

    mom = row.get("momentum", 0)
    if mom >= 5:
        score += 5
    elif mom >= 0:
        score += 3
    elif mom >= -10:
        score += 1

    # 估值安全 (30分)
    price = row.get("price", 999)
    if price <= 50:
        score += 15
    elif price <= 80:
        score += 10
    elif price <= 100:
        score += 5

    mcap = row.get("market_cap", 0)
    if mcap >= 500_000_000_000:
        score += 8
    elif mcap >= 100_000_000_000:
        score += 5

    vol = row.get("volume", 0)
    if vol >= 5_000_000:
        score += 7
    elif vol >= 1_000_000:
        score += 4

    return round(score, 1)


def get_signal(score):
    if score >= 70:
        return "STRONG BUY"
    elif score >= 55:
        return "WATCH"
    elif score >= 40:
        return "HOLD"
    else:
        return "PASS"


def main():
    results = []
    total = len(STOCK_POOL)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[START] Scanning {total} stocks | {now_str}")

    for i in range(0, total, BATCH_SIZE):
        batch = STOCK_POOL[i:i+BATCH_SIZE]
        bn = i // BATCH_SIZE + 1
        tb = (total + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n[Batch {bn}/{tb}] Processing {len(batch)} stocks...")

        for ticker in batch:
            sid = ticker.replace(".TW", "")
            try:
                stock = yf.Ticker(ticker)
                info = stock.info or {}

                price = (info.get("regularMarketPrice")
                         or info.get("currentPrice")
                         or info.get("previousClose") or 0)
                if not price:
                    log(f"{sid} - no price data")
                    continue

                market_cap = info.get("marketCap", 0) or 0
                volume = info.get("regularMarketVolume", 0) or 0

                # L1: Basic filters
                if market_cap > 0 and market_cap < 5_000_000_000:
                    log(f"{sid} - market cap < 50B ({market_cap/1e9:.0f})")
                    continue
                if volume < 1_000_000:
                    log(f"{sid} - volume < 1M ({volume/1e6:.1f}M)")
                    continue
                if "KY" in sid:
                    log(f"{sid} - KY stock")
                    continue

                # Get price history
                hist = stock.history(period="65d", auto_adjust=True)
                if hist.empty or len(hist) < 30:
                    log(f"{sid} - insufficient history")
                    continue

                closes = hist["Close"].tolist()
                price_actual = round(closes[-1], 2)

                # L1: Price < 100
                if price_actual > 100:
                    log(f"{sid} - price ${price_actual} > 100")
                    continue

                # Technical analysis
                rsi = calc_rsi(closes)
                ma20 = np.mean(closes[-20:]) if len(closes) >= 20 else closes[-1]
                momentum = ((closes[-1] - closes[-20]) / closes[-20] * 100) if len(closes) >= 21 else 0
                ma_dev = abs(price_actual - ma20) / ma20 * 100 if ma20 else 0

                # L3: Technical filters (relaxed)
                if not (25 <= rsi <= 75):
                    log(f"{sid} - RSI={rsi} out of range")
                    continue
                if ma_dev > 15:
                    log(f"{sid} - MA deviation {ma_dev:.1f}% > 15%")
                    continue
                if momentum < -20:
                    log(f"{sid} - momentum {momentum:.1f}% < -20%")
                    continue

                if price_actual < ma20 * 0.97:
                    ma_status = "MA20下方"
                elif price_actual > ma20 * 1.03:
                    ma_status = "MA20上方"
                else:
                    ma_status = "接近MA20"

                # Fundamentals from yfinance
                pe = info.get("trailingPE", 0) or 0
                roe = (info.get("returnOnEquity", 0) or 0) * 100
                op_margin = 0
                rev_yoy = (info.get("revenueGrowth", 0) or 0) * 100

                # Try to compute operating margin
                try:
                    total_rev = info.get("totalRevenue", 0) or 0
                    ebit = info.get("ebit", 0) or 0
                    gross_profit = info.get("grossProfit", 0) or 0
                    operating_exp = info.get("operatingExpenses", 0) or 0
                    if total_rev > 0 and ebit > 0:
                        op_margin = ebit / total_rev * 100
                    elif total_rev > 0 and gross_profit > 0 and operating_exp > 0:
                        op_margin = (gross_profit - operating_exp) / total_rev * 100
                except:
                    pass

                # Financial sector detection
                sector = (info.get("sector") or "").lower()
                industry = (info.get("industry") or "").lower()
                is_financial = any(kw in sector + industry for kw in
                                  ["financial", "bank", "insurance", "securities", "holding"])

                # Debt ratio check (D/E > 49 means debt_ratio > 98%)
                debt_ratio_val = 0
                dte = info.get("debtToEquity")
                if dte is not None and dte > 0:
                    debt_ratio_val = dte / (1 + dte) * 100
                if not is_financial and debt_ratio_val > 98:
                    log(f"{sid} - DebtRatio={debt_ratio_val:.1f}% > 98%")
                    continue

                # L2: Fundamental filters
                if pe != 0 and (pe < 0 or pe > 30):
                    log(f"{sid} - PE={pe:.1f} out of range")
                    continue
                if roe != 0 and roe < 5:
                    log(f"{sid} - ROE={roe:.1f}% < 5%")
                    continue
                if op_margin != 0 and op_margin < 5:
                    log(f"{sid} - OpMargin={op_margin:.1f}% < 5%")
                    continue
                if rev_yoy != 0 and rev_yoy < 5:
                    log(f"{sid} - RevGrowth={rev_yoy:.1f}% < 5%")
                    continue

                name = (info.get("shortName") or info.get("longName") or sid)

                row = {
                    "代號": sid,
                    "名稱": name,
                    "現價": price_actual,
                    "RSI": rsi,
                    "MA狀態": ma_status,
                    "MA20偏離%": round(ma_dev, 1),
                    "營收成長%": round(rev_yoy, 1) if rev_yoy else "N/A",
                    "PE": round(pe, 1) if pe else "N/A",
                    "ROE%": round(roe, 2) if roe else "N/A",
                    "營益率%": round(op_margin, 2) if op_margin else "N/A",
                    "負債比%": round(debt_ratio_val, 1) if debt_ratio_val else "N/A",
                    "市值億": round(market_cap / 1e9, 1) if market_cap else "N/A",
                    "日成交量萬": round(volume / 1e4, 0),
                    "1月動能%": round(momentum, 1),
                    "market_cap": market_cap,
                    "volume": volume,
                    "revenue_yoy": rev_yoy,
                    "pe": pe,
                    "roe": roe,
                    "op_margin": op_margin,
                    "momentum": momentum,
                    "price": price_actual,
                    "ma_status": ma_status,
                }

                row["分數"] = calc_score(row)
                row["訊號"] = get_signal(row["分數"])
                row["備註"] = ""
                results.append(row)

                sig = row["訊號"]
                print(f"  {sid} ${price_actual} RSI={rsi} Rev={rev_yoy:.1f}% PE={pe:.1f if pe else 'N/A'} ROE={roe:.1f if roe else 'N/A'} Score={row['分數']} [{sig}]")

            except Exception as e:
                log(f"{sid} - error: {str(e)[:50]}")
                continue

        print(f"  [batch done] cumulative: {len(results)} passed")
        time.sleep(1.5)

    # Sort and save
    results.sort(key=lambda x: x["分數"] if isinstance(x["分數"], (int, float)) else 0, reverse=True)

    df = pd.DataFrame(results)
    cols = ["代號", "名稱", "現價", "RSI", "MA狀態", "MA20偏離%", "營收成長%", "PE", "ROE%",
            "營益率%", "負債比%", "市值億", "日成交量萬", "1月動能%", "分數", "訊號", "備註"]
    df = df[[c for c in cols if c in df.columns]]
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    now2 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[DONE] {now2}")
    print(f"Total scanned: {total} | Passed: {len(results)} | Pass rate: {len(results)/total*100:.1f}%")
    print(f"Signal distribution: {df['訊號'].value_counts().to_dict()}")

    for sig in ["STRONG BUY", "WATCH", "HOLD", "PASS"]:
        sub = df[df["訊號"] == sig]
        if len(sub) > 0:
            print(f"\n[{sig}] ({len(sub)} stocks):")
            for _, r in sub.iterrows():
                print(f"  {r['代號']} ${r['現價']} | RSI={r['RSI']} | MA偏離={r['MA20偏離%']}% | Rev={r['營收成長%']} | PE={r['PE']} | ROE={r['ROE%']} | Score={r['分數']}")

    print(f"\nOutput: {OUTPUT_FILE}")
    return df


if __name__ == "__main__":
    try:
        df = main()
    except KeyboardInterrupt:
        print("\n[ABORTED]")
        sys.exit(0)