# -*- coding: utf-8 -*-
"""
ray_backtest_tw500.py — 回測台股 500 檔
"""
import sys, sqlite3, json, time, logging
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import yfinance as yf
import numpy as np

DB = 'ray_wisdom.db'
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_log = logging.getLogger("tw500")
_log.setLevel(logging.INFO)
if not _log.handlers:
    h = logging.FileHandler(str(LOG_DIR / "tw500.log"), encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _log.addHandler(h)

print("=== 台股 500 檔回測 ===")
print()

# 台股主要股票代碼（500檔）
TW_STOCKS = [
    # 2330 系列
    "2330.TW", "2331.TW", "2332.TW", "2333.TW", "2334.TW", "2335.TW", "2336.TW", "2337.TW", "2338.TW", "2339.TW",
    "2340.TW", "2341.TW", "2342.TW", "2343.TW", "2344.TW", "2345.TW", "2346.TW", "2347.TW", "2348.TW", "2349.TW",
    "2350.TW", "2351.TW", "2352.TW", "2353.TW", "2354.TW", "2355.TW", "2356.TW", "2357.TW", "2358.TW", "2359.TW",
    "2360.TW", "2361.TW", "2362.TW", "2363.TW", "2364.TW", "2365.TW", "2366.TW", "2367.TW", "2368.TW", "2369.TW",
    "2370.TW", "2371.TW", "2372.TW", "2373.TW", "2374.TW", "2375.TW", "2376.TW", "2377.TW", "2378.TW", "2379.TW",
    "2380.TW", "2381.TW", "2382.TW", "2383.TW", "2384.TW", "2385.TW", "2386.TW", "2387.TW", "2388.TW", "2389.TW",
    "2390.TW", "2391.TW", "2392.TW", "2393.TW", "2394.TW", "2395.TW", "2396.TW", "2397.TW", "2398.TW", "2399.TW",
    "2400.TW", "2401.TW", "2402.TW", "2403.TW", "2404.TW", "2405.TW", "2406.TW", "2407.TW", "2408.TW", "2409.TW",
    "2410.TW", "2411.TW", "2412.TW", "2413.TW", "2414.TW", "2415.TW", "2416.TW", "2417.TW", "2418.TW", "2419.TW",
    "2420.TW", "2421.TW", "2422.TW", "2423.TW", "2424.TW", "2425.TW", "2426.TW", "2427.TW", "2428.TW", "2429.TW",
    "2430.TW", "2431.TW", "2432.TW", "2433.TW", "2434.TW", "2435.TW", "2436.TW", "2437.TW", "2438.TW", "2439.TW",
    "2440.TW", "2441.TW", "2442.TW", "2443.TW", "2444.TW", "2445.TW", "2446.TW", "2447.TW", "2448.TW", "2449.TW",
    "2450.TW", "2451.TW", "2452.TW", "2453.TW", "2454.TW", "2455.TW", "2456.TW", "2457.TW", "2458.TW", "2459.TW",
    "2460.TW", "2461.TW", "2462.TW", "2463.TW", "2464.TW", "2465.TW", "2466.TW", "2467.TW", "2468.TW", "2469.TW",
    "2470.TW", "2471.TW", "2472.TW", "2473.TW", "2474.TW", "2475.TW", "2476.TW", "2477.TW", "2478.TW", "2479.TW",
    "2480.TW", "2481.TW", "2482.TW", "2483.TW", "2484.TW", "2485.TW", "2486.TW", "2487.TW", "2488.TW", "2489.TW",
    "2490.TW", "2491.TW", "2492.TW", "2493.TW", "2494.TW", "2495.TW", "2496.TW", "2497.TW", "2498.TW", "2499.TW",
    "2500.TW", "2501.TW", "2502.TW", "2503.TW", "2504.TW", "2505.TW", "2506.TW", "2507.TW", "2508.TW", "2509.TW",
    "2510.TW", "2511.TW", "2512.TW", "2513.TW", "2514.TW", "2515.TW", "2516.TW", "2517.TW", "2518.TW", "2519.TW",
    "2520.TW", "2521.TW", "2522.TW", "2523.TW", "2524.TW", "2525.TW", "2526.TW", "2527.TW", "2528.TW", "2529.TW",
    "2530.TW", "2531.TW", "2532.TW", "2533.TW", "2534.TW", "2535.TW", "2536.TW", "2537.TW", "2538.TW", "2539.TW",
    "2540.TW", "2541.TW", "2542.TW", "2543.TW", "2544.TW", "2545.TW", "2546.TW", "2547.TW", "2548.TW", "2549.TW",
    "2550.TW", "2551.TW", "2552.TW", "2553.TW", "2554.TW", "2555.TW", "2556.TW", "2557.TW", "2558.TW", "2559.TW",
    "2560.TW", "2561.TW", "2562.TW", "2563.TW", "2564.TW", "2565.TW", "2566.TW", "2567.TW", "2568.TW", "2569.TW",
    "2570.TW", "2571.TW", "2572.TW", "2573.TW", "2574.TW", "2575.TW", "2576.TW", "2577.TW", "2578.TW", "2579.TW",
    "2580.TW", "2581.TW", "2582.TW", "2583.TW", "2584.TW", "2585.TW", "2586.TW", "2587.TW", "2588.TW", "2589.TW",
    "2590.TW", "2591.TW", "2592.TW", "2593.TW", "2594.TW", "2595.TW", "2596.TW", "2597.TW", "2598.TW", "2599.TW",
    "2600.TW", "2601.TW", "2602.TW", "2603.TW", "2604.TW", "2605.TW", "2606.TW", "2607.TW", "2608.TW", "2609.TW",
    "2610.TW", "2611.TW", "2612.TW", "2613.TW", "2614.TW", "2615.TW", "2616.TW", "2617.TW", "2618.TW", "2619.TW",
    "2620.TW", "2621.TW", "2622.TW", "2623.TW", "2624.TW", "2625.TW", "2626.TW", "2627.TW", "2628.TW", "2629.TW",
    "2630.TW", "2631.TW", "2632.TW", "2633.TW", "2634.TW", "2635.TW", "2636.TW", "2637.TW", "2638.TW", "2639.TW",
    "2640.TW", "2641.TW", "2642.TW", "2643.TW", "2644.TW", "2645.TW", "2646.TW", "2647.TW", "2648.TW", "2649.TW",
    "2650.TW", "2651.TW", "2652.TW", "2653.TW", "2654.TW", "2655.TW", "2656.TW", "2657.TW", "2658.TW", "2659.TW",
    "2660.TW", "2661.TW", "2662.TW", "2663.TW", "2664.TW", "2665.TW", "2666.TW", "2667.TW", "2668.TW", "2669.TW",
    "2670.TW", "2671.TW", "2672.TW", "2673.TW", "2674.TW", "2675.TW", "2676.TW", "2677.TW", "2678.TW", "2679.TW",
    "2680.TW", "2681.TW", "2682.TW", "2683.TW", "2684.TW", "2685.TW", "2686.TW", "2687.TW", "2688.TW", "2689.TW",
    "2690.TW", "2691.TW", "2692.TW", "2693.TW", "2694.TW", "2695.TW", "2696.TW", "2697.TW", "2698.TW", "2699.TW",
    "2700.TW", "2701.TW", "2702.TW", "2703.TW", "2704.TW", "2705.TW", "2706.TW", "2707.TW", "2708.TW", "2709.TW",
    "2710.TW", "2711.TW", "2712.TW", "2713.TW", "2714.TW", "2715.TW", "2716.TW", "2717.TW", "2718.TW", "2719.TW",
    "2720.TW", "2721.TW", "2722.TW", "2723.TW", "2724.TW", "2725.TW", "2726.TW", "2727.TW", "2728.TW", "2729.TW",
    "2730.TW", "2731.TW", "2732.TW", "2733.TW", "2734.TW", "2735.TW", "2736.TW", "2737.TW", "2738.TW", "2739.TW",
    "2740.TW", "2741.TW", "2742.TW", "2743.TW", "2744.TW", "2745.TW", "2746.TW", "2747.TW", "2748.TW", "2749.TW",
    "2750.TW", "2751.TW", "2752.TW", "2753.TW", "2754.TW", "2755.TW", "2756.TW", "2757.TW", "2758.TW", "2759.TW",
    "2760.TW", "2761.TW", "2762.TW", "2763.TW", "2764.TW", "2765.TW", "2766.TW", "2767.TW", "2768.TW", "2769.TW",
    "2770.TW", "2771.TW", "2772.TW", "2773.TW", "2774.TW", "2775.TW", "2776.TW", "2777.TW", "2778.TW", "2779.TW",
    "2780.TW", "2781.TW", "2782.TW", "2783.TW", "2784.TW", "2785.TW", "2786.TW", "2787.TW", "2788.TW", "2789.TW",
    "2790.TW", "2791.TW", "2792.TW", "2793.TW", "2794.TW", "2795.TW", "2796.TW", "2797.TW", "2798.TW", "2799.TW",
    "2800.TW", "2801.TW", "2802.TW", "2803.TW", "2804.TW", "2805.TW", "2806.TW", "2807.TW", "2808.TW", "2809.TW",
    "2810.TW", "2811.TW", "2812.TW", "2813.TW", "2814.TW", "2815.TW", "2816.TW", "2817.TW", "2818.TW", "2819.TW",
    "2820.TW", "2821.TW", "2822.TW", "2823.TW", "2824.TW", "2825.TW", "2826.TW", "2827.TW", "2828.TW", "2829.TW",
    "2830.TW", "2831.TW", "2832.TW", "2833.TW", "2834.TW", "2835.TW", "2836.TW", "2837.TW", "2838.TW", "2839.TW",
    "2840.TW", "2841.TW", "2842.TW", "2843.TW", "2844.TW", "2845.TW", "2846.TW", "2847.TW", "2848.TW", "2849.TW",
    "2850.TW", "2851.TW", "2852.TW", "2853.TW", "2854.TW", "2855.TW", "2856.TW", "2857.TW", "2858.TW", "2859.TW",
    "2860.TW", "2861.TW", "2862.TW", "2863.TW", "2864.TW", "2865.TW", "2866.TW", "2867.TW", "2868.TW", "2869.TW",
    "2870.TW", "2871.TW", "2872.TW", "2873.TW", "2874.TW", "2875.TW", "2876.TW", "2877.TW", "2878.TW", "2879.TW",
    "2880.TW", "2881.TW", "2882.TW", "2883.TW", "2884.TW", "2885.TW", "2886.TW", "2887.TW", "2888.TW", "2889.TW",
    "2890.TW", "2891.TW", "2892.TW", "2893.TW", "2894.TW", "2895.TW", "2896.TW", "2897.TW", "2898.TW", "2899.TW",
    "2900.TW", "2901.TW", "2902.TW", "2903.TW", "2904.TW", "2905.TW", "2906.TW", "2907.TW", "2908.TW", "2909.TW",
    "2910.TW", "2911.TW", "2912.TW", "2913.TW", "2914.TW", "2915.TW", "2916.TW", "2917.TW", "2918.TW", "2919.TW",
    "2920.TW", "2921.TW", "2922.TW", "2923.TW", "2924.TW", "2925.TW", "2926.TW", "2927.TW", "2928.TW", "2929.TW",
    "2930.TW", "2931.TW", "2932.TW", "2933.TW", "2934.TW", "2935.TW", "2936.TW", "2937.TW", "2938.TW", "2939.TW",
    "2940.TW", "2941.TW", "2942.TW", "2943.TW", "2944.TW", "2945.TW", "2946.TW", "2947.TW", "2948.TW", "2949.TW",
    "2950.TW", "2951.TW", "2952.TW", "2953.TW", "2954.TW", "2955.TW", "2956.TW", "2957.TW", "2958.TW", "2959.TW",
    "3000.TW", "3001.TW", "3002.TW", "3003.TW", "3004.TW", "3005.TW", "3006.TW", "3007.TW", "3008.TW", "3009.TW",
]

# 去重
TW_STOCKS = list(dict.fromkeys(TW_STOCKS))
symbols = TW_STOCKS[:500]
print(f"台股檔數: {len(symbols)}")
print()

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_sharpe(returns):
    if len(returns) < 5 or returns.std() == 0:
        return 0
    return returns.mean() / returns.std() * np.sqrt(252)

def calc_mdd(equity):
    peak = np.maximum.accumulate(equity)
    return abs((equity - peak) / peak).min() * 100

def backtest_one(ticker, start="2024-01-01"):
    try:
        data = yf.download(ticker, start=start, progress=False, timeout=5)
        if data.empty or len(data) < 100:
            return []

        close = data['Close'].dropna().squeeze()
        returns = close.pct_change().dropna()
        mom5 = close.pct_change(5)
        rsi = calc_rsi(close)
        ma20 = close.rolling(20).mean()

        results = []

        # Momentum
        sig = (mom5 > 0) & (close > ma20) & (rsi < 75)
        ret = returns[sig.shift(1).fillna(False)]
        if len(ret) >= 10:
            sh = calc_sharpe(ret)
            if sh > 0:
                eq = (1 + ret).cumprod()
                results.append({
                    "strategy": f"MOM_5_{ticker}",
                    "indicator": "MOMENTUM",
                    "sharpe": sh,
                    "mdd": calc_mdd(eq),
                    "ret": (eq.iloc[-1] - 1) * 100,
                    "win": (ret > 0).sum() / len(ret) * 100,
                    "trades": len(ret)
                })

        # RSI2
        rsi2 = calc_rsi(close, 2)
        sig2 = (rsi2 < 25) & (close > ma20)
        ret2 = returns[sig2.shift(1).fillna(False)]
        if len(ret2) >= 10:
            sh = calc_sharpe(ret2)
            if sh > 0:
                eq = (1 + ret2).cumprod()
                results.append({
                    "strategy": f"RSI2_{ticker}",
                    "indicator": "RSI2",
                    "sharpe": sh,
                    "mdd": calc_mdd(eq),
                    "ret": (eq.iloc[-1] - 1) * 100,
                    "win": (ret2 > 0).sum() / len(ret2) * 100,
                    "trades": len(ret2)
                })

        return results
    except Exception as e:
        return []

def run():
    today = time.strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    c = conn.cursor()

    written = 0
    total = len(symbols)

    for i, ticker in enumerate(symbols):
        if (i + 1) % 50 == 0:
            pct = (i + 1) / total * 100
            print(f"進度: {i+1}/{total} ({pct:.0f}%) - 已寫入 {written} 筆")

        results = backtest_one(ticker)
        for r in results:
            symbol = ticker.replace(".TW", "")
            c.execute(f'''INSERT INTO backtest_reports
                (timestamp, strategy_name, symbol, indicator, params, sharpe_ratio, max_drawdown, total_return, win_rate, avg_return, num_trades, passed, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (today, r["strategy"], symbol, r["indicator"],
                 json.dumps({"ma20": True}),
                 round(r["sharpe"], 2), round(r["mdd"], 2), round(r["ret"], 2),
                 round(r["win"], 1), round(r["ret"] / max(r["trades"], 1), 3),
                 r["trades"], 1 if r["sharpe"] >= 1.5 else 0,
                 "TW500"))
            written += 1

        if (i + 1) % 20 == 0:
            conn.commit()

    conn.commit()
    conn.close()

    conn2 = sqlite3.connect(DB)
    c2 = conn2.cursor()
    c2.execute('SELECT COUNT(*) FROM backtest_reports WHERE symbol LIKE \'%TW\'')
    tw_total = c2.fetchone()[0]
    c2.execute('SELECT COUNT(DISTINCT symbol) FROM backtest_reports WHERE symbol LIKE \'%TW\'')
    tw_unique = c2.fetchone()[0]
    c2.execute('SELECT COUNT(*) FROM backtest_reports WHERE sharpe_ratio >= 1.5 AND symbol LIKE \'%TW\'')
    tw_high = c2.fetchone()[0]
    c2.execute('SELECT symbol, strategy_name, sharpe_ratio, max_drawdown, win_rate FROM backtest_reports WHERE sharpe_ratio >= 1.5 AND symbol LIKE \'%TW\' ORDER BY sharpe_ratio DESC LIMIT 10')
    top10 = c2.fetchall()
    conn2.close()

    print()
    print(f"=== 台股回測完成 ===")
    print(f"寫入: {written} 筆")
    print(f"台股總筆數: {tw_total} 筆")
    print(f"台股獨特檔: {tw_unique} 檔")
    print(f"台股高 Sharpe: {tw_high} 筆")
    print()
    print("Top 10 台股高 Sharpe:")
    for r in top10:
        sym = r[0][:10] if r[0] else "N/A"
        strat = r[1][:20] if r[1] else "N/A"
        print(f"   {sym:<10} {strat:<20} Sharpe:{r[2]:.2f} MDD:{r[3]:.1f}% Win:{r[4]:.1f}%")

    return {"written": written, "tw_total": tw_total, "tw_unique": tw_unique, "tw_high": tw_high}

if __name__ == "__main__":
    run()