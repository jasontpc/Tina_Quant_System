"""
fix_yfinance_symbols_final.py
補足剩餘未命名的 ETF 和常見代碼
"""
import sqlite3

DB = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data\yfinance.db'

# 常見 ETF 名稱對照表（人工填補）
ETF_NAMES = {
    '00640U.TW': '富邦日本ETF',
    '00641U.TW': '富邦韓國ETF',
    '00648L.TW': '富邦NASDAQ正2',
    '00669.TW': 'FH天天ETF',
    '00670T.TW': 'FH油能ETF',
    '00731B.TW': '元大10年電能債',
    '00771B.TW': '中信優先順天道',
    '00776B.TW': '中信優先非金融',
    '00788.TW': 'SPDR黄金股票',
    '00931.TW': '兆豐ESG成長高息',
    '00933.TW': '國泰數位支付服務',
    '00937.TW': '統一智慧q指',
    '00942.TW': '台新AAC ESG科技',
    '00945.TW': '野村全球晶圓指標',
    '00948.TW': '台新全球AIoT',
    '1478.TW': '詩天',
    '1479.TW': '和大',
    '2222.TW': '彰銀',
    '2333.TW': '永嘉',
    '2334.TW': '大縮',
    # 美股常見
    'SPY': 'SPDR S&P 500 ETF',
    'QQQ': 'Invesco QQQ Trust',
    'AAPL': 'Apple Inc',
    'MSFT': 'Microsoft Corp',
    'GOOGL': 'Alphabet Inc',
    'AMZN': 'Amazon.com Inc',
    'NVDA': 'NVIDIA Corp',
    'META': 'Meta Platforms',
    'TSLA': 'Tesla Inc',
    'BRK.B': 'Berkshire Hathaway',
    'JPM': 'JPMorgan Chase',
    'V': 'Visa Inc',
    'MA': 'Mastercard Inc',
    'UNH': 'UnitedHealth',
    'HD': 'Home Depot',
    'PG': 'Procter & Gamble',
    'XOM': 'Exxon Mobil',
    'CVX': 'Chevron Corp',
    'LLY': 'Eli Lilly',
    'JNJ': 'Johnson & Johnson',
    'KO': 'Coca-Cola Co',
    'PEP': 'PepsiCo Inc',
    'COST': 'Costco Wholesale',
    'MRK': 'Merck & Co',
    'ABBV': 'AbbVie Inc',
    'WMT': 'Walmart Inc',
    'BAC': 'Bank of America',
    'TMO': 'Thermo Fisher',
    'AVGO': 'Broadcom Inc',
    'CRM': 'Salesforce Inc',
    'ACN': 'Accenture PLC',
    'CSCO': 'Cisco Systems',
    'MCD': "McDonald's Corp",
    'ABT': 'Abbott Labs',
    'NKE': 'Nike Inc',
    'ORCL': 'Oracle Corp',
    'AMD': 'AMD Inc',
    'INTC': 'Intel Corp',
    'QCOM': 'Qualcomm Inc',
    'TXN': 'Texas Instruments',
    'LOW': "Lowe's Companies",
    'DIS': 'Walt Disney',
    'NFLX': 'Netflix Inc',
    'PYPL': 'PayPal Holdings',
    'GS': 'Goldman Sachs',
    'BLK': 'BlackRock Inc',
    'SPXL': 'Direxion S&P 500 3x',
    'SPXS': 'Direxion S&P 500 -3x',
    'TQQQ': 'ProShares UltraPro QQQ',
    'SQQQ': 'ProShares UltraPro Short QQQ',
    'SOXL': 'Direxion Daily Semiconductor 3x',
    'SOXS': 'Direxion Daily Semiconductor -3x',
    'UPRO': 'ProShares UltraPro S&P 500',
    'SDOW': 'ProShares UltraPro Short Dow30',
    'YANG': 'Direxion Daily China -3x',
    'YINN': 'Direxion Daily China 3x',
    'CURE': 'Direxion Daily Healthcare 3x',
    'WEAT': 'Teucrium Wheat Fund',
    'USO': 'United States Oil Fund',
    'GLD': 'SPDR Gold Shares',
    'SLV': 'iShares Silver Trust',
    'VIX': 'CBOE Volatility Index',
    '^VIX': 'CBOE Volatility Index',
    '^SPX': 'S&P 500 Index',
    '^NDX': 'NASDAQ 100 Index',
    '^TWII': '台灣加權指數',
    '^DJI': 'Dow Jones Industrial',
    'DX-Y.NYB': 'US Dollar Index',
    '^TNX': '10-Year Treasury Yield',
    '^TYX': '30-Year Treasury Yield',
    '^FVX': '5-Year Treasury Yield',
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

updated = 0
for sym, name in ETF_NAMES.items():
    cur.execute("UPDATE symbols SET name=? WHERE symbol=? AND name IS NULL", (name, sym))
    if cur.rowcount > 0:
        updated += 1

conn.commit()

cur.execute("SELECT COUNT(*) FROM symbols WHERE name IS NOT NULL")
named = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM symbols WHERE name IS NULL")
unnamed = cur.fetchone()[0]
print(f"Named: {named}/1290 ({named/1290*100:.0f}%) | Unnamed: {unnamed}")

cur.execute("SELECT symbol, name FROM symbols WHERE name IS NOT NULL ORDER BY RANDOM() LIMIT 10")
print("\nRandom named samples:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
print(f"\nFixed {updated} more symbols. Total named: {named}/1290")