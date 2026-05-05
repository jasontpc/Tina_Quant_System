# -*- coding: utf-8 -*-
"""美股歷史資料庫擴充"""
import sys, sqlite3, os, yfinance
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\data'

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))

def expand_us_history():
    print('=== 擴充美股歷史資料庫 ===\n')
    
    db = f'{DATA_DIR}\\us_history.db'
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    NEW_STOCKS = [
        ('AVGO', 'Broadcom'), ('ORCL', 'Oracle'), ('IBM', 'IBM'),
        ('INFY', 'Infosys'), ('TXN', 'Texas Instr'), ('QCOM', 'Qualcomm'),
        ('NOW', 'ServiceNow'), ('SNOW', 'Snowflake'), ('TEAM', 'Atlassian'),
        ('DOCU', 'DocuSign'), ('ZM', 'Zoom'), ('OKTA', 'Okta'),
        ('CRWD', 'CrowdStrike'), ('NET', 'Cloudflare'), ('PLTR', 'Palantir'),
        ('BLK', 'BlackRock'), ('SCHW', 'Charles Schwab'), ('COF', 'Capital One'),
        ('USB', 'US Bancorp'), ('PNC', 'PNC'),
        ('SLB', 'Schlumberger'), ('EOG', 'EOG Resources'), ('MPC', 'Marathon'),
        ('CAT', 'Caterpillar'), ('DE', 'John Deere'), ('BA', 'Boeing'),
        ('HON', 'Honeywell'), ('UNP', 'Union Pacific'), ('CSX', 'CSX'),
        ('UNH', 'UnitedHealth'), ('ABBV', 'AbbVie'), ('MRK', 'Merck'),
        ('LLY', 'Eli Lilly'), ('TMO', 'Thermo Fisher'), ('DHR', 'Danaher'),
        ('AMGN', 'Amgen'), ('PFE', 'Pfizer'), ('BMY', 'Bristol-Myers'),
        ('NKE', 'Nike'), ('SBUX', 'Starbucks'), ('MCD', "McDonald's"),
        ('DIS', 'Disney'), ('CMCSA', 'Comcast'),
        ('AMD', 'AMD'), ('INTC', 'Intel'), ('NVDA', 'Nvidia'),
        ('MSFT', 'Microsoft'), ('AMZN', 'Amazon'), ('GOOGL', 'Google'),
        ('META', 'Meta'), ('TSLA', 'Tesla'), ('NFLX', 'Netflix'),
        ('CRM', 'Salesforce'), ('ADBE', 'Adobe'), ('PYPL', 'PayPal'),
        ('UBER', 'Uber'), ('LYFT', 'Lyft'), ('SPOT', 'Spotify'),
        ('SPY', 'S&P 500'), ('QQQ', 'Nasdaq'), ('IWM', 'Russell'),
        ('DIA', 'Dow Jones'), ('VTI', 'Vanguard Total'),
        ('VGT', 'Vanguard Tech'), ('VFH', 'Vanguard Fin'),
        ('XLK', 'Tech ETF'), ('XLV', 'Health ETF'), ('XLE', 'Energy ETF'),
        ('XLF', 'Financial ETF'), ('XLY', 'Consumer ETF'),
        ('SMH', 'Semi ETF'), ('SOXX', 'Semi ETF'), ('ARKK', 'ARK'),
        ('TQQQ', 'Nasdaq 3x'), ('SQQQ', 'Nasdaq -3x'), ('SPXL', 'S&P 3x'),
    ]
    
    added = 0
    for sym, name in NEW_STOCKS:
        try:
            cur.execute('SELECT COUNT(*) FROM stock_summary WHERE symbol=?', (sym,))
            if cur.fetchone()[0] > 0:
                continue
            
            print(f'+ {sym} {name}...', end='', flush=True)
            
            t = yfinance.Ticker(sym)
            hist = t.history(period='3y')
            
            if len(hist) < 500:
                print(f' 不足({len(hist)})')
                continue
            
            closes = hist['Close'].tolist()
            highs = hist['High'].tolist()
            lows = hist['Low'].tolist()
            dates = hist.index.strftime('%Y-%m-%d').tolist()
            
            for i in range(len(hist)):
                row = hist.iloc[i]
                close = row['Close']
                high = row['High']
                low = row['Low']
                open_ = row['Open']
                vol = row['Volume']
                
                # SMA
                sma_20 = sum(closes[max(0,i-19):i+1]) / min(20, i+1) if i >= 0 else close
                sma_60 = sum(closes[max(0,i-59):i+1]) / min(60, i+1) if i >= 0 else close
                sma_120 = sum(closes[max(0,i-119):i+1]) / min(120, i+1) if i >= 0 else close
                
                # EMA
                ema_12 = close
                ema_26 = close
                
                # RSI
                rsi_14 = calc_rsi(closes[:i+1], 14)
                rsi_7 = calc_rsi(closes[:i+1], 7)
                rsi_28 = calc_rsi(closes[:i+1], 28)
                
                # MACD
                ema12 = close
                ema26 = close
                if len(closes[:i+1]) >= 26:
                    k12 = 2/(12+1)
                    k26 = 2/(26+1)
                    ema12 = sum([closes[max(0,i-11+j)]*k12*((1-k12)**(11-j)) for j in range(min(12, i+1))])
                    ema26 = sum([closes[max(0,i-25+j)]*k26*((1-k26)**(25-j)) for j in range(min(26, i+1))])
                macd_line = ema12 - ema26
                macd_signal = macd_line
                macd_hist = 0
                
                # BB
                period = 20
                start = max(0, i-period+1)
                slice_ = closes[start:i+1]
                sma20 = sum(slice_)/len(slice_) if slice_ else close
                std = (sum([(c-sma20)**2 for c in slice_])/len(slice_))**0.5 if slice_ else 0
                bb_upper = sma20 + 2*std
                bb_middle = sma20
                bb_lower = sma20 - 2*std
                
                # ATR
                atr_14 = 0
                if i > 0:
                    trs = [max(highs[j]-lows[j], abs(highs[j]-closes[j-1]), abs(lows[j]-closes[j-1])) for j in range(max(1,i-12), i+1)]
                    atr_14 = sum(trs)/len(trs) if trs else 0
                
                # KDJ
                kdj_k = 50
                kdj_d = 50
                kdj_j = 50
                
                # CCI
                cci_14 = 0
                
                # Zone
                if rsi_14 < 30:
                    zone = 'OVERSOLD'
                elif rsi_14 < 40:
                    zone = 'NEUTRAL_LOW'
                elif rsi_14 < 70:
                    zone = 'NEUTRAL'
                else:
                    zone = 'OVERBOUGHT'
                
                cur.execute('INSERT OR IGNORE INTO daily_ohlcv (symbol, date, open, high, low, close, volume, sma_20, sma_60, sma_120, ema_12, ema_26, rsi_14, rsi_7, rsi_28, macd_line, macd_signal, macd_hist, bb_upper, bb_middle, bb_lower, atr_14, kdj_k, kdj_d, kdj_j, cci_14, zone, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (sym, dates[i], open_, high, low, close, vol, sma_20, sma_60, sma_120, ema_12, ema_26, rsi_14, rsi_7, rsi_28, macd_line, macd_signal, macd_hist, bb_upper, bb_middle, bb_lower, atr_14, kdj_k, kdj_d, kdj_j, cci_14, zone, dates[i]))
            
            conn.commit()
            
            rsi = calc_rsi(closes)
            high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
            low_52w = min(closes[-252:]) if len(closes) >= 252 else min(closes)
            zone = 'OVERSOLD' if rsi < 30 else 'NEUTRAL_LOW' if rsi < 40 else 'NEUTRAL' if rsi < 70 else 'OVERBOUGHT'
            
            cur.execute('INSERT OR REPLACE INTO stock_summary (symbol, name, sector, current_price, current_rsi, current_zone, high_52w, low_52w, total_records, last_updated) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (sym, name, 'US_STOCK', closes[-1], rsi, zone, high_52w, low_52w, len(hist), dates[-1]))
            conn.commit()
            
            print(f' {len(hist)}筆')
            added += 1
            
        except Exception as e:
            print(f' ERR: {e}')
    
    conn.close()
    print(f'\n新增 {added} 檔股票')
    return added

def main():
    print('=== 美股資料庫擴充 ===')
    added = expand_us_history()
    print(f'\n完成: 新增{added}檔')

if __name__ == '__main__':
    main()