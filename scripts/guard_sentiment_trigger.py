# -*- coding: utf-8 -*-
"""
BR-001: GUARD 情資觸發系統
============================
軍工/國防相關新聞情資監控，地緣政治事件驅動
"""
import sqlite3, json, sys, time, re
from pathlib import Path
from datetime import datetime
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE = Path(r"C:\Users\USER\.openclaw\workspace\Tina_Quant_System")
DATA = WORKSPACE / "data"
GUARD_STOCKS = ['2634.TW', '2313.TW']

# 軍工相關關鍵字
GUARD_KEYWORDS = [
    '軍演', '軍演', '軍事', '國防', '戰機', '導彈', '無人機',
    '美軍售', '軍售', '愛國者', 'F16', '魚叉', '刺針',
    '台海', '共機', '軍艦', '航母', '航太', '漢翔', '拓凱',
    '中美', '美中', '制裁', '軍備', '演習', '武力'
]

# 事件強度評估
EVENT_TIERS = {
    'TIER1_IMMINENT': ['共軍演習', '台海危機', '美軍售台', '戰機交付', '導彈試射'],
    'TIER2_HIGH': ['軍事合作', '國防預算', '航母通過', '軍演公告', '無人機軍售'],
    'TIER3_MEDIUM': ['軍事訓練', '軍備採購', '外交訪問', '聯合軍演'],
    'TIER4_LOW': ['國防報告', '政策調整', '軍事評論']
}

TWEETS_DB = DATA / "social_sentiment.db"

def scan_guard_news():
    """掃描軍工相關新聞/社群"""
    mentions = {}

    # 嘗試讀取 social_sentiment.db
    try:
        conn = sqlite3.connect(str(TWEETS_DB))
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in c.fetchall()]

        for tbl in tables:
            try:
                c.execute(f"SELECT content FROM {tbl} ORDER BY rowid DESC LIMIT 100")
                for row in c.fetchall():
                    content = str(row[0]).lower()
                    for kw in GUARD_KEYWORDS:
                        if kw.lower() in content:
                            mentions[kw] = mentions.get(kw, 0) + 1
            except:
                pass
        conn.close()
    except:
        pass

    return mentions

def get_guard_indicators():
    """取得軍工股技術指標"""
    import yfinance as yf
    results = []

    for sym in GUARD_STOCKS:
        try:
            tk = yf.Ticker(sym)
            h = tk.history(period='30d')
            if len(h) < 5:
                continue

            prices = list(h['Close'])
            vols = list(h['Volume'])
            s = pd.Series(prices)

            # RSI
            delta = s.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
            rs = avg_gain / avg_loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # Vol ratio
            vol20 = pd.Series(vols).rolling(20).mean().iloc[-1]
            vol_r = vols[-1] / vol20 if vol20 > 0 else 1.0

            chg_1d = (prices[-1] / prices[-2] - 1) * 100 if len(prices) >= 2 else 0

            results.append({
                'symbol': sym,
                'price': prices[-1],
                'rsi': round(rsi, 1),
                'vol_r': round(vol_r, 2),
                'chg_1d': round(chg_1d, 2),
                'price_level': 'high' if chg_1d > 2 else ('low' if chg_1d < -2 else 'normal')
            })
        except:
            continue

    return results

def event_trigger_score(news_mentions, stock_data):
    """計算事件觸發分數"""
    score = 0
    triggers = []

    total_mentions = sum(news_mentions.values())
    if total_mentions > 20:
        score += 40
        triggers.append('high_social_buzz')
    elif total_mentions > 5:
        score += 20
        triggers.append('moderate_buzz')

    # 檢查是否有高強度關鍵字
    for kw in news_mentions:
        if any(t in kw for t in ['演習', '軍售', '台海', '導彈', '共機']):
            score += 30
            triggers.append(f'critical_keyword:{kw}')
            break

    # 個股技術面確認
    for s in stock_data:
        if s['price_level'] == 'high' and s['rsi'] < 70:
            score += 15
            triggers.append(f'technical_confirm:{s["symbol"]}')

    return score, triggers

def main():
    print('='*60)
    print('  GUARD 情資觸發系統 BR-001')
    print('  ' + datetime.now().strftime('%Y-%m-%d %H:%M'))
    print('='*60)

    mentions = scan_guard_news()
    stocks = get_guard_indicators()

    print('\n【軍工關鍵字提及】')
    if mentions:
        for kw, cnt in sorted(mentions.items(), key=lambda x: -x[1])[:5]:
            print(f'  {kw}: {cnt}次')
    else:
        print('  無社群提及記錄')

    print('\n【軍工股技術面】')
    for s in stocks:
        vol = f"Vol={s['vol_r']}x"
        rsi_icon = '🔴' if s['rsi'] > 75 else ('🟢' if s['rsi'] < 40 else '🟡')
        print(f"  {s['symbol']}: ${s['price']:.2f} RSI={rsi_icon}{s['rsi']} {vol} {s['chg_1d']:+.2f}%")

    score, triggers = event_trigger_score(mentions, stocks)

    print('\n【事件觸發評估】')
    print(f'  觸發分數: {score}/100')
    if triggers:
        for t in triggers:
            print(f'  觸發條件: {t}')
    else:
        print('  無觸發條件')

    if score >= 60:
        verdict = '🟢 積極關注'
        action = '考慮進場，嚴守停損'
    elif score >= 30:
        verdict = '🟡 觀察'
        action = '等待技術面確認'
    else:
        verdict = '⚪ 無信號'
        action = '觀望'

    print(f'  裁決: {verdict}')
    print(f'  建議: {action}')


if __name__ == '__main__':
    main()