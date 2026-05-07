# -*- coding: utf-8 -*-
"""
Ray Autonomous Trader — 真實交易模擬系統（K線版）
功能：
  - 使用 K線分析結果（MA60/MA120/低點）判斷進場策略
  - Buy&Hold：低點一次買入，設定目標價 +20%，停損 -15%
  - Hybrid：50% BH + 50% DCA
  - DCA：正常定期定額（根據 K線低點動態調整倍數 ×0.5~×2.0）
  - 記錄虛擬交易到 autonomous_trades.json
"""
import yfinance as yf
import pandas as pd
import json
import sys
import math
import requests
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\ray')
TRADES_FILE = BASE_DIR / 'autonomous_trades.json'
TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSIsInRva2VuX3ZlcnNpb24iOjF9.ivums9mfJUrM2MYazJiOEg49RiYLOJMZtejqX79YWS8'
FINMIND_URL = 'https://api.finmindtrade.com/api/v4/data'

MONITOR_ETFS = [
    '0050', '0056', '00878', '00891', '00919',
    '00927', '00713', '00646', '00662', '00757',
    '00923', '00915', '00917', '00918', '00920'
]

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00891': '中信低碳', '00919': '群益台灣精選', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00923': '凱基優選高股息', '00915': '兆豐永續高息',
    '00917': '中信關鍵半導體', '00918': '中信上游半導體', '00920': '中信特選金融'
}

BH_TARGET_PCT = 20.0   # Buy&Hold 目標報酬
BH_STOP_LOSS_PCT = -15.0  # Buy&Hold 停損


def get_kline(etf_id, period='2y'):
    """抓取 K線數據（自動清除尾部NaN）"""
    sym = etf_id + '.TW'
    h = yf.Ticker(sym).history(period=period)
    close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
    # 清除尾部 NaN
    close = close.dropna()
    return close


def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def get_institutional(etf_id, lookback=20):
    """抓取法人資料"""
    end = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=lookback)).strftime('%Y-%m-%d')
    params = {
        'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
        'data_id': etf_id,
        'start_date': start,
        'end_date': end,
        'token': TOKEN
    }
    try:
        r = requests.get(FINMIND_URL, params=params, timeout=15)
        return r.json().get('data', [])
    except:
        return []


def get_kline_multiplier(price: float, low_52w: float, low_26w: float, low_12w: float) -> float:
    """
    根據 K線低點偏離計算 DCA 倍數
    規則：
      - 偏離52W < 5%   → ×2.0（極佳買點）
      - 偏離26W < 5%   → ×1.5（良好買點）
      - 偏離12W < 5%   → ×1.2（普通買點）
      - 偏離52W > 20%  → ×0.5（觀望）
      - 其他           → ×1.0（正常）
    """
    dev_52w = (price - low_52w) / low_52w * 100 if low_52w > 0 else 0
    dev_26w = (price - low_26w) / low_26w * 100 if low_26w > 0 else 0
    dev_12w = (price - low_12w) / low_12w * 100 if low_12w > 0 else 0

    if dev_52w < 5:
        return 2.0
    elif dev_26w < 5:
        return 1.5
    elif dev_12w < 5:
        return 1.2
    elif dev_52w > 20:
        return 0.5
    else:
        return 1.0


def analyze_etf_decision(etf_id):
    """
    根據 K線分析執行進場判斷
    規則：
      - 價格 < MA120 → 強制 Buy&Hold（一筆 NT$100,000）
      - 價格 < MA60 → 50% BH + 50% DCA
      - 價格 > MA60 → 純 DCA（根據 K線低點動態調整倍數）
    """
    close = get_kline(etf_id, '2y')
    if len(close) < 60:
        return None

    price = float(close.iloc[-1])

    # 均線
    ma60 = float(close.rolling(60).mean().iloc[-1]) if len(close) >= 60 else None
    ma120 = float(close.rolling(120).mean().iloc[-1]) if len(close) >= 120 else None
    ma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None

    # K線低點（滾動窗口）
    low_52w = float(close.rolling(52).min().iloc[-1]) if len(close) >= 52 else float(close.min())
    low_26w = float(close.rolling(26).min().iloc[-1]) if len(close) >= 26 else float(close.min())
    low_12w = float(close.rolling(12).min().iloc[-1]) if len(close) >= 12 else float(close.min())

    # K線 DCA 倍數
    kline_multiplier = get_kline_multiplier(price, low_52w, low_26w, low_12w)

    # RSI
    rsi = float(calc_rsi(close).iloc[-1])

    # 法人
    inst_data = get_institutional(etf_id)
    fi_buy_days = 0
    for r in inst_data:
        if r.get('name') == 'Foreign_Investor':
            net = r.get('buy', 0) - r.get('sell', 0)
            if net > 0:
                fi_buy_days += 1

    # 1年位置
    if len(close) >= 252:
        low_1y = float(close.tail(252).min())
        high_1y = float(close.tail(252).max())
        pos_1y = (price - low_1y) / (high_1y - low_1y) * 100 if high_1y > low_1y else 50
    else:
        low_1y = float(close.min())
        high_1y = float(close.max())
        pos_1y = 50

    # === 評分（與 Buy&Hold Finder 一致）===
    score = 0
    dev_low_52w = (price - low_52w) / low_52w * 100 if low_52w != 0 else 0
    dev_ma120 = (price - ma120) / ma120 * 100 if ma120 and ma120 != 0 else 0

    if dev_low_52w < 5: score += 5
    elif dev_low_52w < 10: score += 3
    if ma120 and dev_ma120 < 5: score += 5
    elif ma120 and dev_ma120 < 10: score += 3
    if rsi < 30: score += 5
    elif rsi < 40: score += 3
    elif rsi > 70: score -= 3
    if fi_buy_days >= 3: score += 5
    elif fi_buy_days >= 1: score += 2
    if pos_1y < 50: score += 3

    # === 策略判定 ===
    # 優先用評分系統，同時參考均線位置
    if score >= 15:
        strategy = 'BUY&HOLD'
        bh_amount = 100000
        base_dca_amount = 0
        kline_multiplier_bh = 0
        dca_amount = 0
        action = 'BH 進場'
    elif score >= 10:
        strategy = 'HYBRID'
        bh_amount = 50000
        base_dca_amount = 5000
        kline_multiplier_bh = kline_multiplier
        dca_amount = int(base_dca_amount * kline_multiplier_bh)
        action = f'BH 50% + DCA ×{kline_multiplier_bh:.1f}'
    elif ma120 and price < ma120:
        # 均線 fallback
        strategy = 'BUY&HOLD'
        bh_amount = 100000
        dca_amount = 0
        kline_multiplier_bh = 0
        action = 'BH 低點'
    elif ma60 and price < ma60:
        strategy = 'HYBRID'
        bh_amount = 50000
        base_dca_amount = 5000
        kline_multiplier_bh = kline_multiplier
        dca_amount = int(base_dca_amount * kline_multiplier_bh)
        action = f'BH 均線 + DCA ×{kline_multiplier_bh:.1f}'
    else:
        strategy = 'DCA'
        bh_amount = 0
        base_dca_amount = 10000
        kline_multiplier_bh = kline_multiplier
        dca_amount = int(base_dca_amount * kline_multiplier_bh)
        action = f'DCA ×{kline_multiplier_bh:.1f}'

    # Buy&Hold 目標價 / 停損價
    if strategy in ('BUY&HOLD', 'HYBRID'):
        target_price = round(price * (1 + BH_TARGET_PCT / 100), 2)
        stop_price = round(price * (1 + BH_STOP_LOSS_PCT / 100), 2)
    else:
        target_price = None
        stop_price = None

    # 股數計算
    if price and not math.isnan(price):
        bh_shares = int(bh_amount / price) if bh_amount > 0 else 0
        dca_shares = int(dca_amount / price) if dca_amount > 0 else 0
    else:
        bh_shares = 0
        dca_shares = 0

    return {
        'etf_id': etf_id,
        'name': ETF_NAMES.get(etf_id, etf_id),
        'price': round(price, 2),
        'ma20': round(ma20, 2) if ma20 else None,
        'ma60': round(ma60, 2) if ma60 else None,
        'ma120': round(ma120, 2) if ma120 else None,
        'low_52w': round(low_52w, 2),
        'low_26w': round(low_26w, 2),
        'low_12w': round(low_12w, 2),
        'kline_multiplier': kline_multiplier,
        'rsi': round(rsi, 1),
        'pos_1y_pct': round(pos_1y, 1),
        'fi_buy_days': fi_buy_days,
        'score': score,
        'strategy': strategy,
        'action': action,
        'bh_amount': bh_amount,
        'dca_amount': dca_amount,
        'bh_shares': bh_shares,
        'dca_shares': dca_shares,
        'target_price': target_price,
        'stop_price': stop_price,
        'target_pct': BH_TARGET_PCT,
        'stop_loss_pct': BH_STOP_LOSS_PCT,
        'total_cost': round(bh_shares * price + dca_shares * price, 2)
    }


def load_trades():
    if TRADES_FILE.exists():
        try:
            with open(TRADES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'trades': [], 'summary': {}}
    return {'trades': [], 'summary': {}}


def get_recent_trade(etf_id, trade_type, minutes=30):
    """Check if same ETF+type was traded within cooldown window."""
    trades_data = load_trades()
    cutoff = datetime.now() - timedelta(minutes=minutes)
    for t in trades_data.get('trades', []):
        if t.get('etf_id') == etf_id and t.get('type') == trade_type:
            try:
                trade_time = datetime.fromisoformat(t.get('timestamp',''))
                if trade_time >= cutoff:
                    return t
            except:
                pass
    return None


def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def simulate_trading_decisions():
    """模擬所有 ETF 的交易決策"""
    decisions = []
    for etf_id in MONITOR_ETFS:
        r = analyze_etf_decision(etf_id)
        if r:
            decisions.append(r)
    return decisions


def run_autonomous_trader():
    """主執行流程"""
    print('=== Ray 自主交易模擬系統（K線版）===')
    print(f'時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print()
    print(f'策略參數：目標報酬 +{BH_TARGET_PCT}%，停損 {BH_STOP_LOSS_PCT}%')
    print()

    # Step 1: 分析所有 ETF
    print('[Step 1] K線分析 — 15檔ETF')
    decisions = simulate_trading_decisions()
    print(f'  完成 {len(decisions)} 檔')
    print()

    # Step 2: 依評分排序輸出
    print('[Step 2] Buy&Hold 評分排序')
    decisions_sorted = sorted(decisions, key=lambda x: x['score'], reverse=True)
    print(f'  {"ETF":<8s} {"名稱":<10s} {"評分":>5s} {"策略":<10s} {"行動":<20s} {"BH金額":>9s} {"DCA":>8s} {"目標價":>8s} {"停損價":>8s}')
    print('  ' + '-' * 105)
    for d in decisions_sorted:
        target = f'${d["target_price"]:.2f}' if d['target_price'] else '-'
        stop = f'${d["stop_price"]:.2f}' if d['stop_price'] else '-'
        print(f'  {d["etf_id"]:<8s} {d["name"]:<10s} {d["score"]:>4d}  {d["strategy"]:<10s} {d["action"]:<20s} {d["bh_amount"]:>8d} {d["dca_amount"]:>7d} {target:>8s} {stop:>8s}')
    print()

    # Step 3: 分策略統計
    bh_dec = [d for d in decisions if d['strategy'] == 'BUY&HOLD']
    hy_dec = [d for d in decisions if d['strategy'] == 'HYBRID']
    dca_dec = [d for d in decisions if d['strategy'] == 'DCA']

    print('[Step 3] 策略分組')
    print(f'  Buy&Hold: {len(bh_dec)} 檔')
    for d in bh_dec:
        print(f'    {d["name"]} — BH NT${d["bh_amount"]:,}，目標 ${d["target_price"]:.2f}，停損 ${d["stop_price"]:.2f}')
    print(f'  混合策略: {len(hy_dec)} 檔')
    for d in hy_dec:
        print(f'    {d["name"]} — BH NT${d["bh_amount"]:,} + DCA NT${d["dca_amount"]:,}/月（×{d["kline_multiplier"]:.1f}）')
    print(f'  純 DCA: {len(dca_dec)} 檔')
    for d in dca_dec:
        print(f'    {d["name"]} — DCA NT${d["dca_amount"]:,}/月（×{d["kline_multiplier"]:.1f}）')
    print()

    # Step 4: 更新交易記錄
    trades_data = load_trades()
    now = datetime.now()

    # 新增 Buy&Hold 進場記錄（防重複：30分鐘內同ETF同type不重複）
    for d in decisions:
        if d['bh_shares'] > 0:
            if get_recent_trade(d['etf_id'], 'BUY&HOLD', minutes=30):
                print(f'  [冷卻] {d["etf_id"]} Buy&Hold 30分鐘內已記錄，跳過')
            else:
                trade = {
                    'trade_id': f"BH_{d['etf_id']}_{now.strftime('%Y%m%d%H%M%S')}",
                    'timestamp': now.isoformat(),
                    'etf_id': d['etf_id'],
                    'name': d['name'],
                    'type': 'BUY&HOLD',
                    'action': d['action'],
                    'price': d['price'],
                    'shares': d['bh_shares'],
                    'amount': d['bh_amount'],
                    'target_price': d['target_price'],
                    'stop_price': d['stop_price'],
                    'target_pct': d['target_pct'],
                    'stop_loss_pct': d['stop_loss_pct'],
                    'score': d['score'],
                    'strategy': d['strategy']
                }
                trades_data['trades'].append(trade)

        if d['dca_shares'] > 0:
            if get_recent_trade(d['etf_id'], 'DCA', minutes=30):
                print(f'  [冷卻] {d["etf_id"]} DCA 30分鐘內已記錄，跳過')
            else:
                trade = {
                    'trade_id': f"DCA_{d['etf_id']}_{now.strftime('%Y%m%d%H%M%S')}",
                    'timestamp': now.isoformat(),
                    'etf_id': d['etf_id'],
                    'name': d['name'],
                    'type': 'DCA',
                    'action': d['action'],
                    'price': d['price'],
                    'shares': d['dca_shares'],
                    'amount': d['dca_amount'],
                    'kline_multiplier': d.get('kline_multiplier', 1.0),
                    'reason': f"K線×{d.get('kline_multiplier', 1.0):.1f} | DCA×{d.get('kline_multiplier', 1.0):.1f}",
                    'score': d['score'],
                    'strategy': d['strategy']
                }
                trades_data['trades'].append(trade)

    trades_data['last_update'] = now.isoformat()
    trades_data['strategy'] = 'KLINE_BASED'
    save_trades(trades_data)
    print(f'[Step 5] 記錄已儲存到 {TRADES_FILE}')
    print()

    # Step 5: 摘要
    print('[Step 6] 本輪操作摘要')
    bh_total = sum(d['bh_amount'] for d in decisions)
    dca_total = sum(d['dca_amount'] for d in decisions)
    print(f'  Buy&Hold 進場: {len(bh_dec)} 檔，總金額 NT${bh_total:,}')
    print(f'  DCA 月預算: {len(dca_dec)} 檔，NT${dca_total:,}/月')
    print()
    print('=== 模擬完成 ===')

    return trades_data


if __name__ == '__main__':
    run_autonomous_trader()
