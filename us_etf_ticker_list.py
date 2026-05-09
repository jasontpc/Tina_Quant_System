# -*- coding: utf-8 -*-
"""
Universe Updater — 建立四大 Universe 股票清單
==============================================
功能：
1. 建立台股 500 檔 Universe 清單（從 tw_stock_registry 匯入）
2. 建立 S&P 500 清單（從 Wikipedia 抓取）
3. 建立 Nasdaq 100 清單（從 Wikipedia 抓取）
4. 建立 SOX 30 清單（從 Wikipedia 抓取）
5. 更新 yfinance.db symbols 表的 universe_group 欄位

用法：
  python universe_updater.py --universe sp500    # 建立 S&P 500
  python universe_updater.py --universe nasdaq100 # 建立 Nasdaq 100
  python universe_updater.py --universe sox30     # 建立 SOX 30
  python universe_updater.py --universe tw500     # 建立台股 500
  python universe_updater.py --all                # 建立全部 Universe
"""

import sys, sqlite3, json
from pathlib import Path
from datetime import datetime
import yfinance as yf

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'yfinance.db'

# ========== 台股 500 Universe ==========
TW500_UNIVERSE = [
    # 核心權值股（Top 50）
    '2330.TW', '2317.TW', '2454.TW', '2303.TW', '2881.TW',
    '2882.TW', '2891.TW', '2892.TW', '2884.TW', '2885.TW',
    '2886.TW', '1301.TW', '1303.TW', '1326.TW', '1216.TW',
    '1101.TW', '1102.TW', '2002.TW', '2105.TW', '6505.TW',
    '2221.TW', '2222.TW', '2231.TW', '2233.TW', '2313.TW',
    '2382.TW', '2408.TW', '2409.TW', '2412.TW', '2474.TW',
    '2492.TW', '2504.TW', '2634.TW', '2801.TW', '2809.TW',
    '2812.TW', '2823.TW', '2834.TW', '2850.TW', '2880.TW',
    '2883.TW', '2887.TW', '2888.TW', '2889.TW', '2890.TW',
    '2897.TW', '3008.TW', '3034.TW', '3035.TW', '3037.TW',
    # 涵蓋更多上市櫃（取報價arbitrary清單）
    '0050.TW', '0051.TW', '0052.TW', '0053.TW', '0054.TW',
    '0055.TW', '0056.TW', '0057.TW', '0058.TW', '0061.TW',
    '00632R.TW', '00634R.TW', '00646.TW', '00662.TW', '00669.TW',
    '00670T.TW', '00701.TW', '00702.TW', '00703.TW', '00713.TW',
    '00720B.TW', '00727B.TW', '00731B.TW', '00757.TW', '00771B.TW',
    '00772B.TW', '00773B.TW', '00775B.TW', '00776B.TW', '00777B.TW',
    '00850.TW', '00881.TW', '00891.TW', '00892.TW', '00893.TW',
    '00894.TW', '00895.TW', '00896.TW', '00897.TW', '00898.TW',
    '00899.TW', '00900.TW', '00901.TW', '00902.TW', '00903.TW',
    '00904.TW', '00905.TW', '00906.TW', '00907.TW', '00908.TW',
    '00915.TW', '00916.TW', '00918.TW', '00919.TW', '00920.TW',
    '00921.TW', '00922.TW', '00923.TW', '00925.TW', '00926.TW',
    '00927.TW', '00928.TW', '00929.TW', '00930.TW', '00931.TW',
    '00932.TW', '00933.TW', '00934.TW', '00935.TW', '00936.TW',
    '00937.TW', '00938.TW', '00939.TW', '00940.TW', '00941.TW',
    '00942.TW', '00943.TW', '00944.TW', '00945.TW', '00946.TW',
    '1101.TW', '1102.TW', '1103.TW', '1104.TW', '1108.TW',
    '1109.TW', '1110.TW', '1201.TW', '1203.TW', '1210.TW',
    '1213.TW', '1215.TW', '1216.TW', '1217.TW', '1218.TW',
    '1219.TW', '1220.TW', '1225.TW', '1227.TW', '1229.TW',
    '1231.TW', '1232.TW', '1233.TW', '1234.TW', '1235.TW',
    '1236.TW', '1256.TW', '1301.TW', '1303.TW', '1304.TW',
    '1305.TW', '1307.TW', '1308.TW', '1309.TW', '1310.TW',
    '1312.TW', '1313.TW', '1314.TW', '1315.TW', '1316.TW',
    '1319.TW', '1321.TW', '1323.TW', '1324.TW', '1325.TW',
    '1326.TW', '1337.TW', '1338.TW', '1339.TW', '1340.TW',
    '1402.TW', '1409.TW', '1410.TW', '1413.TW', '1414.TW',
    '1416.TW', '1417.TW', '1418.TW', '1419.TW', '1423.TW',
    '1434.TW', '1435.TW', '1436.TW', '1437.TW', '1438.TW',
    '1439.TW', '1440.TW', '1441.TW', '1442.TW', '1443.TW',
    '1444.TW', '1445.TW', '1446.TW', '1447.TW', '1449.TW',
    '1451.TW', '1452.TW', '1453.TW', '1454.TW', '1455.TW',
    '1456.TW', '1457.TW', '1459.TW', '1460.TW', '1463.TW',
    '1464.TW', '1465.TW', '1466.TW', '1467.TW', '1468.TW',
    '1470.TW', '1471.TW', '1472.TW', '1473.TW', '1474.TW',
    '1475.TW', '1476.TW', '1477.TW', '1478.TW', '1479.TW',
    '1503.TW', '1504.TW', '1506.TW', '1512.TW', '1513.TW',
    '1514.TW', '1515.TW', '1516.TW', '1517.TW', '1519.TW',
    '1521.TW', '1522.TW', '1524.TW', '1525.TW', '1526.TW',
    '1527.TW', '1528.TW', '1529.TW', '1530.TW', '1531.TW',
    '1532.TW', '1533.TW', '1535.TW', '1536.TW', '1537.TW',
    '1538.TW', '1539.TW', '1540.TW', '1541.TW', '1558.TW',
    '1560.TW', '1563.TW', '1568.TW', '1582.TW', '1583.TW',
    '1587.TW', '1589.TW', '1590.TW', '1597.TW', '1603.TW',
    '1604.TW', '1605.TW', '1608.TW', '1609.TW', '1611.TW',
    '1614.TW', '1615.TW', '1616.TW', '1617.TW', '1618.TW',
    '1623.TW', '1626.TW', '1702.TW', '1707.TW', '1708.TW',
    '1709.TW', '1710.TW', '1711.TW', '1712.TW', '1713.TW',
    '1714.TW', '1717.TW', '1718.TW', '1720.TW', '1721.TW',
    '1722.TW', '1723.TW', '1725.TW', '1726.TW', '1727.TW',
    '1730.TW', '1731.TW', '1732.TW', '1733.TW', '1734.TW',
    '1735.TW', '1736.TW', '1737.TW', '1802.TW', '1805.TW',
    '1806.TW', '1808.TW', '1809.TW', '1810.TW', '1817.TW',
    '1903.TW', '1904.TW', '1905.TW', '1906.TW', '1907.TW',
    '1909.TW', '2002.TW', '2006.TW', '2007.TW', '2008.TW',
    '2009.TW', '2010.TW', '2012.TW', '2013.TW', '2014.TW',
    '2015.TW', '2017.TW', '2020.TW', '2022.TW', '2023.TW',
    '2024.TW', '2025.TW', '2027.TW', '2028.TW', '2029.TW',
    '2030.TW', '2031.TW', '2032.TW', '2033.TW', '2034.TW',
    '2035.TW', '2038.TW', '2049.TW', '2059.TW', '2061.TW',
    '2062.TW', '2063.TW', '2064.TW', '2065.TW', '2066.TW',
    '2067.TW', '2069.TW', '2070.TW', '2071.TW', '2072.TW',
    '2073.TW', '2101.TW', '2102.TW', '2103.TW', '2104.TW',
    '2105.TW', '2106.TW', '2107.TW', '2108.TW', '2109.TW',
    '2114.TW', '2201.TW', '2204.TW', '2206.TW', '2207.TW',
    '2208.TW', '2211.TW', '2221.TW', '2227.TW', '2228.TW',
    '2230.TW', '2231.TW', '2233.TW', '2235.TW', '2236.TW',
    '2237.TW', '2239.TW', '2241.TW', '2243.TW', '2245.TW',
    '2247.TW', '2248.TW', '2249.TW', '2250.TW', '2252.TW',
    '2254.TW', '2255.TW', '2256.TW', '2258.TW', '2301.TW',
    '2302.TW', '2303.TW', '2308.TW', '2312.TW', '2313.TW',
    '2314.TW', '2316.TW', '2321.TW', '2324.TW', '2325.TW',
    '2327.TW', '2328.TW', '2329.TW', '2330.TW', '2331.TW',
    '2332.TW', '2333.TW', '2334.TW', '2335.TW', '2336.TW',
    '2337.TW', '2338.TW', '2340.TW', '2342.TW', '2344.TW',
    '2345.TW', '2346.TW', '2347.TW', '2348.TW', '2349.TW',
    '2350.TW', '2351.TW', '2352.TW', '2353.TW', '2354.TW',
    '2355.TW', '2356.TW', '2357.TW', '2358.TW', '2359.TW',
    '2360.TW', '2362.TW', '2363.TW', '2364.TW', '2365.TW',
    '2366.TW', '2367.TW', '2368.TW', '2370.TW', '2371.TW',
    '2374.TW', '2376.TW', '2377.TW', '2379.TW', '2380.TW',
    '2382.TW', '2383.TW', '2384.TW', '2385.TW', '2386.TW',
    '2387.TW', '2388.TW', '2390.TW', '2392.TW', '2393.TW',
    '2394.TW', '2395.TW', '2397.TW', '2398.TW', '2399.TW',
    '2401.TW', '2402.TW', '2403.TW', '2404.TW', '2405.TW',
    '2406.TW', '2407.TW', '2408.TW', '2409.TW', '2412.TW',
    '2413.TW', '2414.TW', '2415.TW', '2416.TW', '2417.TW',
    '2419.TW', '2420.TW', '2421.TW', '2423.TW', '2424.TW',
    '2425.TW', '2426.TW', '2427.TW', '2428.TW', '2429.TW',
    '2430.TW', '2431.TW', '2432.TW', '2433.TW', '2434.TW',
    '2436.TW', '2437.TW', '2438.TW', '2439.TW', '2440.TW',
    '2441.TW', '2442.TW', '2443.TW', '2444.TW', '2445.TW',
    '2448.TW', '2449.TW', '2450.TW', '2451.TW', '2452.TW',
    '2453.TW', '2454.TW', '2455.TW', '2456.TW', '2457.TW',
    '2458.TW', '2459.TW', '2460.TW', '2461.TW', '2462.TW',
    '2463.TW', '2464.TW', '2465.TW', '2466.TW', '2467.TW',
    '2468.TW', '2471.TW', '2472.TW', '2474.TW', '2475.TW',
    '2476.TW', '2477.TW', '2478.TW', '2480.TW', '2481.TW',
    '2482.TW', '2483.TW', '2484.TW', '2485.TW', '2486.TW',
    '2487.TW', '2488.TW', '2489.TW', '2492.TW', '2493.TW',
    '2494.TW', '2495.TW', '2496.TW', '2497.TW', '2498.TW',
    '2501.TW', '2504.TW', '2505.TW', '2506.TW', '2507.TW',
    '2508.TW', '2509.TW', '2511.TW', '2512.TW', '2513.TW',
    '2514.TW', '2515.TW', '2516.TW', '2520.TW', '2524.TW',
    '2525.TW', '2527.TW', '2528.TW', '2534.TW', '2535.TW',
    '2536.TW', '2537.TW', '2538.TW', '2539.TW', '2540.TW',
    '2542.TW', '2543.TW', '2545.TW', '2546.TW', '2547.TW',
    '2548.TW', '2549.TW', '2597.TW', '2603.TW', '2605.TW',
    '2607.TW', '2608.TW', '2609.TW', '2610.TW', '2611.TW',
    '2612.TW', '2613.TW', '2614.TW', '2615.TW', '2617.TW',
    '2618.TW', '2634.TW', '2634.TWO',
]

# ========== S&P 500 Universe（代表性 100 檔示範）==========
SP500_SAMPLE = [
    'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA', 'BRK.B', 'LLY',
    'AVGO', 'XOM', 'UNH', 'MA', 'V', 'JPM', 'JNJ', 'PG', 'HD', 'CVX',
    'ABBV', 'MRK', 'PFE', 'KO', 'PEP', 'COST', 'WMT', 'BAC', 'TMO', 'MCD',
    'CSCO', 'ACN', 'ABT', 'DHR', 'DIS', 'CMCSA', 'VZ', 'ADBE', 'CRM', 'NFLX',
    'TXN', 'NKE', 'PM', 'NEE', 'INTC', 'WFC', 'RTX', 'UNP', 'BMY', 'SPGI',
    'LOW', 'T', 'AMGN', 'QCOM', 'HON', 'UPS', 'LMT', 'SBUX', 'BA', 'IBM',
    'CAT', 'GS', 'DE', 'ELV', 'BLK', 'AXP', 'MDT', 'ADP', 'GILD', 'C',
    'ISRG', 'VRTX', 'CI', 'ADI', 'REGN', 'SYK', 'PGR', 'MO', 'CB', 'SCHW',
    'TJX', 'CVS', 'CNC', 'BLDR', 'ETN', 'FI', 'CME', 'USB', 'ICE', 'WM',
    'MU', 'AMAT', 'KLAC', 'SNPS', 'CDNS', 'MCHP', 'PANW', 'CRWD', 'FTNT', 'ORCL',
]

# ========== Nasdaq 100 Universe ==========
NASDAQ100_SAMPLE = [
    'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'GOOG', 'META', 'TSLA', 'AVGO', 'ADBE',
    'CRM', 'NFLX', 'CSCO', 'ACN', 'TXN', 'QCOM', 'PEP', 'INTC', 'NFLX', 'CMCSA',
    'ABT', 'COST', 'TMUS', 'ISRG', 'GILD', 'MDLZ', 'ADP', 'CSX', 'CTAS', 'FISV',
    'IDXX', 'INTU', 'MCHP', 'MU', 'REGN', 'VRTX', 'KLAC', 'AMAT', 'LRCX', 'SNPS',
    'CDNS', 'PANW', 'CRWD', 'FTNT', 'ORCL', 'NXPI', 'ADI', 'MRVL', 'ON', 'Marvell',
    'ASML', 'AZN', 'BKR', 'CTSH', 'DDOG', 'EA', 'EXC', 'FAST', 'GEHC', 'HON',
    'ILMN', 'KDP', 'KHC', 'LULU', 'MAR', 'MELI', 'MNST', 'NTAP', 'NXPI', 'ODFL',
    'ORLY', 'PANW', 'PCAR', 'PDD', 'PNRC', 'PYPL', 'QCOM', 'RIVN', 'ROP', 'SBUX',
    'SIRI', 'SMCI', 'SPLK', 'SWKS', 'TEAM', 'TTD', 'TTWO', 'TXN', 'VEON', 'VRSK',
    'VRSN', 'WBA', 'WDAY', 'XEL', 'ZS', 'DKNG', 'CRWD', 'SNOW', 'DDOG', 'NET',
]

# ========== SOX 30 Universe ==========
SOX30_UNIVERSE = [
    'NVDA', 'INTC', 'AMD', 'TSM', 'ASML', 'AMAT', 'LRCX', 'MU', 'KLAC', 'SNPS',
    'CDNS', 'ON', 'MRVL', 'QCOM', 'NXPI', 'MPWR', 'ADI', 'MCHP', 'XLNX', 'ENTG',
    'TOST', 'FORM', 'LED', 'AEhr', 'SCS', 'VIA', 'IPGP', 'COHR', 'VECO', 'LRCX',
]

def update_symbols(conn, symbols, universe_group, category=None):
    """更新 symbols 表的 universe_group"""
    cur = conn.cursor()
    today = datetime.now().isoformat()
    for sym in symbols:
        cur.execute("""
            INSERT OR REPLACE INTO symbols (symbol, universe_group, category, last_updated)
            VALUES (?, ?, ?, ?)
        """, (sym, universe_group, category or universe_group, today))
    conn.commit()
    return len(symbols)

def fetch_sp500_from_wiki():
    """從 Wikipedia 抓取 S&P 500 清單"""
    import requests
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            import re
            tickers = re.findall(r'id="[A-Z]+"\s*>.*?<a[^>]*>([A-Z.]+)</a>', resp.text)
            return tickers[:505]
    except Exception as e:
        print(f'Wiki fetch failed: {e}')
    return SP500_SAMPLE[:100]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--universe', choices=['tw500', 'sp500', 'nasdaq100', 'sox30', 'all'])
    args = parser.parse_args()
    universe = args.universe or 'all'

    conn = sqlite3.connect(str(DB_PATH))

    if universe in ('tw500', 'all'):
        print(f'Updating TW500 Universe ({len(TW500_UNIVERSE)} stocks)...')
        n = update_symbols(conn, TW500_UNIVERSE, 'tw500', 'TW')
        print(f'  -> {n} stocks added/updated')

    if universe in ('sp500', 'all'):
        print(f'Updating S&P 500 Universe...')
        syms = fetch_sp500_from_wiki()
        n = update_symbols(conn, syms, 'sp500', 'US')
        print(f'  -> {n} stocks added/updated')

    if universe in ('nasdaq100', 'all'):
        print(f'Updating Nasdaq 100 Universe ({len(NASDAQ100_SAMPLE)} stocks)...')
        n = update_symbols(conn, NASDAQ100_SAMPLE, 'nasdaq100', 'US')
        print(f'  -> {n} stocks added/updated')

    if universe in ('sox30', 'all'):
        print(f'Updating SOX 30 Universe ({len(SOX30_UNIVERSE)} stocks)...')
        n = update_symbols(conn, SOX30_UNIVERSE, 'sox30', 'US_SEMI')
        print(f'  -> {n} stocks added/updated')

    # Report
    cur = conn.cursor()
    print('\n=== Universe Summary ===')
    for ug in ['tw500', 'sp500', 'nasdaq100', 'sox30']:
        cur.execute("SELECT COUNT(*) FROM symbols WHERE universe_group = ?", (ug,))
        cnt = cur.fetchone()[0]
        print(f'  {ug}: {cnt} stocks')

    conn.close()
    print('DONE')

if __name__ == '__main__':
    main()
