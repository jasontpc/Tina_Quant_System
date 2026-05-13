# -*- coding: utf-8 -*-
"""
Ray Taiwan Stock Backtest - 3-5月 500檔個股
使用 ray_engine 對台股大量個股進行回測
"""

import sqlite3, json, time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 嘗試從 finmind 或 yfinance 取得台股資料
try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    print("[WARNING] yfinance not available")

from ray_engine import RayEngine
from ray_data_center import RayDataCenter

DB_PATH = "ray_wisdom.db"

# 測試區間：2026年3月1日 - 2026年5月12日
START_DATE = "2026-03-01"
END_DATE   = "2026-05-12"
LOOKBACK   = "120d"  # 往前抓120天足夠計算指標

# 台股主要個股（示範用TOP 50 - 可擴充到500）
# 實際使用時應串接 FinMind 或 TejAPI 取得完整名單
SAMPLE_TAIWAN_STOCKS = [
    "2330.TW", "2454.TW", "2317.TW", "2303.TW", "2382.TW",
    "3008.TW", "2412.TW", "3711.TW", "2451.TW", "2327.TW",
    "2881.TW", "2882.TW", "2883.TW", "2884.TW", "2885.TW",
    "2308.TW", "2344.TW", "2301.TW", "2371.TW", "2395.TW",
    "2353.TW", "2354.TW", "2360.TW", "2362.TW", "2377.TW",
    "2474.TW", "2498.TW", "2504.TW", "2542.TW", "2603.TW",
    "2609.TW", "2615.TW", "2618.TW", "2624.TW", "2633.TW",
    "2801.TW", "2812.TW", "2823.TW", "2834.TW", "2855.TW",
    "2886.TW", "2887.TW", "2890.TW", "2891.TW", "2892.TW",
    "4938.TW", "4958.TW", "4961.TW", "4974.TW", "4985.TW",
]

# 全量台股代碼池（500檔，可擴充）
TAIWAN_STOCK_POOL = [
    # 半導體
    "2330.TW","2454.TW","2303.TW","2382.TW","2344.TW","2379.TW","2401.TW","2376.TW","2377.TW","2360.TW",
    "2395.TW","2474.TW","2308.TW","2301.TW","2317.TW","2327.TW","2332.TW","2345.TW","2353.TW","2362.TW",
    "2371.TW","2378.TW","2383.TW","2385.TW","2387.TW","2392.TW","2408.TW","2412.TW","2420.TW","2421.TW",
    "2431.TW","2433.TW","2441.TW","2448.TW","2451.TW","2453.TW","2455.TW","2456.TW","2457.TW","2458.TW",
    # 電子零組件
    "2317.TW","2327.TW","2332.TW","2344.TW","2353.TW","2354.TW","2356.TW","2362.TW","2371.TW","2373.TW",
    "2376.TW","2377.TW","2379.TW","2382.TW","2383.TW","2385.TW","2395.TW","2401.TW","2408.TW","2412.TW",
    # 電腦及周邊
    "2324.TW","2352.TW","2353.TW","2367.TW","2368.TW","2373.TW","2385.TW","2392.TW","2395.TW","2404.TW",
    "2408.TW","2412.TW","2420.TW","2421.TW","2425.TW","2426.TW","2427.TW","2428.TW","2429.TW","2431.TW",
    # 通信網路
    "2317.TW","2324.TW","2344.TW","2353.TW","2377.TW","2383.TW","2385.TW","2392.TW","2395.TW","2401.TW",
    # 光電
    "2468.TW","2474.TW","2481.TW","2498.TW","3008.TW","3014.TW","3017.TW","3018.TW","3019.TW","3022.TW",
    # 軟體服務
    "3022.TW","3024.TW","3025.TW","3026.TW","3027.TW","3028.TW","3029.TW","3030.TW","3031.TW","3032.TW",
    # 其他電子
    "3033.TW","3034.TW","3035.TW","3036.TW","3037.TW","3038.TW","3039.TW","3040.TW","3041.TW","3042.TW",
    # 金融
    "2801.TW","2812.TW","2823.TW","2834.TW","2855.TW","2880.TW","2881.TW","2882.TW","2883.TW","2884.TW",
    "2885.TW","2886.TW","2887.TW","2890.TW","2891.TW","2892.TW","2893.TW","2894.TW","2895.TW","2896.TW",
    # 壽險/金控
    "2881.TW","2882.TW","2883.TW","2884.TW","2885.TW","2886.TW","2887.TW","2890.TW","2891.TW","2892.TW",
    # 營建
    "2504.TW","2515.TW","2520.TW","2524.TW","2527.TW","2528.TW","2530.TW","2534.TW","2535.TW","2537.TW",
    "2538.TW","2539.TW","2542.TW","2543.TW","2545.TW","2547.TW","2548.TW","2552.TW","2553.TW","2554.TW",
    # 航運
    "2603.TW","2609.TW","2610.TW","2611.TW","2612.TW","2613.TW","2615.TW","2617.TW","2618.TW","2624.TW",
    "2630.TW","2633.TW","2634.TW","2635.TW","2636.TW","2637.TW","2638.TW","2639.TW","2640.TW","2641.TW",
    # 鋼鐵/DRAM
    "2002.TW","2006.TW","2009.TW","2010.TW","2012.TW","2014.TW","2015.TW","2017.TW","2020.TW","2022.TW",
    "2023.TW","2024.TW","2027.TW","2028.TW","2029.TW","2030.TW","2031.TW","2032.TW","2033.TW","2034.TW",
    # 傳產
    "1101.TW","1102.TW","1103.TW","1104.TW","1105.TW","1108.TW","1109.TW","1110.TW","1201.TW","1203.TW",
    "1215.TW","1216.TW","1217.TW","1218.TW","1219.TW","1220.TW","1225.TW","1227.TW","1229.TW","1231.TW",
    "1232.TW","1233.TW","1234.TW","1235.TW","1236.TW","1237.TW","1238.TW","1239.TW","1240.TW","1241.TW",
    # 紡織
    "1402.TW","1413.TW","1414.TW","1417.TW","1418.TW","1423.TW","1434.TW","1435.TW","1437.TW","1438.TW",
    # 化學/生技
    "1301.TW","1303.TW","1304.TW","1305.TW","1308.TW","1312.TW","1313.TW","1314.TW","1319.TW","1321.TW",
    "1323.TW","1324.TW","1325.TW","1326.TW","1327.TW","1328.TW","1329.TW","1330.TW","1331.TW","1332.TW",
    "1333.TW","1334.TW","1335.TW","1336.TW","1337.TW","1338.TW","1339.TW","1340.TW","1341.TW","1342.TW",
    # 油電
    "1503.TW","1504.TW","1506.TW","1507.TW","1512.TW","1513.TW","1514.TW","1515.TW","1516.TW","1517.TW",
    # 其他
    "1605.TW","1702.TW","1704.TW","1707.TW","1708.TW","1709.TW","1710.TW","1711.TW","1712.TW","1713.TW",
    "1802.TW","1805.TW","1806.TW","1807.TW","1808.TW","1809.TW","1810.TW","1812.TW","1813.TW","1814.TW",
    "1903.TW","1904.TW","1905.TW","1906.TW","1907.TW","1908.TW","1909.TW","1910.TW","1911.TW","1912.TW",
    "1913.TW","1914.TW","1915.TW","1916.TW","1917.TW","1918.TW","1919.TW","1920.TW","1921.TW","1922.TW",
    "1923.TW","1924.TW","1925.TW","1926.TW","1927.TW","1928.TW","1929.TW","1930.TW","1931.TW","1932.TW",
    "1933.TW","1934.TW","1935.TW","1936.TW","1937.TW","1938.TW","1939.TW","1940.TW","1941.TW","1942.TW",
    "1943.TW","1944.TW","1945.TW","1946.TW","1947.TW","1948.TW","1949.TW","1950.TW","1951.TW","1952.TW",
    "1953.TW","1954.TW","1955.TW","1956.TW","1957.TW","1958.TW","1959.TW","1960.TW","1961.TW","1962.TW",
    "1963.TW","1964.TW","1965.TW","1966.TW","1967.TW","1968.TW","1969.TW","1970.TW","1971.TW","1972.TW",
    "1973.TW","1974.TW","1975.TW","1976.TW","1977.TW","1978.TW","1979.TW","1980.TW","1981.TW","1982.TW",
    "1983.TW","1984.TW","1985.TW","1986.TW","1987.TW","1988.TW","1989.TW","1990.TW","1991.TW","1992.TW",
    "1993.TW","1994.TW","1995.TW","1996.TW","1997.TW","1998.TW","1999.TW","2001.TW","2002.TW","2003.TW",
    "2004.TW","2005.TW","2006.TW","2007.TW","2008.TW","2009.TW","2010.TW","2011.TW","2012.TW","2013.TW",
    "2014.TW","2015.TW","2016.TW","2017.TW","2018.TW","2019.TW","2020.TW","2021.TW","2022.TW","2023.TW",
    "2024.TW","2025.TW","2026.TW","2027.TW","2028.TW","2029.TW","2030.TW","2031.TW","2032.TW","2033.TW",
    "2034.TW","2035.TW","2036.TW","2037.TW","2038.TW","2039.TW","2040.TW","2041.TW","2042.TW","2043.TW",
    "2044.TW","2045.TW","2046.TW","2047.TW","2048.TW","2049.TW","2050.TW","2051.TW","2052.TW","2053.TW",
    "2054.TW","2055.TW","2056.TW","2057.TW","2058.TW","2059.TW","2060.TW","2061.TW","2062.TW","2063.TW",
    "2064.TW","2065.TW","2066.TW","2067.TW","2068.TW","2069.TW","2070.TW","2071.TW","2072.TW","2073.TW",
    "2074.TW","2075.TW","2076.TW","2077.TW","2078.TW","2079.TW","2080.TW","2081.TW","2082.TW","2083.TW",
    "2084.TW","2085.TW","2086.TW","2087.TW","2088.TW","2089.TW","2090.TW","2091.TW","2092.TW","2093.TW",
    "2094.TW","2095.TW","2096.TW","2097.TW","2098.TW","2099.TW","2100.TW","2101.TW","2102.TW","2103.TW",
    "2104.TW","2105.TW","2106.TW","2107.TW","2108.TW","2109.TW","2110.TW","2111.TW","2112.TW","2113.TW",
    "2114.TW","2115.TW","2116.TW","2117.TW","2118.TW","2119.TW","2120.TW","2121.TW","2122.TW","2123.TW",
    "2124.TW","2125.TW","2126.TW","2127.TW","2128.TW","2129.TW","2130.TW","2131.TW","2132.TW","2133.TW",
    "2134.TW","2135.TW","2136.TW","2137.TW","2138.TW","2139.TW","2140.TW","2141.TW","2142.TW","2143.TW",
    "2144.TW","2145.TW","2146.TW","2147.TW","2148.TW","2149.TW","2150.TW","2151.TW","2152.TW","2153.TW",
    "2154.TW","2155.TW","2156.TW","2157.TW","2158.TW","2159.TW","2160.TW","2161.TW","2162.TW","2163.TW",
    "2164.TW","2165.TW","2166.TW","2167.TW","2168.TW","2169.TW","2170.TW","2171.TW","2172.TW","2173.TW",
    "2174.TW","2175.TW","2176.TW","2177.TW","2178.TW","2179.TW","2180.TW","2181.TW","2182.TW","2183.TW",
    "2184.TW","2185.TW","2186.TW","2187.TW","2188.TW","2189.TW","2190.TW","2191.TW","2192.TW","2193.TW",
    "2194.TW","2195.TW","2196.TW","2197.TW","2198.TW","2199.TW","2200.TW","2201.TW","2202.TW","2203.TW",
    "2204.TW","2205.TW","2206.TW","2207.TW","2208.TW","2209.TW","2210.TW","2211.TW","2212.TW","2213.TW",
    "2214.TW","2215.TW","2216.TW","2217.TW","2218.TW","2219.TW","2220.TW","2221.TW","2222.TW","2223.TW",
    "2224.TW","2225.TW","2226.TW","2227.TW","2228.TW","2229.TW","2230.TW","2231.TW","2232.TW","2233.TW",
    "2234.TW","2235.TW","2236.TW","2237.TW","2238.TW","2239.TW","2240.TW","2241.TW","2242.TW","2243.TW",
    "2244.TW","2245.TW","2246.TW","2247.TW","2248.TW","2249.TW","2250.TW","2251.TW","2252.TW","2253.TW",
    "2254.TW","2255.TW","2256.TW","2257.TW","2258.TW","2259.TW","2260.TW","2261.TW","2262.TW","2263.TW",
    "2264.TW","2265.TW","2266.TW","2267.TW","2268.TW","2269.TW","2270.TW","2271.TW","2272.TW","2273.TW",
    "2274.TW","2275.TW","2276.TW","2277.TW","2278.TW","2279.TW","2280.TW","2281.TW","2282.TW","2283.TW",
    "2284.TW","2285.TW","2286.TW","2287.TW","2288.TW","2289.TW","2290.TW","2291.TW","2292.TW","2293.TW",
]

# 移除重複
TAIWAN_STOCK_POOL = list(set(TAIWAN_STOCK_POOL))
print(f"Total pool: {len(TAIWAN_STOCK_POOL)} stocks")


# 回測策略候選（針對台股調整）
STRATEGIES = [
    # 均線交叉
    {"strategy_name": "EMA_CROSS_5_20",   "indicator": "EMA_CROSS",   "params": {"fast": 5,  "slow": 20},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08},
    {"strategy_name": "EMA_CROSS_10_30",  "indicator": "EMA_CROSS",   "params": {"fast": 10, "slow": 30},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.08},
    {"strategy_name": "EMA_CROSS_20_60",  "indicator": "EMA_CROSS",   "params": {"fast": 20, "slow": 60},  "entry_condition": {"operator": "CROSS_ABOVE", "threshold": 0}, "stop_loss": 0.10},
    # 動能
    {"strategy_name": "MOMENTUM_5",        "indicator": "MOMENTUM",     "params": {"window": 5},           "entry_condition": {"operator": ">", "threshold": 0.03}, "stop_loss": 0.10},
    {"strategy_name": "MOMENTUM_20",       "indicator": "MOMENTUM",     "params": {"window": 20},          "entry_condition": {"operator": ">", "threshold": 0.05}, "stop_loss": 0.08},
    # RSI 超跌反彈（康諾斯）
    {"strategy_name": "RSI2_CONNORS",      "indicator": "RSI2",         "params": {"period": 2},          "entry_condition": {"operator": "<", "threshold": 20},  "stop_loss": 0.08},
    {"strategy_name": "RSI_14_OVER",      "indicator": "RSI",          "params": {"period": 14},         "entry_condition": {"operator": "<", "threshold": 30},  "stop_loss": 0.08},
]


def run_taiwan_backtest(symbols, max_stocks=500, write_db=True):
    """
    對台股清單進行批量回測
    """
    engine = RayEngine(market_type="TW")  # 台股 0.54% 摩擦成本
    engine.SHARPE_MIN = 0.5  # 台股門檻放寬（短線波動大）
    engine.MDD_MAX    = 0.25  # MDD < 25%
    engine.WIN_MIN    = 0.35

    db = RayDataCenter(DB_PATH) if write_db else None
    results = []
    passed_all = []
    errors = []

    symbols_to_test = symbols[:max_stocks]
    total = len(symbols_to_test)
    t0 = time.time()

    for i, sym in enumerate(symbols_to_test):
        # 移除 .TW suffix 給 DB 用
        plain_sym = sym.replace(".TW", "")

        if i % 20 == 0:
            elapsed = time.time() - t0
            eta = (elapsed / max(i, 1)) * (total - i) if i > 0 else 0
            print(f"[{i}/{total}] {sym} | ETA: {eta/60:.1f}min | Passed: {len(passed_all)}")

        try:
            df = yf.Ticker(sym).history(period=LOOKBACK, interval="1d", auto_adjust=True)
            if df is None or len(df) < 60:
                errors.append({"symbol": plain_sym, "reason": "insufficient data"})
                continue

            stock_passed = []
            for strat in STRATEGIES:
                try:
                    report = engine.run_backtest(df, strat)

                    if write_db and db:
                        backtest_id = db.log_backtest(
                            strategy_name=strat["strategy_name"],
                            symbol=plain_sym,
                            indicator=strat["indicator"],
                            params=strat["params"],
                            sharpe=report.get("sharpe", 0),
                            mdd=report.get("mdd", 999),
                            total_ret=report.get("total_ret", 0),
                            win_rate=report.get("win_rate", 0),
                            avg_return=report.get("avg_return", 0),
                            num_trades=report.get("num_trades", 0),
                            note=f"TW_3-5M | {report.get('reason','')}",
                        )
                        db.log_wisdom(
                            axiom_json=json.dumps(strat),
                            reflection=f"{'PASSED' if report['passed'] else 'FAILED'} sharpe={report.get('sharpe',0):.2f} mdd={report.get('mdd',0):.2%} win={report.get('win_rate',0):.1%}",
                            backtest_id=backtest_id if report["passed"] else None,
                            passed=report["passed"],
                            model_used="ray_engine",
                        )

                    if report["passed"]:
                        stock_passed.append({**report, "strategy": strat["strategy_name"], "symbol": plain_sym})
                except Exception as e:
                    pass

            if stock_passed:
                best = sorted(stock_passed, key=lambda x: -x["sharpe"])[0]
                passed_all.append(best)
                results.append({
                    "symbol": plain_sym,
                    "passed_strategies": len(stock_passed),
                    "best_strategy": best["strategy"],
                    "sharpe": best["sharpe"],
                    "mdd": best["mdd"],
                    "win_rate": best["win_rate"],
                    "num_trades": best["num_trades"],
                })

        except Exception as e:
            errors.append({"symbol": plain_sym, "reason": str(e)[:80]})

    total_time = time.time() - t0
    print(f"\n=== 台股回測完成 ===")
    print(f"測試個股: {total}")
    print(f"成功回測: {len(results)}")
    print(f"通過策略: {len(passed_all)}")
    print(f"錯誤/無資料: {len(errors)}")
    print(f"總耗时: {total_time/60:.1f} min")

    if passed_all:
        print(f"\n=== TOP 10 黃金策略 ===")
        top10 = sorted(passed_all, key=lambda x: -x["sharpe"])[:10]
        print(f"{'Symbol':<10} {'Strategy':<20} {'Sharpe':<8} {'MDD':<8} {'Win%':<8} {'Trades'}")
        for r in top10:
            print(f"{r['symbol']:<10} {r['strategy']:<20} {r['sharpe']:<8.2f} {r['mdd']:<8.2%} {r['win_rate']:<8.1%} {r['num_trades']}")

    return results, passed_all, errors


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=500, help="最大測試檔數")
    parser.add_argument("--sample", type=int, default=None, help="只測試N檔（快速測試）")
    args = parser.parse_args()

    stocks = TAIWAN_STOCK_POOL[:args.max]
    if args.sample:
        stocks = stocks[:args.sample]
        print(f"[Sample mode] Testing {args.sample} stocks...")

    print(f"[Taiwan Backtest] {len(stocks)} stocks | Period: {LOOKBACK} | Strategies: {len(STRATEGIES)}")
    results, passed, errors = run_taiwan_backtest(stocks, max_stocks=len(stocks))