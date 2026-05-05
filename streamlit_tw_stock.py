# -*- coding: utf-8 -*-
"""
Tina Scanner v3.0 - TW+US Stock Analysis | 1000 Tech Scoring + Institutional Data + Telegram
"""
import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import time
import urllib.request
import json
from datetime import datetime

TELEGRAM_BOT_TOKEN = '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q'
TELEGRAM_CHAT_ID = '1616824689'
FINMIND_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM'

def push_telegram(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True, 'OK'
    except Exception as e:
        return False, str(e)

def format_telegram(results, title):
    if not results:
        return ["No results"]
    all_lines = [
        f"*{title}* | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 40
    ]
    for r in results:
        tier_icon = {"A": "A", "B": "B", "C": "C", "D": "X"}.get(r.get('tier','?'), '?')
        ma_icon = "Y" if r.get('ma20_above_ma60') else "N"
        macd_icon = "+" if r.get('macd_hist', 0) > 0 else "-"
        bull = r.get('bullish', 'N')
        kd = "K+D+" if r.get('kd_golden') else ""
        inst = r.get('inst') or {}
        f_val = inst.get('foreign', 0)
        t_val = inst.get('trust', 0)
        d_val = inst.get('dealer', 0)
        inst_str = f" F:{f_val:+,} T:{t_val:+,} D:{d_val:,}" if inst else ""
        macd_hist = r.get('macd_hist', 0)
        macd_warn = ' ⚠️MACD-' if macd_hist < 0 else ''
        tier_display = tier_icon if not (tier_icon == 'A' and macd_hist < 0) else 'B'  # downgrade A if MACD<
        all_lines.append(
            f"[{tier_display}] {r['code']} {r['name'][:8]}"
            f" ${r['price']:.2f} ({r['chg']:+.2f}%)"
            f" S={r['score']:.0f}/1000 R={r['rsi']:.0f} K={r['k']:.0f} D={r['d']:.0f}"
            f" BB%={r['bb_pct']:.0f} BIAS={r['bias5']:+.1f}% Vol={r['vol_ratio']:.1f}x"
            f" M={macd_icon} MACD={macd_hist:+.2f}{macd_warn} MA={ma_icon} {bull} {kd}{inst_str}"
        )
    a = sum(1 for r in results if r.get('tier') == 'A')
    b = sum(1 for r in results if r.get('tier') == 'B')
    c = sum(1 for r in results if r.get('tier') == 'C')
    all_lines.append("=" * 40)
    all_lines.append(f"Grade: A={a} B={b} C={c} | Total={len(results)}")
    chunks = []
    chunk = []
    chunk_len = 0
    for line in all_lines:
        if chunk_len + len(line) + 1 > 4000 and chunk:
            chunks.append("\n".join(chunk))
            chunk = []
            chunk_len = 0
        chunk.append(line)
        chunk_len += len(line) + 1
    if chunk:
        chunks.append("\n".join(chunk))
    return chunks

# ── Short-lived In-Memory Cache (no persistent DB, auto-expire) ──
# SESSION_CACHE: stores 6mo price history per stock, TTL=300s
#   • No disk write — purely in-memory, cleared on app restart
#   • Every fetch checks TTL; expired entries are purged on access
#   • After TTL, MACD+RSI are recalculated from fresh yfinance data
#   • Cron jobs start with empty cache → always fresh calculation
#   • atexit handler clears expired entries on graceful shutdown
SESSION_CACHE = {}
CACHE_TTL = 300  # 5-minute TTL per stock entry

import atexit
def _clear_expired():
    now = time.time()
    expired = [k for k, (ts, _) in SESSION_CACHE.items() if now - ts > CACHE_TTL]
    for k in expired:
        del SESSION_CACHE[k]
    print(f"[Cache] Cleared {len(expired)} expired entries on shutdown.")

atexit.register(_clear_expired)

TW_CATS = {
    "熱門台股": ["2330","2454","2317","2382","3034","3665","2881","2603","2303","1216"],
    "AI 科技": ["2317","2324","2330","2345","2353","2381","2382","2454","3034","3095","3163","3211","3231","3306","3323","3325","3349","3432","3479","3483","3491","3534","3653","3665","3702","5515"],
    "半導體": ["2303","2311","2325","2363","2379","2473","3035","3041","3063","3105","3122","3141","3169","3178","3227","3228","3257","3259","3260","3264","3265","3268","3317","3372","3374","3438","3443","3467","3474","3519","3527","3529","3534","3536","3555","3556","3567","3579","3581","3598","3675","3680","3686","3707","4749","4923","4925","4945","4951","4966","4971","4973","4991","5236","5246","5262","5272","5274","5280","5297","5299","5302","5305","5344","5347","5351","5425","5443","5468","5483","5487","6103","6104","6129","6138","6147","6182","6187","6208","6223","6229","6233","6237","6239","6261","6271","6287","6291","6411","6415","6423","6435","6451","6457","6462","6485","6488","6494","6510","6515","6525","6526","6531","6532","6548","6552","6563","6568","6594","6640","6643","6651","6679","6683","6684","6693","6695","6699","6708","6716","6719","6720","6732","6756","6770","6786","6788","6819","6823","6829","6842","6895","6907","6920","6927","6953","6996","7530","7556","7669","7704","7707","7712","7734","7751","7768","7769","7770","7772","7796","7810","7815","7828","7843","7853","7856","7866","7872","7880","7886","7887","7899","7909","8024","8040","8054","8081","8086","8088","8091","8098","8102","8131","8150","8227","8261","8271","8277","8299","8383"],
    "光通訊/CPO": ["2345","3053","3432","3491","3534","3599","3627","4944","5233","5281","6255","6409","2444","3047","3053","3432","3491","3534","3558","3564","4903","4905","4906","4908","4909","5233","5353","6109","6409","3081","2455","3363","3163","6442","6715","4979","6451","4977","4908","3450","2489","3711","3265","6830","6223","6515","2360","2499","6706","2345","3665","3533","2455","3105","6488","2303","2330","3711"],
    "儲存/記憶體": ["2330","2382","2401","2454","3034","3044","3217","3356","3592","4924","4939","6208","6488","3711"],
    "ETF": ["0050","0056","00646","00662","00713","00757","00927","00878","00900","00902","00906"],
    "金融": ["2801","2807","2809","2812","2816","2820","2823","2827","2831","2832","2833","2833A","2834","2836","2836A","2837","2838","2838A","2845","2847","2849","2850","2851","2852","2854","2855","2856","2867","2880","2881","2881A","2881B","2881C","2882","2882A","2882B","2883","2883A","2883B","2884","2885","2886","2887","2887C","2887E","2887F","2887G","2887H","2887I","2887Z1","2888","2888A","2888B","2889","2890","2891","2891A","2891B","2891C","2892","2897","2897A","2897B","5820","5854","5859","5863","5864","5876","5878","5880","6004","6005","6012","6015","6016","6020","6021","6023","6024","6026","6027","6028","6035","6878"],
    "全部": [],
}
US_CATS = {
    'S&P 500': ['A','AAPL','ABBV','ABNB','ABT','ACGL','ACN','ADBE','ADI','ADM','ADP','ADSK','AEE','AEP','AES','AFL','AIG','AIZ','AJG','AKAM','ALB','ALGN','ALL','ALLE','AMAT','AMCR','AMD','AME','AMGN','AMP','AMT','AMZN','ANET','AON','AOS','APA','APD','APH','APO','APP','APTV','ARE','ARES','ATO','AVB','AVGO','AVY','AWK','AXON','AXP','AZO','B','BA','BAC','BALL','BAX','BBY','BDX','BEN','BG','BIIB','BK','BKNG','BKR','BLDR','BLK','BMY','BR','BRO','BSX','BX','BXP','C','CAG','CAH','CARR','CASY','CAT','CB','CBOE','CBRE','CCI','CCL','CDNS','CDW','CEG','CF','CFG','CHD','CHRW','CHTR','CI','CIEN','CINF','CL','CLX','CME','CMG','CMI','CMS','CNC','CNP','COF','COHR','COIN','COO','COP','COR','COST','CPAY','CPB','CPRT','CPT','CRH','CRL','CRM','CRWD','CSCO','CSGP','CSX','CTAS','CTRA','CTSH','CTVA','CVNA','CVS','CVX','D','DAL','DASH','DD','DDOG','DE','DECK','DELL','DG','DGX','DHI','DHR','DIS','DLR','DLTR','DOC','DOV','DOW','DPZ','DRI','DTE','DUK','DVA','DVN','DXCM','EA','EBAY','ECL','ED','EFX','EG','EIX','EL','ELV','EME','EMR','EOG','EPAM','EQIX','EQR','EQT','ERIE','ES','ESS','ETN','ETR','EVRG','EW','EXC','EXE','EXPD','EXPE','EXR','F','FANG','FAST','FCX','FDS','FDX','FE','FFIV','FICO','FIS','FISV','FITB','FIX','FOX','FOXA','FRT','FSLR','FTNT','FTV','GD','GDDY','GE','GEHC','GEN','GEV','GILD','GIS','GL','GLW','GM','GNRC','GOOG','GPC','GPN','GRMN','GS','GWW','HAL','HAS','HBAN','HCA','HD','HIG','HII','HLT','HON','HOOD','HPE','HPQ','HRL','HSIC','HST','HSY','HUBB','HUM','HWM','IBKR','IBM','ICE','IDXX','IEX','IFF','INCY','INTC','INTU','INVH','IP','IQV','IR','IRM','ISRG','IT','ITW','IVZ','J','JBHT','JBL','JCI','JKHY','JNJ','JPM','KDP','KEY','KEYS','KHC','KIM','KKR','KLAC','KMB','KMI','KO','KR','KVUE','L','LDOS','LEN','LH','LHX','LII','LIN','LITE','LLY','LMT','LNT','LOW','LRCX','LULU','LUV','LVS','LYB','LYV','MA','MAA','MAR','MAS','MCD','MCHP','MCK','MCO','MDLZ','MDT','MET','META','MGM','MKC','MLM','MMM','MNST','MO','MOS','MPC','MPWR','MRK','MRNA','MRSH','MS','MSCI','MSFT','MSI','MTB','MTD','MU','NCLH','NDAQ','NDSN','NEE','NEM','NFLX','NI','NKE','NOC','NOW','NRG','NSC','NTAP','NTRS','NUE','NVDA','NVR','NWS','NWSA','NXPI','O','ODFL','OKE','OMC','ON','ORCL','ORLY','OTIS','OXY','PANW','PAYX','PCAR','PCG','PEG','PEP','PFE','PFG','PG','PGR','PH','PHM','PKG','PLD','PLTR','PM','PNC','PNR','PNW','PODD','POOL','PPG','PPL','PRU','PSA','PSX','PTC','PWR','PYPL','Q','QCOM','RCL','REG','REGN','RF','RJF','RL','RMD','ROK','ROL','ROP','ROST','RSG','RTX','RVTY','SATS','SBAC','SBUX','SCHW','SHW','SJM','SLB','SMCI','SNA','SNDK','SNPS','SO','SOLV','SPG','SPGI','SRE','STE','STLD','STT','STX','STZ','SW','SWK','SWKS','SYF','SYK','SYY','T','TAP','TDG','TDY','TECH','TEL','TER','TFC','TGT','TJX','TKO','TMO','TMUS','TPL','TPR','TRGP','TRMB','TROW','TRV','TSCO','TSLA','TSN','TT','TTD','TTWO','TXN','TXT','TYL','UAL','UBER','UDR','UHS','ULTA','UNH','UNP','UPS','URI','USB','V','VICI','VLO','VLTO','VMC','VRSK','VRSN','VRT','VRTX','VST','VTR','VTRS','VZ','WAB','WAT','WBD','WDAY','WDC','WEC','WELL','WFC','WM','WMB','WMT','WRB','WSM','WST','WTW','WY','WYNN','XEL','XOM','XYL','XYZ','YUM','ZBH','ZBRA','ZTS'],
    # ─── S&P 500 GICS 產業分類 ───
    'IT - Information Technology': ['AAPL','ACN','ADBE','ADI','ADSK','AKAM','AMAT','AMD','ANET','APH','APP','AVGO','CDNS','CDW','CIEN','COHR','CRM','CRWD','CSCO','CTSH','DDOG','DELL','EPAM','FFIV','FICO','FSLR','FTNT','GDDY','GEN','GLW','HPE','HPQ','IBM','INTC','INTU','IT','JBL','KEYS','KLAC','LITE','LRCX','MCHP','MPWR','MSFT','MSI','MU','NOW','NTAP','NVDA','NXPI','ON','ORCL','PANW','PLTR','PTC','Q','QCOM','ROP','SMCI','SNDK','SNPS','STX','SWKS','TDY','TEL','TER','TRMB','TXN','TYL','VRSN','WDAY','WDC','ZBRA'],
    'HC - Health Care': ['A','ABBV','ABT','ALGN','AMGN','BAX','BDX','BIIB','BMY','BSX','CAH','CI','CNC','COO','COR','CRL','CVS','DGX','DHR','DVA','DXCM','ELV','EW','GEHC','GILD','HCA','HSIC','HUM','IDXX','INCY','IQV','ISRG','JNJ','LH','LLY','MCK','MDT','MRK','MRNA','MTD','PFE','PODD','REGN','RMD','RVTY','SOLV','STE','SYK','TECH','TMO','UHS','UNH','VRTX','VTRS','WAT','WST','ZBH','ZTS'],
    'FIN - Financials': ['ACGL','AFL','AIG','AIZ','AJG','ALL','AMP','AON','APO','ARES','AXP','BAC','BEN','BK','BLK','BRK.B','BRO','BX','C','CB','CFG','CINF','CME','COF','COIN','CPAY','EG','ERIE','FDS','FIS','FISV','FITB','GL','GPN','GS','HBAN','HIG','HOOD','IBKR','ICE','IVZ','JKHY','JPM','KEY','KKR','L','MA','MCO','MET','MRSH','MS','MSCI','MTB','NDAQ','NTRS','PFG','PGR','PNC','PRU','PYPL','RF','RJF','SCHW','SPGI','STT','SYF','TFC','TROW','TRV','USB','V','WFC','WRB','WTW','XYZ'],
    'CD - Consumer Discretionary': ['ABNB','AMZN','APTV','AZO','BBY','BKNG','CCL','CMG','CVNA','DASH','DECK','DHI','DPZ','DRI','EBAY','EXPE','F','GM','GPC','GRMN','HAS','HD','HLT','LEN','LOW','LULU','LVS','MAR','MCD','MGM','NCLH','NKE','NVR','ORLY','PHM','POOL','RCL','RL','ROST','SBUX','TJX','TPR','TSCO','TSLA','ULTA','WSM','WYNN','YUM'],
    'COMM - Communication Services': ['CHTR','CMCSA','DIS','EA','FOX','FOXA','GOOG','GOOGL','LYV','META','NFLX','NWS','NWSA','OMC','SATS','T','TKO','TMUS','TTD','TTWO','VZ','WBD'],
    'IND - Industrials': ['ADP','ALLE','AME','AOS','AXON','BA','BLDR','BR','CARR','CAT','CHRW','CMI','CPRT','CSX','CTAS','DAL','DE','DOV','EFX','EME','EMR','ETN','EXPD','FAST','FDX','FIX','FTV','GD','GE','GEV','GNRC','GWW','HII','HON','HUBB','HWM','IEX','IR','ITW','J','JBHT','JCI','LDOS','LHX','LII','LMT','LUV','MAS','MMM','NDSN','NOC','NSC','ODFL','OTIS','PAYX','PCAR','PH','PNR','PWR','ROK','ROL','RSG','RTX','SNA','SWK','TDG','TT','TXT','UAL','UBER','UNP','UPS','URI','VLTO','VRSK','VRT','WAB','WM','XYL'],
    'CST - Consumer Staples': ['ADM','BF.B','BG','CAG','CASY','CHD','CL','CLX','COST','CPB','DG','DLTR','EL','GIS','HRL','HSY','KDP','KHC','KMB','KO','KR','KVUE','MDLZ','MKC','MNST','MO','PEP','PG','PM','SJM','STZ','SYY','TAP','TGT','TSN','WMT'],
    'ENE - Energy': ['APA','BKR','COP','CTRA','CVX','DVN','EOG','EQT','EXE','FANG','HAL','KMI','MPC','OKE','OXY','PSX','SLB','TPL','TRGP','VLO','WMB','XOM'],
    'UTI - Utilities': ['AEE','AEP','AES','ATO','AWK','CEG','CMS','CNP','D','DTE','DUK','ED','EIX','ES','ETR','EVRG','EXC','FE','LNT','NEE','NI','NRG','PCG','PEG','PNW','PPL','SO','SRE','VST','WEC','XEL'],
    'RE - Real Estate': ['AMT','ARE','AVB','BXP','CBRE','CCI','CPT','CSGP','DLR','DOC','EQIX','EQR','ESS','EXR','FRT','HST','INVH','IRM','KIM','MAA','O','PLD','PSA','REG','SBAC','SPG','UDR','VICI','VTR','WELL','WY'],
    'MAT - Materials': ['ALB','AMCR','APD','AVY','BALL','CF','CRH','CTVA','DD','DOW','ECL','FCX','IFF','IP','LIN','LYB','MLM','MOS','NEM','NUE','PKG','PPG','SHW','STLD','SW','VMC'],
    # ─── 主題精選（跨 GICS 板塊）───
    'AI 基礎設施': ['NVDA','AMD','AVGO','MRVL','AMZN','MSFT','GOOGL','META','ANET','VRT','DELL','PLTR','NOW','ORCL','COHR','LITE','GLW','AMSC','NVT','SBGSY','EQIX','DLR','AMKR'],
    '金融科技': ['PYPL','SQ','AFRM','COIN','HOOD','DB','AFC','GREM','UPST','LC','RBLX','NU','SOFI'],
    '電動車/綠能': ['TSLA','RIVN','LCID','F','GM','HYLN','ENPH','SEDG','SPWR','FSLR','RUN','ALB','NIO','XPEV','CHPT','BLNK','CCID','NOVA'],
    # ─── 美股 ETF ───
    # ─── 美股熱門 ETF（Jo 提供，22 檔）───
    'ETF - 指數核心': ['VOO','IVV','SPY','VTI'],
    'ETF - 科技與成長': ['QQQ','VUG','SOXX','SMH'],
    'ETF - 股息與價值': ['SCHD','VYM','VTV','DGRO'],
    'ETF - 債券與配置': ['BND','TLT','SHY','AGG'],
    'ETF - 全球與其他': ['VT','VXUS','VWO'],
    '全部': [],
}





all_tw = []
seen = set()
for v in TW_CATS.values():
    for c in v:
        if c not in seen:
            seen.add(c)
            all_tw.append(c)
TW_CATS["全部"] = sorted(all_tw, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))[:500]

all_us = []
seen = set()
for v in US_CATS.values():
    for c in v:
        if c not in seen:
            seen.add(c)
            all_us.append(c)
US_CATS["全部"] = sorted(all_us, key=lambda x: x)[:500]

TW_NAMES = {
    "2330": "台積電", "2454": "聯發科", "2317": "鴻海", "2382": "廣達",
    "3034": "緯穎", "3665": "穎崴", "2881": "富邦金", "2603": "長榮",
    "2303": "聯電", "1216": "統一", "0050": "元大台灣50", "0056": "元大高股息",
    "00646": "富邦S&P500", "00662": "富邦NASDAQ", "00713": "元大高息低波",
    "00757": "統一大FANG+", "00927": "統一手創未來", "00878": "國泰永續高股息",
    "00900": "富邦ESG", "00902": "兆豐藍籌", "00906": "凱基優選高股息",
    "3217": "3217", "2401": "2401", "3527": "3527", "4749": "美時",
    "6819": "6819", "6229": "6229", "6786": "6786", "6563": "6563",
    "5351": "5351", "4923": "4923", "3265": "3265",
}
US_NAMES = {
    # S&P 500 stocks
    "NVDA": "NVIDIA", "AVGO": "Broadcom", "AMD": "AMD", "MRVL": "Marvell", "MU": "Micron",
    "INTC": "Intel", "QCOM": "Qualcomm", "AMAT": "Applied Mat", "LRCX": "Lam Research",
    "KLAC": "KLA", "SNPS": "Synopsys", "CDNS": "Cadence", "NXPI": "NXP", "ASML": "ASML",
    "TSM": "TSM", "TXN": "Texas Instr", "ADI": "Analog Devices", "MPWR": "Monolithic Power",
    "TER": "Teradyne", "MCHP": "Microchip", "ON": "ON Semi", "CRDO": "Credo", "ALAB": "Astera Labs",
    "ENTG": "Entegris", "MTSI": "MACOM", "ASX": "ASE Tech",
    # XPU / Design
    "ARM": "ARM",
    # 光通訊 / CPO
    "ANET": "Arista", "CSCO": "Cisco", "COHR": "Coherent", "LITE": "Lumentum", "GLW": "Corning",
    # 記憶體 / 儲存
    "WDC": "Western Digital", "STX": "Seagate",
    # 電力 / 散熱
    "VRT": "Vertiv", "ETN": "Eaton", "AMSC": "AMSC", "SBGSY": "Schneider", "NVT": "nVent",
    # 先進封裝 / 雲端
    "AMKR": "Amkor", "EQIX": "Equinix", "DLR": "Digital Realty", "ORCL": "Oracle",
    # AI 雲端
    "AMZN": "Amazon", "MSFT": "Microsoft", "GOOGL": "Google", "META": "Meta", "DELL": "Dell",
    # 5G
    "NOK": "Nokia", "ERIC": "Ericsson", "SWKS": "Skyworks", "RF": "RF Micro",
    "VZ": "Verizon", "T": "AT&T", "TMUS": "T-Mobile",
    # 設備
    "CAMT": "Camtek",
    # FinTech
    "PYPL": "PayPal", "SQ": "Block", "AFRM": "Affirm", "COIN": "Coinbase", "HOOD": "Robinhood",
    "DB": "Deutsche Bank", "BAC": "Bank of America", "GS": "Goldman", "V": "Visa", "MA": "Mastercard",
    # 其他
    "SMCI": "SuperMicro", "AI": "C3.ai", "DT": "Dynatrace",
    # ─── ETF - 指數核心 ───
    'VOO': "Vanguard S&P 500", 'IVV': "iShares Core S&P 500", 'SPY': "SPDR S&P 500", 'VTI': "Vanguard 全美市場",
    # ─── ETF - 科技與成長 ───
    'QQQ': "Invesco QQQ", 'VUG': "Vanguard Growth", 'SOXX': "iShares 半導體", 'SMH': "VanEck 半導體",
    # ─── ETF - 股息與價值 ───
    'SCHD': "Schwab 高股息", 'VYM': "Vanguard 高殖利率", 'VTV': "Vanguard Value", 'DGRO': "iShares 股息增長",
    # ─── ETF - 債券與配置 ───
    'BND': "Vanguard 綜合債券", 'TLT': "iShares 長天期美債", 'SHY': "iShares 短天期美債", 'AGG': "iShares 綜合債",
    # ─── ETF - 全球與其他 ───
    'VT': "Vanguard 全球股票", 'VXUS': "Vanguard 非美股市", 'VWO': "Vanguard 新興市場",
    # 舊 ETF
    'SOXX': "SOX ETF", 'SMH': "SMH ETF",
    'XLF': "Financial ETF", 'ARKK': "ARK ETF", 'FXI': "China ETF",
    'GDX': "Gold ETF", 'XLE': "Energy ETF",
}

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def get_tier(rsi):
    if rsi < 35: return "A"
    if rsi < 50: return "B"
    if rsi < 70: return "C"
    return "D"

def calc_macd(close):
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(macd_signal.iloc[-1]), float((macd - macd_signal).iloc[-1])

# ── Data Fetch ──────────────────────────────────────────────────────────────

def fetch_institutional(code):
    """Fetch F/T/D from FinMind TaiwanStockInstitutionalInvestorsBuySell (real-time)"""
    try:
        import urllib.request
        params = {
            'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
            'data_id': str(code).zfill(4),
            'start_date': '2026-05-04',
            'end_date': '2026-05-05',
            'token': FINMIND_TOKEN
        }
        url = 'https://api.finmindtrade.com/api/v4/data?' + '&'.join(f'{k}={v}' for k, v in params.items())
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
            rows = data.get('data', [])
            if not rows:
                return None
            latest_date = max(r['date'] for r in rows)
            day_rows = [r for r in rows if r['date'] == latest_date]
            result = {'foreign': 0, 'trust': 0, 'dealer': 0}
            for r in day_rows:
                name = r.get('name', '')
                net = r.get('buy', 0) - r.get('sell', 0)
                if name == 'Foreign_Investor':
                    result['foreign'] = net
                elif name == 'Investment_Trust':
                    result['trust'] = net
                elif 'Dealer' in name:
                    result['dealer'] += net
            return result if (result['foreign'] or result['trust'] or result['dealer']) else None
    except:
        return None

def fetch_price(code, market='TW'):
    cache_key = f"{market}:{code}"
    now = time.time()
    if cache_key in SESSION_CACHE:
        ts, cached_h = SESSION_CACHE[cache_key]
        if now - ts < CACHE_TTL:
            return cached_h
    try:
        if market == 'TW':
            for suffix in ['.TW', '.TWO']:
                sym = str(code).zfill(4) + suffix
                h = yf.Ticker(sym).history(period='6mo')
                if h is not None and len(h) >= 30:
                    SESSION_CACHE[cache_key] = (now, h)
                    return h
        else:
            h = yf.Ticker(code).history(period='6mo')
            if h is not None and len(h) >= 30:
                SESSION_CACHE[cache_key] = (now, h)
                return h
    except:
        pass
    return None

def analyze(code, market='TW'):
    name = (TW_NAMES if market == 'TW' else US_NAMES).get(code, code)
    price_hist = fetch_price(code, market)
    if price_hist is None:
        return None
    inst = fetch_institutional(code) if market == 'TW' else None
    try:
        close = price_hist['Close'].astype(float)
        price = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) >= 2 else price
        chg = (price - prev) / prev * 100
        rsi = float(calc_rsi(close).iloc[-1])
        if np.isnan(rsi): rsi = 50.0
        ma20 = float(close.rolling(20).mean().iloc[-1])
        ma60_val = float(close.rolling(60).mean().iloc[-1])
        ma60 = ma60_val if not np.isnan(ma60_val) else None
        ma_bull = bool(ma60 and ma20 > ma60)
        macd_val, macd_sig, macd_hist = calc_macd(close)
        macd_bull = macd_hist > 0
        low9 = close.rolling(9).min()
        high9 = close.rolling(9).max()
        rsv = (close - low9) / (high9 - low9 + 1e-9) * 100
        k_series = rsv.ewm(alpha=1/3).mean()
        d_series = k_series.ewm(alpha=1/3).mean()
        k_val = float(k_series.iloc[-1])
        d_val = float(d_series.iloc[-1])
        kd_golden = bool(k_val > d_val and k_val < 30)
        bb_ma20 = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = float((bb_ma20 + 2 * bb_std).iloc[-1])
        bb_lower = float((bb_ma20 - 2 * bb_std).iloc[-1])
        bb_pct = (price - bb_lower) / (bb_upper - bb_lower + 1e-9) * 100
        ma5 = close.rolling(5).mean()
        bias5 = float((close.iloc[-1] - ma5.iloc[-1]) / ma5.iloc[-1] * 100)
        vol = price_hist['Volume'] if 'Volume' in price_hist.columns else close * 0
        vol_ma5 = float(vol.rolling(5).mean().iloc[-1])
        vol_ratio = float(vol.iloc[-1] / vol_ma5) if vol_ma5 > 0 else 1.0
        bullish = "Y" if (ma_bull and macd_bull) else ("W" if macd_bull else "N")
        # ── Tina Brain 1000 Tech Score ────────────────────────────────
        # RSI: 250pts | MACD: 200pts | K: 150pts | D: 100pts
        # BB%: 150pts | MA: 100pts | Vol: 50pts
        if rsi < 30:
            rsi_s = 250
        elif rsi < 35:
            rsi_s = 220
        elif rsi < 40:
            rsi_s = 175
        elif rsi < 45:
            rsi_s = 130
        elif rsi < 50:
            rsi_s = 90
        elif rsi < 55:
            rsi_s = 55
        elif rsi < 60:
            rsi_s = 30
        elif rsi < 65:
            rsi_s = 15
        elif rsi < 70:
            rsi_s = 5
        else:
            rsi_s = 0
        if macd_hist > 2:
            macd_s = 200
        elif macd_hist > 1:
            macd_s = 170
        elif macd_hist > 0.5:
            macd_s = 130
        elif macd_hist > 0:
            macd_s = 80
        elif macd_hist > -0.5:
            macd_s = 40
        else:
            macd_s = 0
        if k_val < 20:
            k_s = 150
        elif k_val < 30:
            k_s = 130
        elif k_val < 40:
            k_s = 90
        elif k_val < 50:
            k_s = 50
        elif k_val < 60:
            k_s = 25
        elif k_val < 70:
            k_s = 10
        else:
            k_s = 0
        if d_val < 20:
            d_s = 100
        elif d_val < 30:
            d_s = 80
        elif d_val < 40:
            d_s = 50
        elif d_val < 50:
            d_s = 25
        elif d_val < 60:
            d_s = 10
        else:
            d_s = 0
        if bb_pct < 10:
            bb_s = 150
        elif bb_pct < 20:
            bb_s = 130
        elif bb_pct < 30:
            bb_s = 100
        elif bb_pct < 40:
            bb_s = 60
        elif bb_pct < 50:
            bb_s = 30
        elif bb_pct < 70:
            bb_s = 10
        else:
            bb_s = 0
        ma_s = 100 if ma_bull else 0
        if vol_ratio >= 2.0:
            vol_s = 50
        elif vol_ratio >= 1.5:
            vol_s = 40
        elif vol_ratio >= 1.2:
            vol_s = 30
        elif vol_ratio >= 1.0:
            vol_s = 15
        else:
            vol_s = 5
        score = rsi_s + macd_s + k_s + d_s + bb_s + ma_s + vol_s
        # Grade from score
        if score >= 700:
            tier = "A"
        elif score >= 500:
            tier = "B"
        elif score >= 300:
            tier = "C"
        else:
            tier = "D"
        return {
            'code': code, 'name': name,
            'price': price, 'chg': chg, 'rsi': rsi,
            'macd': macd_val, 'macd_sig': macd_sig, 'macd_hist': macd_hist,
            'ma20': ma20, 'ma60': ma60, 'ma20_above_ma60': ma_bull,
            'k': k_val, 'd': d_val, 'kd_golden': kd_golden,
            'bb_upper': bb_upper, 'bb_lower': bb_lower, 'bb_pct': bb_pct,
            'bias5': bias5, 'vol_ratio': vol_ratio,
            'bullish': bullish,
            'inst': inst,
            'score': score, 'tier': tier,
            'score_breakdown': {'rsi': rsi_s, 'macd': macd_s, 'k': k_s, 'd': d_s, 'bb': bb_s, 'ma': ma_s, 'vol': vol_s},
        }
    except:
        return None

# ── Page Setup ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Tina Scanner v3.0", page_icon="📈", layout="wide")
st.title("📈 Tina Scanner v3.0 — US Tech 1000 Scoring")

tw_tab, us_tab = st.tabs(["Taiwan", "US"])

# ═══════════════════════════ TW TAB ═══════════════════════════
with tw_tab:
    col_side, col_main = st.columns([1, 4], vertical_alignment="top")
    with col_side:
        st.header("Filters")
        tw_cat = st.selectbox("Category", list(TW_CATS.keys()), key="tw_cat")
        tw_grade = st.multiselect("Grade", ["A","B","C","D"], default=["A","B","C","D"], key="tw_grade")
        tw_score_min = st.slider("Score Min", 0, 1000, 0, key="tw_score")
        tw_rsi_max = st.slider("RSI Max", 30, 100, 100, key="tw_rsi")
        tw_macd_filter = st.checkbox("排除 MACD < 0", value=False, key="tw_macd_filter")
        codes = TW_CATS.get(tw_cat, [])
        st.info(f"{len(codes)} stocks")
        analyze_tw = st.button("Analyze", type="primary", use_container_width=True, key="btn_tw_analyze")

    if 'tw_results' not in st.session_state:
        st.session_state.tw_results = None
        st.session_state.tw_filtered = None
        st.session_state.tw_cat_saved = None

    if analyze_tw:
        with st.spinner("Analyzing + Fetching Institutional..."):
            results = []
            bar = st.progress(0)
            for i, code in enumerate(codes):
                r = analyze(code, 'TW')
                if r:
                    results.append(r)
                bar.progress((i+1) / len(codes))
                time.sleep(0.12)
            bar.empty()
            filtered = [r for r in results
                        if r['rsi'] <= tw_rsi_max
                        and r['tier'] in tw_grade
                        and r['score'] >= tw_score_min
                        and (not tw_macd_filter or r['macd_hist'] >= 0)]
            filtered.sort(key=lambda x: x['score'], reverse=True)
            st.session_state.tw_results = results
            st.session_state.tw_filtered = filtered
            st.session_state.tw_cat_saved = tw_cat

    results = st.session_state.tw_results
    filtered = st.session_state.tw_filtered
    cat_saved = st.session_state.tw_cat_saved

    if results:
        a = sum(1 for r in filtered if r['tier'] == 'A')
        b = sum(1 for r in filtered if r['tier'] == 'B')
        c = sum(1 for r in filtered if r['tier'] == 'C')
        d = sum(1 for r in filtered if r['tier'] == 'D')
        bull = sum(1 for r in filtered if r['bullish'] == 'Y')
        kd = sum(1 for r in filtered if r['kd_golden'])
        m = st.columns(6)
        m[0].metric("A", a)
        m[1].metric("B", b)
        m[2].metric("C", c)
        m[3].metric("D", d)
        m[4].metric("BULL", bull)
        m[5].metric("KD+", kd)
        st.success(f"{len(results)} stocks | {len(filtered)} after filter")

    if filtered:
        rows = []
        for r in filtered:
            inst = r.get('inst') or {}
            f_val = inst.get('foreign', 0)
            t_val = inst.get('trust', 0)
            d_val = inst.get('dealer', 0)
            rows.append({
                "Score": f"{r['score']:.0f}",
                "Code": r['code'],
                "Name": r['name'],
                "Price": f"${r['price']:.2f}",
                "Chg%": f"{r['chg']:+.2f}%",
                "RSI": f"{r['rsi']:.0f}",
                "K": f"{r['k']:.0f}",
                "D": f"{r['d']:.0f}",
                "BB%": f"{r['bb_pct']:.0f}%",
                "BIAS5": f"{r['bias5']:+.1f}%",
                "Vol": f"{r['vol_ratio']:.1f}x",
                "MA": "Y" if r['ma20_above_ma60'] else "N",
                "F": f"{f_val:+,}" if f_val != 0 else "-",
                "T": f"{t_val:+,}" if t_val != 0 else "-",
                "D": f"{d_val:+,}" if d_val != 0 else "-",
                "Tier": r['tier'],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400, hide_index=True)

        with st.expander("Send to Telegram"):
            grade_filter = st.multiselect("Grade Filter", ["A","B","C","D"], default=["A","B","C","D"], key="tw_grade_send")
            grade_filtered = [r for r in filtered if r['tier'] in grade_filter]
            sel = st.multiselect("Select", [f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" for r in grade_filtered], key="tw_sel")
            sel_rows = [r for r in grade_filtered if f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" in sel]
            sc = len(sel_rows)
            r1, r2 = st.columns(2)
            if r1.button(f"Send ({sc}) Grade {','.join(grade_filter)}", disabled=(sc==0), use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(sel_rows, f"TW-{cat_saved} ({','.join(grade_filter)})")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {sc} stocks ({len(chunks)} msgs)")
            if r2.button(f"Send All ({len(grade_filtered)}) Grade {','.join(grade_filter)}", use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(grade_filtered, f"TW-{cat_saved} ({','.join(grade_filter)})")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {len(grade_filtered)} stocks ({len(chunks)} msgs)")

        if results:
            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')
            st.download_button("CSV", csv, f"tw_{cat_saved}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="tw_csv")
    # --- Single Stock Deep Analysis ---
    st.divider()
    st.subheader("Single Stock Deep Analysis")
    col_code, col_btn = st.columns([2, 1])
    with col_code:
        single_code = st.text_input("Stock Code", "2330", key="tw_single_code").strip().upper()
    with col_btn:
        st.write(" ")
        do_single = st.button("Analyze", type="primary", use_container_width=True, key="btn_tw_single")
    if do_single:
        with st.spinner(f"Analyzing {single_code}..."):
            r = analyze(single_code, "TW")
        if r:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Price", f"${r['price']:.2f}")
            m2.metric("Change", f"{r['chg']:+.2f}%")
            m3.metric("RSI", f"{r['rsi']:.0f}")
            m4.metric("Tier", r['tier'])
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("K", f"{r['k']:.0f}")
            m2.metric("D", f"{r['d']:.0f}")
            m3.metric("BB%", f"{r['bb_pct']:.0f}%")
            m4.metric("BIAS5", f"{r['bias5']:+.1f}%")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("MA20", f"${r['ma20']:.0f}")
            m2.metric("MA60", f"${r['ma60']:.0f}" if r['ma60'] else "N/A")
            m3.metric("Vol Ratio", f"{r['vol_ratio']:.1f}x")
            m4.metric("MACD Hist", f"{r['macd_hist']:+.2f}")
            sigs = []
            if r['kd_golden']: sigs.append("KD Golden Cross")
            if r['ma20_above_ma60']: sigs.append("MA Bullish")
            if r['macd_hist'] > 0: sigs.append("MACD+")
            if r['bb_pct'] < 20: sigs.append("BB Oversold")
            if r['rsi'] < 35: sigs.append("RSI Oversold")
            if r['rsi'] > 70: sigs.append("RSI Overbought")
            inst = r.get("inst") or {}
            if inst:
                st.caption("Institutional: F={:+,.0f} T={:+,.0f} D={:+,.0f}".format(
                    inst.get("foreign",0), inst.get("trust",0), inst.get("dealer",0)))
            st.caption(" | ".join(sigs) if sigs else "No special signals")
        else:
            st.warning(f"Cannot find data for {single_code}")


# ═══════════════════════════ US TAB ═══════════════════════════
with us_tab:
    col_side, col_main = st.columns([1, 4], vertical_alignment="top")
    with col_side:
        st.header("Filters")
        us_cat = st.selectbox("Category", list(US_CATS.keys()), key="us_cat")
        us_grade = st.multiselect("Grade", ["A","B","C","D"], default=["A","B","C","D"], key="us_grade")
        us_score_min = st.slider("Score Min", 0, 1000, 0, key="us_score")
        us_rsi_max = st.slider("RSI Max", 30, 100, 100, key="us_rsi")
        us_macd_filter = st.checkbox("排除 MACD < 0", value=False, key="us_macd_filter")
        codes = US_CATS.get(us_cat, [])
        st.info(f"{len(codes)} stocks")
        analyze_us = st.button("Analyze", type="primary", use_container_width=True, key="btn_us_analyze")

    if 'us_results' not in st.session_state:
        st.session_state.us_results = None
        st.session_state.us_filtered = None
        st.session_state.us_cat_saved = None

    if analyze_us:
        with st.spinner("Analyzing..."):
            results = []
            bar = st.progress(0)
            for i, code in enumerate(codes):
                r = analyze(code, 'US')
                if r:
                    results.append(r)
                bar.progress((i+1) / len(codes))
                time.sleep(0.12)
            bar.empty()
            filtered = [r for r in results
                        if r['rsi'] <= us_rsi_max
                        and r['tier'] in us_grade
                        and r['score'] >= us_score_min
                        and (not us_macd_filter or r['macd_hist'] >= 0)]
            filtered.sort(key=lambda x: x['score'], reverse=True)
            st.session_state.us_results = results
            st.session_state.us_filtered = filtered
            st.session_state.us_cat_saved = us_cat

    results = st.session_state.us_results
    filtered = st.session_state.us_filtered
    cat_saved = st.session_state.us_cat_saved

    if results:
        a = sum(1 for r in filtered if r['tier'] == 'A')
        b = sum(1 for r in filtered if r['tier'] == 'B')
        c = sum(1 for r in filtered if r['tier'] == 'C')
        d = sum(1 for r in filtered if r['tier'] == 'D')
        bull = sum(1 for r in filtered if r['bullish'] == 'Y')
        kd = sum(1 for r in filtered if r['kd_golden'])
        avg_score = sum(r['score'] for r in filtered) / len(filtered) if filtered else 0
        m = st.columns(7)
        m[0].metric("A", a)
        m[1].metric("B", b)
        m[2].metric("C", c)
        m[3].metric("D", d)
        m[4].metric("BULL", bull)
        m[5].metric("KD+", kd)
        m[6].metric("Avg Score", f"{avg_score:.0f}")
        st.success(f"{len(results)} stocks | {len(filtered)} after filter")

    if filtered:
        rows = []
        for r in filtered:
            rows.append({
                "Score": f"{r['score']:.0f}",
                "Code": r['code'],
                "Name": r['name'],
                "Price": f"${r['price']:.2f}",
                "Chg%": f"{r['chg']:+.2f}%",
                "RSI": f"{r['rsi']:.0f}",
                "K": f"{r['k']:.0f}",
                "D": f"{r['d']:.0f}",
                "BB%": f"{r['bb_pct']:.0f}%",
                "BIAS5": f"{r['bias5']:+.1f}%",
                "Vol": f"{r['vol_ratio']:.1f}x",
                "MA": "Y" if r['ma20_above_ma60'] else "N",
                "Tier": r['tier'],
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400, hide_index=True)

        with st.expander("Send to Telegram"):
            grade_filter = st.multiselect("Grade Filter", ["A","B","C","D"], default=["A","B","C","D"], key="us_grade_send")
            grade_filtered = [r for r in filtered if r['tier'] in grade_filter]
            sel = st.multiselect("Select", [f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" for r in grade_filtered], key="us_sel")
            sel_rows = [r for r in grade_filtered if f"[{r['tier']}] S={r['score']:.0f} {r['code']} ${r['price']:.0f}" in sel]
            sc = len(sel_rows)
            r1, r2 = st.columns(2)
            if r1.button(f"Send ({sc}) Grade {','.join(grade_filter)}", disabled=(sc==0), use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(sel_rows, f"US-{cat_saved} ({','.join(grade_filter)})")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {sc} stocks ({len(chunks)} msgs)")
            if r2.button(f"Send All ({len(grade_filtered)}) Grade {','.join(grade_filter)}", use_container_width=True):
                with st.spinner("Sending..."):
                    chunks = format_telegram(grade_filtered, f"US-{cat_saved} ({','.join(grade_filter)})")
                    ok_all = True
                    for chunk in chunks:
                        ok, err = push_telegram(chunk)
                        if not ok:
                            ok_all = False
                            st.error(f"Error: {err}")
                            break
                    if ok_all:
                        st.success(f"Sent {len(grade_filtered)} stocks ({len(chunks)} msgs)")

        if results:
            csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')
            st.download_button("CSV", csv, f"us_{cat_saved}_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="us_csv")
    # --- Single Stock Deep Analysis ---
    st.divider()
    st.subheader("Single Stock Deep Analysis")
    col_code, col_btn = st.columns([2, 1])
    with col_code:
        us_single_code = st.text_input("Stock Code", "NVDA", key="us_single_code").strip().upper()
    with col_btn:
        st.write(" ")
        do_us_single = st.button("Analyze", type="primary", use_container_width=True, key="btn_us_single")
    if do_us_single:
        with st.spinner(f"Analyzing {us_single_code}..."):
            r = analyze(us_single_code, "US")
        if r:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Price", f"${r['price']:.2f}")
            m2.metric("Change", f"{r['chg']:+.2f}%")
            m3.metric("RSI", f"{r['rsi']:.0f}")
            m4.metric("Tier", r['tier'])
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("K", f"{r['k']:.0f}")
            m2.metric("D", f"{r['d']:.0f}")
            m3.metric("BB%", f"{r['bb_pct']:.0f}%")
            m4.metric("BIAS5", f"{r['bias5']:+.1f}%")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("MA20", f"${r['ma20']:.0f}")
            m2.metric("MA60", f"${r['ma60']:.0f}" if r['ma60'] else "N/A")
            m3.metric("Vol Ratio", f"{r['vol_ratio']:.1f}x")
            m4.metric("MACD Hist", f"{r['macd_hist']:+.2f}")
            sigs = []
            if r['kd_golden']: sigs.append("KD Golden Cross")
            if r['ma20_above_ma60']: sigs.append("MA Bullish")
            if r['macd_hist'] > 0: sigs.append("MACD+")
            if r['bb_pct'] < 20: sigs.append("BB Oversold")
            if r['rsi'] < 35: sigs.append("RSI Oversold")
            if r['rsi'] > 70: sigs.append("RSI Overbought")
            st.caption(" | ".join(sigs) if sigs else "No special signals")
        else:
            st.warning(f"Cannot find data for {us_single_code}")


st.divider()
st.caption("Data: yfinance + FinMind Institutional | Tina Brain v3.0 — 1000 Tech Score | For reference only")