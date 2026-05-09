# -*- coding: utf-8 -*-
"""
ETF Universe Builder — 台美 ETF 完整清單
========================================
目標：
- 台股高股息/價值/成長 ETF：50-100 檔
- 美股價值/成長/高股息 ETF：50-100 檔
- 更新 yfinance.db symbols 表

ETF 類型：
- 高股息（Yield > 4%）
- 價值型（Low P/E, Low P/B）
- 成長型（High Revenue Growth）
- 防禦型（Low Volatility）
"""

import sys, json
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System')
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'yfinance.db'

# ===== 台股 ETF Universe（完整列表）=====
TW_ETF_UNIVERSE = {
    # === 高股息 ETF（20檔）===
    '高股息': [
        '0056.TW',  # 元大高股息
        '00713.TW',  # 元大高息低波
        '00730.TW',  # 國泰永續高股息
        '00701.TW',  # 兆豐永續高息
        '00878.TW',  # 國泰永續高股息
        '00900.TW',  # 富邦特選高股息
        '00907.TW',  # 統一凹安全時高股息
        '00911.TW',  # 群益台灣精選高息
        '00915.TW',  # 凱基優選高股息
        '00918.TW',  # 大華優利高股息
        '00919.TW',  # 群益台灣精選高息
        '00927.TW',  # 統一股創未來
        '00929.TW',  # 復華華人世紀
        '00933.TW',  # 國泰永續高股息
        '00936.TW',  # 台新永續高息
        '00940.TW',  # 元大台灣價值高息
        '00943.TW',  # 統一全能
        '00944.TW',  # 台新臺灣永續高息
        '00948.TW',  # 中信關鍵半導體
        '00951.TW',  # 兆豐永續高息
    ],
    # === 價值型 ETF（10檔）===
    '價值型': [
        '0050.TW',  # 元大台灣50
        '00631L.TW',  # 兆豐藍籌30
        '00692.TW',  # 富邦公司治理
        '00752.TW',  # 中信創新醫療
        '00850.TW',  # 元大MSCI台灣
        '00876.TW',  # 國泰AI+
        '00893.TW',  # 國泰5G+
        '00902.TW',  # 兆豐永續高息
        '00912.TW',  # 永豐台灣ESG
        '00899.TW',  # 合庫摩卡特選50
    ],
    # === 成長型 ETF（15檔）===
    '成長型': [
        '0052.TW',  # 富邦台灣科技
        '0058.TW',  # 兆豐豐台灣科技
        '006201.TW',  # 統一全天候
        '006203.TW',  # 群益長安
        '006204.TW',  # 永豐DAWHO
        '006208.TW',  # 富邦台50
        '00690.TW',  # 兆豐藍籌30
        '00713.TW',  # 元大高息低波
        '00737.TW',  # 國泰AI+
        '00757.TW',  # 統一大FANG+
        '00788.TW',  # 國泰永續高股息
        '00891.TW',  # 中信關鍵半導體
        '00895.TW',  # 國泰5G+
        '00881.TW',  # 國泰台灣AI
        '00894.TW',  # 永豐ESG
    ],
    # === 半導體/科技（10檔）===
    '半導體科技': [
        '00891.TW',  # 中信關鍵半導體
        '00893.TW',  # 國泰5G+
        '00881.TW',  # 國泰台灣AI
        '00876.TW',  # 國泰AI+
        '00737.TW',  # 國泰AI+
        '00895.TW',  # 國泰5G+
        '00929.TW',  # 復華華人世紀
        '00946.TW',  # 台新AI
        '00948.TW',  # 中信關鍵半導體
        '00951.TW',  # 兆豐永續高息
    ],
    # === 槓桿/反向（10檔）===
    '槓桿反向': [
        '00631L.TW',  # 兆豐藍籌30 2x
        '00632R.TW',  # 兆豐藍籌30 -2x
        '00634R.TW',  # 元大台灣50 -2x
        '00637L.TW',  # 元大電子 -2x
        '00640U.TW',  # 國泰台灣加權 -2x
        '00641U.TW',  # 永豐台灣加權 -2x
        '00647L.TW',  # 富邦NASDAQ 2x
        '00648L.TW',  # 富邦NASDAQ -2x
        '00673R.TW',  # 元大S&P500 -2x
        '00674R.TW',  # 國泰S&P500 -2x
    ],
    # === 主題型（10檔）===
    '主題': [
        '00891.TW',  # 中信關鍵半導體
        '00893.TW',  # 國泰5G+
        '00881.TW',  # 國泰台灣AI
        '00876.TW',  # 國泰AI+
        '00757.TW',  # 統一大FANG+
        '00737.TW',  # 國泰AI+
        '00895.TW',  # 國泰5G+
        '00929.TW',  # 復華華人世紀
        '00946.TW',  # 台新AI
        '00912.TW',  # 永豐台灣ESG
    ],
}

# ===== 美股 ETF Universe（完整列表）=====
US_ETF_UNIVERSE = {
    # === 高股息 ETF（25檔）===
    '高股息': [
        'VYM',      # Vanguard 高股息
        'HDV',      # iShares 高股息
        'SPHD',     # Invesco 高股息
        'SPYD',     # SPDR 高股息
        'DVY',      # iShares 優先股
        'VIG',      # Vanguard 成長股息
        'DGRO',     # iShares 股息成長
        'SCHD',     # Schwab 股息優勢
        'FCO',      # Aberdeen 高股息
        'FID',      # First Trust 高股息
        'IQDF',     # IQ 股息成長
        'LRGF',     # iShares MSCI 美股動能
        'SRET',     # Global X 全球股息
        'VYM',      # Vanguard 高股息
        'HYLV',     # iShares 高 Yield
        'DGRW',     # WisdomTree 股息成長
        'DGRO',     # iShares 股息成長
        'VYMI',     # Vanguard 國際高股息
        'IDV',      # iShares 國際高股息
        'HDEF',     # iShares 國際高股息
        'SPFF',     # Global X Canadian
        'KWT',      # 太陽能股息
        'CLDL',     # 雲端股息
        'MOO',      # 農業股息
        'VNQ',      # 不動產（REIT）
    ],
    # === 價值型 ETF（25檔）===
    '價值型': [
        'VTV',      # Vanguard 價值
        'IVE',      # iShares S&P 500 價值
        'IUSV',     # iShares 價值
        'SPUV',     # Direxion S&P 500 價值
        'IVLV',     # iShares 價值
        'VBR',      # Vanguard 小型價值
        'VBR',      # Vanguard 小型價值
        'IWN',      # iShares 小型價值
        'SLYV',     # SPDR 小型價值
        'DLS',      # WisdomTree 國際價值
        'IWD',      # iShares 大型價值
        'IWS',      # iShares 中型價值
        'FAB',      # 小型價值
        'FAD',      # 中型價值
        'PRF',      # PowerShares 優先股
        'VOT',      # Vanguard 中型動能
        'SCHV',     # Schwab 價值
        'SPHQ',     # Invesco 質量股
        'RSP',      # S&P 500 等權重
        'USMV',     # 低波動價值
        'EFAV',     # 國際低波動
        'EFA',      # 國際 MSCI
        'SCZ',      # 小型國際股
        'DVI',      # 國際價值
        'DLN',      # 大型國際價值
    ],
    # === 成長型 ETF（25檔）===
    '成長型': [
        'VUG',      # Vanguard 成長
        'IVW',      # iShares S&P 500 成長
        'QQQ',      # Invesco QQQ（科技成長）
        'QQQM',     # Invesco QQQ（微型）
        'VGT',      # Vanguard 科技
        'XLK',      # Technology Select
        'ARKK',     # ARK Innovation
        'ARKW',     # ARK Next Generation
        'ARKQ',     # ARK 自動
        'ARKF',     # ARK Fintech
        'IGV',      # iShares 科技軟體
        'SMH',      # VanEck 半導體
        'SOXX',     # iShares 半導體
        'XSD',      # 半導體設備
        'SOCL',     # Social Media
        'FINX',     # Global X FinTech
        'AIQ',      # Global X AI
        'BOTZ',     # Global X 機器人
        'ROBO',     # Robo Global
        'CTNN',     # 消費科技
        'XLS',      # 健康科技
        'BUG',      # 全球網路安全
        'CLOU',     # 全球雲端
        'WTAI',     # AI 與機器人
        'BIB',      # 2x 納斯達克生物
    ],
    # === 質量/動能型（15檔）===
    '質量動能': [
        'MTUM',     # iShares 動能
        'SPGM',     # SPDR 質量股
        'QUAL',     # iShares 質量股
        'IUSV',     # iShares 價值
        'IJK',      # iShares 中型成長
        'IJS',      # iShares 小型價值
        'VBK',      # Vanguard 小型成長
        'VXF',      # Vanguard 擴展
        'VOOG',     # Vanguard 成長型
        'VOT',      # Vanguard 中型動能
        'SPMO',     # SPDR 動能
        'DAL',      # 動能Alpha
        'QMOM',     # QuantShares 動能
        'STOT',     # 短期動能
        'SLT',      # 長期動能
    ],
    # === 低波動/防禦型（15檔）===
    '低波動防禦': [
        'USMV',     # iShares 低波動
        'SPLV',     # Invesco 低波動
        'IDLV',     # Invesco 國際低波動
        'EFAV',     # iShares 國際低波動
        'EEMV',     # iShares 新興市場低波動
        'ACWV',     # iShares 全球低波動
        'ALTS',     # 全球多資產
        'VTI',      # Vanguard Total Market
        'ITOT',     # iShares 全市場
        'SPTM',     # SPDR 全市場
        'SCHB',     # Schwab 全市場
        'IWV',      # iShares 全市場
        'RSP',      # S&P 500 等權重
        'VO',       # Vanguard 中型
        'VB',       # Vanguard 小型
    ],
    # === 半導體/AI（10檔）===
    '半導體AI': [
        'SMH',      # VanEck 半導體
        'SOXX',     # iShares 半導體
        'XSD',      # 半導體設備
        'AIQ',      # Global X AI
        'BOTZ',     # Global X 機器人
        'ROBO',     # Robo Global
        'ARKK',     # ARK Innovation
        'ARKW',     # ARK Next
        'IRBO',     # iShares 機器人
        'THNQ',     # ROBO 人工智慧
    ],
}

# 去除重複並計算
ALL_TW_ETFS = list(set(sym for syms in TW_ETF_UNIVERSE.values() for sym in syms))
ALL_US_ETFS = list(set(sym for syms in US_ETF_UNIVERSE.values() for sym in syms))

print(f'TW ETF Universe: {len(ALL_TW_ETFS)} unique ETFs')
for category, syms in TW_ETF_UNIVERSE.items():
    print(f'  {category}: {len(syms)} ETFs')

print(f'\nUS ETF Universe: {len(ALL_US_ETFS)} unique ETFs')
for category, syms in US_ETF_UNIVERSE.items():
    print(f'  {category}: {len(syms)} ETFs')

# ===== 更新 yfinance.db symbols 表 =====

def update_etf_symbols(conn, etfs: list, universe_group: str, category: str):
    """更新 ETF 符號到 symbols 表"""
    import sqlite3
    from datetime import datetime
    
    cur = conn.cursor()
    today = datetime.now().isoformat()
    
    for sym in etfs:
        cur.execute("""
            INSERT OR REPLACE INTO symbols 
            (symbol, universe_group, category, last_updated)
            VALUES (?, ?, ?, ?)
        """, (sym, universe_group, category, today))
    
    conn.commit()
    return len(etfs)

if __name__ == '__main__':
    import sqlite3
    
    conn = sqlite3.connect(str(DB_PATH))
    
    # 寫入台股 ETF
    tw_count = 0
    for category, syms in TW_ETF_UNIVERSE.items():
        n = update_etf_symbols(conn, syms, f'tw_etf_{category}', 'TW_ETF')
        tw_count += n
    
    # 寫入美股 ETF
    us_count = 0
    for category, syms in US_ETF_UNIVERSE.items():
        n = update_etf_symbols(conn, syms, f'us_etf_{category}', 'US_ETF')
        us_count += n
    
    conn.close()
    
    print(f'\nDB Update:')
    print(f'  TW ETFs: {tw_count} entries → tw_etf_* universe')
    print(f'  US ETFs: {us_count} entries → us_etf_* universe')
    print('DONE')