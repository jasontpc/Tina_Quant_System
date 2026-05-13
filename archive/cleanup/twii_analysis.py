import sys, numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import yfinance as yf
from datetime import datetime

print("=== 台股即時分析 ===")
print(f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# TWII 台灣加權指數
print("[1] 台灣加權指數 (TWII)")
twii = yf.Ticker("^TWII")
hist = twii.history(period="5d", interval="1d")

if len(hist) < 1:
    print("  ❌ 無法取得數據")
else:
    price = float(hist["Close"].iloc[-1])
    prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
    change = (price - prev) / prev * 100
    high = float(hist["High"].iloc[-1])
    low = float(hist["Low"].iloc[-1])
    vol = float(hist["Volume"].iloc[-1])
    print(f"  最新日期：{hist.index[-1].strftime('%Y-%m-%d')}")
    print(f"  現價：{price:.2f}")
    print(f"  漲跌：{change:+.2f}%")
    print(f"  區間：{low:.2f} - {high:.2f}")
    print(f"  成交量：{vol/1e6:.1f}M")

print()

if len(hist) >= 30:
    close = hist["Close"].values.astype(float)
    high_arr = hist["High"].values.astype(float)
    low_arr = hist["Low"].values.astype(float)

    # MA
    ma5 = float(np.mean(close[-5:]))
    ma10 = float(np.mean(close[-10:]))
    ma20 = float(np.mean(close[-20:]))
    ma60 = float(np.mean(close[-60:])) if len(close) >= 60 else float(np.mean(close[-20:]))

    print("[2] 移動平均線")
    print(f"  MA5:  {ma5:.2f}")
    print(f"  MA10: {ma10:.2f}")
    print(f"  MA20: {ma20:.2f}")
    print(f"  MA60: {ma60:.2f}")
    print()

    # MACD
    def ema_arr(arr, n):
        k = 2/(n+1)
        result = [arr[0]]
        for x in arr[1:]:
            result.append(x*k + result[-1]*(1-k))
        return np.array(result)

    ema12 = ema_arr(close, 12)
    ema26 = ema_arr(close, 26)
    macd_line = ema12 - ema26
    signal_line = ema_arr(macd_line, 9)
    macd_hist = float(macd_line[-1] - signal_line[-1])

    print("[3] MACD")
    print(f"  MACD: {macd_line[-1]:.4f}")
    print(f"  Signal: {signal_line[-1]:.4f}")
    print(f"  Hist: {macd_hist:.4f} ({'多頭' if macd_hist > 0 else '空頭'})")
    print()

    # KDJ
    n = 9
    k_vals = [50.0] * n
    d_vals = [50.0] * n
    for i in range(n, len(close)):
        h = float(np.max(high_arr[i-n:i+1]))
        l = float(np.min(low_arr[i-n:i+1]))
        rsv = 100 * (close[i] - l) / (h - l) if h != l else 50.0
        k_vals.append(rsv)
        d_vals.append(np.mean(k_vals[-9:]))
    kdj_k = float(k_vals[-1])
    kdj_d = float(d_vals[-1])
    kdj_j = float(3 * kdj_k - 2 * kdj_d)

    print("[4] KDJ")
    print(f"  K: {kdj_k:.2f}")
    print(f"  D: {kdj_d:.2f}")
    print(f"  J: {kdj_j:.2f}")
    print()

    # RSI
    delta = np.diff(close)
    up = np.maximum(delta, 0)
    down = np.maximum(-delta, 0)
    rs_up = float(np.convolve(up, np.ones(14)/14, mode='same')[-1])
    rs_down = float(np.convolve(down, np.ones(14)/14, mode='same')[-1])
    rsi = 100 - 100 / (1 + rs_up / rs_down) if rs_down > 0 else 50.0

    print("[5] RSI(14)")
    print(f"  RSI: {rsi:.2f}")
    print()

    # 綜合訊號
    print("[6] 綜合訊號")
    above_ma20 = price > ma20
    above_ma60 = price > ma60
    macd_bull = macd_hist > 0
    kdj_bull = kdj_j > 50

    print(f"  價格 > MA20: {'✅' if above_ma20 else '❌'} ({price:.2f} vs {ma20:.2f})")
    print(f"  價格 > MA60: {'✅' if above_ma60 else '❌'} ({price:.2f} vs {ma60:.2f})")
    print(f"  MACD 多頭: {'✅' if macd_bull else '❌'} (hist={macd_hist:.4f})")
    print(f"  KDJ 多頭: {'✅' if kdj_bull else '❌'} (J={kdj_j:.2f})")
    print(f"  RSI: {rsi:.2f} ({'超買' if rsi > 70 else '超賣' if rsi < 30 else '中性'})")

    score = sum([above_ma20, above_ma60, macd_bull, kdj_bull, rsi < 70])
    print()
    print(f"  多空評分：{score}/5")

    if score >= 4:
        rec = "🟢 偏多操作"
    elif score >= 3:
        rec = "🟡 中性偏多"
    elif score >= 2:
        rec = "🟡 中性偏空"
    else:
        rec = "🔴 偏空操作"

    print(f"  操作建議：{rec}")
    print()

    # 美股影響評估
    print("[7] 美股對台股影響")
    try:
        spy = yf.Ticker("SPY").history(period="2d", interval="1d")
        if len(spy) >= 1:
            spy_price = float(spy["Close"].iloc[-1])
            spy_prev = float(spy["Close"].iloc[-2]) if len(spy) >= 2 else spy_price
            spy_change = (spy_price - spy_prev) / spy_prev * 100
            print(f"  SPY: {spy_price:.2f} ({spy_change:+.2f}%)")
            if spy_change > 0.5:
                print(f"  美股偏多 → 台股有機會跟漲")
            elif spy_change < -0.5:
                print(f"  美股偏空 → 台股留意壓力")
            else:
                print(f"  美股平盤 → 台股觀望")
    except:
        print("  SPY: 無法取得數據")

    print()
    print("=== 建議摘要 ===")
    if rsi > 80:
        print("⚠️  RSI 超買，建議觀望或少量操作")
    elif rsi < 30:
        print("📌 RSI 超賣，可留意反彈機會")
    else:
        print("📌 RSI 中性，謹慎操作")

    if not above_ma20:
        print("⚠️  價格跌破 MA20，技術面偏弱")
    elif not above_ma60:
        print("📌 價格在 MA20-MA60 之間，中性整理")
    else:
        print("✅ 價格站穩均線，技術面偏強")

    if kdj_j < 20:
        print("📌 KDJ 超賣區，低點反彈機會")
    elif kdj_j > 80:
        print("📌 KDJ 超買區，慎防回調")