# -*- coding: utf-8 -*-
"""
Ray Alert Agent — 主動推播功能
功能：
  - 每 30 分鐘檢查一次所有監控 ETF
  - 當 ETF 近1年位置低於 60% 發送推播
  - 當 ETF 出現「建議進場」信號時發送推播
  - 根據位置分級：< 50% 積極(紅), 50-60% 正常(黃), > 70% 觀望(綠)

用法（由 Cron 調用）:
  python teams/ray/ray_alert_agent.py

Cron 設定:
  openclaw cron add
  Name: Ray DCA 即時監控
  Every: 1800000ms (30分鐘)
  Message: Ray DCA 即時監控 — 檢查所有ETF位置，低於60%時主動推播進場機會
  Timeout: 120 秒
  Announce: 是，to 1616824689
"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# 載入 .env
ENV_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8614615741:AAHEMV6daIzF6J_MFUAm8KkhJYtOGVOM14Q')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1616824689')

import requests
import json
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================================
# ETF 設定
# ============================================================
MAJOR_ETFS = [
    '0050', '0056', '00878', '00881', '00891',
    '00915', '00919', '00923', '00927',
    '00713', '00646', '00662', '00757',
    '00762', '00895'
]

ETF_NAMES = {
    '0050': '元大台灣50', '0056': '元大高股息', '00878': '國泰永續高息',
    '00881': '國泰台灣5G', '00891': '中信低碳', '00915': '富邦台灣永續高息',
    '00919': '群益台灣精選', '00923': '群益台灣ESG低碳', '00927': '統一手創未來',
    '00713': '元大高息低波', '00646': '富邦S&P500', '00662': '富邦NASDAQ',
    '00757': '統一大FANG+', '00762': '元大石油', '00895': '富邦上証'
}

FINMIND_TOKEN = os.getenv('FINMIND_TOKEN', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiSm9qbzg4OCIsImVtYWlsIjoiYnJpYW4wMjYwQGdtYWlsLmNvbSJ9.oCdQO1qNRUCYxHZSVuRQCqlF7X2DbQ77wury5ARCKzM')
FINMIND_URL = 'https://api.finmindtrade.com/api/v4/data'

# ============================================================
# 路徑設定
# ============================================================
WORKSPACE = r'C:\Users\USER\.openclaw\workspace'
RAY_TEAMS_DIR = os.path.dirname(__file__)  # ...\teams\ray
RAY_ROOT_DIR = os.path.dirname(RAY_TEAMS_DIR)  # ...\Tina_Quant_System
MEMORY_DIR = os.path.join(WORKSPACE, 'memory')
RAY_ALERTS_FILE = os.path.join(MEMORY_DIR, 'Ray_alerts.md')
RAY_STATUS_FILE = os.path.join(MEMORY_DIR, 'Ray_status.md')

os.makedirs(MEMORY_DIR, exist_ok=True)

# ============================================================
# Telegram 發送
# ============================================================
def send_telegram(text: str, parse_mode='Markdown') -> bool:
    """發送 Telegram 訊息"""
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': parse_mode
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return True
        else:
            print(f'[Ray Alert] Telegram 發送失敗: {r.text}')
            return False
    except Exception as e:
        print(f'[Ray Alert] Telegram 異常: {e}')
        return False

# ============================================================
# 資料取得
# ============================================================
def get_etf_data(etf_id: str) -> Optional[Dict]:
    """取得單一 ETF 價值評估資料"""
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        close = close.dropna()
        if len(close) < 30:
            return None
    except Exception:
        return None

    price = float(close.iloc[-1])
    low = float(close.min())
    high = float(close.max())
    avg = float(close.mean())
    position_pct = round((price - low) / (high - low) * 100, 1) if high > low else 50.0

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = round(float((100 - (100 / (1 + rs))).iloc[-1]), 1)

    # 法人
    fi_net = 0
    it_net = 0
    try:
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        params = {
            'dataset': 'TaiwanStockInstitutionalInvestorsBuySell',
            'data_id': etf_id,
            'start_date': start,
            'end_date': end,
            'token': FINMIND_TOKEN
        }
        r = requests.get(FINMIND_URL, params=params, timeout=10)
        data = r.json().get('data', [])
        fi_net = sum(item['buy'] - item['sell'] for item in data if item['name'] == 'Foreign_Investor')
        it_net = sum(item['buy'] - item['sell'] for item in data if item['name'] == 'Investment_Trust')
    except Exception:
        pass

    # 5日表現
    recent_5d = close.tail(5)
    recent_5d_pct = round(float((recent_5d.iloc[-1] / recent_5d.iloc[0] - 1) * 100), 2) if len(recent_5d) >= 2 else 0.0

    return {
        'etf_id': etf_id,
        'name': ETF_NAMES.get(etf_id, etf_id),
        'price': price,
        'low_1y': low,
        'high_1y': high,
        'avg_1y': avg,
        'position_pct': position_pct,
        'rsi': rsi,
        'fi_net': fi_net,
        'it_net': it_net,
        'recent_5d_pct': recent_5d_pct
    }


def calc_dca_score(data: Dict) -> float:
    """計算 DCA 價值分數 (0-100)"""
    score = 50.0
    pos = data['position_pct']
    score += (50 - pos) * 0.5

    fi = data['fi_net'] / 1_000_000
    if fi > 0:
        score += min(fi, 500) * 0.02
    elif fi < -200:
        score -= 5

    it = data['it_net'] / 1_000_000
    if it > 0:
        score += min(it, 200) * 0.025

    rsi = data['rsi']
    if rsi < 40:
        score += 10
    elif rsi < 50:
        score += 5
    elif rsi > 75:
        score -= 5

    recent = data['recent_5d_pct']
    if recent < -5:
        score += 7.5
    elif recent < -2:
        score += 4
    elif recent > 10:
        score -= 5

    return max(0.0, min(100.0, round(score, 1)))


def get_alert_level(position_pct: float) -> tuple:
    """根據位置回傳警示等級 (等級, 顏色emoji, 說明)"""
    if position_pct < 50:
        return ('積極進場', '🔴', f'極佳進場點（位置 {position_pct}%）')
    elif position_pct < 60:
        return ('正常進場', '🟡', f'合理進場點（位置 {position_pct}%）')
    elif position_pct < 70:
        return ('中性觀望', '🟠', f'中性偏高（位置 {position_pct}%）')
    else:
        return ('暫停觀望', '🟢', f'價格偏高（位置 {position_pct}%）')


def get_kline_multiplier(dev_52w: float, dev_26w: float, dev_12w: float) -> tuple:
    """
    根據 K線低點偏離計算 DCA 倍數與警示等級
    返回: (dca_multiplier, alert_emoji, alert_desc)
    """
    if dev_52w < 3:
        return (2.0, '🔴', f'極佳DCA買點（偏離52W {dev_52w:+.2f}%，×2.0）')
    elif dev_26w < 5:
        return (1.5, '🟡', f'良好DCA買點（偏離26W {dev_26w:+.2f}%，×1.5）')
    elif dev_12w < 5:
        return (1.2, '🟡', f'普通DCA買點（偏離12W {dev_12w:+.2f}%，×1.2）')
    elif dev_52w > 25:
        return (0.5, '🟢', f'觀望（偏離52W {dev_52w:+.2f}%，×0.5）')
    else:
        return (1.0, '🟢', f'正常DCA（×1.0）')



def get_etf_kline_low_points(etf_id: str) -> Optional[Dict]:
    """
    取得 K線低點偏離資料
    返回: dict 含 deviation_52w, deviation_26w, deviation_12w, dca_multiplier
    """
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        close = close.dropna()
        if len(close) < 60:
            return None
    except Exception:
        return None

    current_price = float(close.iloc[-1])

    # 52週低點
    low_52w = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())
    # 26週低點
    low_26w = float(close.tail(126).min()) if len(close) >= 126 else float(close.min())
    # 12週低點
    low_12w = float(close.tail(60).min()) if len(close) >= 60 else float(close.min())

    dev_52w = round((current_price - low_52w) / low_52w * 100, 2) if low_52w > 0 else 0
    dev_26w = round((current_price - low_26w) / low_26w * 100, 2) if low_26w > 0 else 0
    dev_12w = round((current_price - low_12w) / low_12w * 100, 2) if low_12w > 0 else 0

    mult, emoji, desc = get_kline_multiplier(dev_52w, dev_26w, dev_12w)

    return {
        'etf_id': etf_id,
        'name': ETF_NAMES.get(etf_id, etf_id),
        'current_price': current_price,
        'low_52w': low_52w,
        'low_26w': low_26w,
        'low_12w': low_12w,
        'deviation_52w': dev_52w,
        'deviation_26w': dev_26w,
        'deviation_12w': dev_12w,
        'dca_multiplier': mult,
        'alert_emoji': emoji,
        'alert_desc': desc
    }


def get_kline_multiplier(dev_52w: float, dev_26w: float, dev_12w: float) -> tuple:
    """
    根據 K線低點偏離計算 DCA 倍數與警示等級
    返回: (dca_multiplier, alert_emoji, alert_desc)
    """
    if dev_52w < 3:
        return (2.0, '🔴', f'極佳DCA買點（偏離52W {dev_52w:+.2f}%，×2.0）')
    elif dev_26w < 5:
        return (1.5, '🟡', f'良好DCA買點（偏離26W {dev_26w:+.2f}%，×1.5）')
    elif dev_12w < 5:
        return (1.2, '🟡', f'普通DCA買點（偏離12W {dev_12w:+.2f}%，×1.2）')
    elif dev_52w > 25:
        return (0.5, '🟢', f'觀望（偏離52W {dev_52w:+.2f}%，×0.5）')
    else:
        return (1.0, '🟢', f'正常DCA（×1.0）')



def get_etf_kline_low_points(etf_id: str) -> Optional[Dict]:
    """
    取得 K線低點偏離資料
    返回: dict 含 deviation_52w, deviation_26w, deviation_12w, dca_multiplier
    """
    sym = etf_id + '.TW'
    try:
        h = yf.Ticker(sym).history(period='1y')
        close = h['Close'].squeeze() if isinstance(h['Close'], pd.DataFrame) else h['Close']
        if len(close) < 60:
            return None
    except Exception:
        return None

    current_price = float(close.iloc[-1])

    # 52週低點
    low_52w = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())
    # 26週低點
    low_26w = float(close.tail(126).min()) if len(close) >= 126 else float(close.min())
    # 12週低點
    low_12w = float(close.tail(60).min()) if len(close) >= 60 else float(close.min())

    dev_52w = round((current_price - low_52w) / low_52w * 100, 2) if low_52w > 0 else 0
    dev_26w = round((current_price - low_26w) / low_26w * 100, 2) if low_26w > 0 else 0
    dev_12w = round((current_price - low_12w) / low_12w * 100, 2) if low_12w > 0 else 0

    mult, emoji, desc = get_kline_multiplier(dev_52w, dev_26w, dev_12w)

    return {
        'etf_id': etf_id,
        'name': ETF_NAMES.get(etf_id, etf_id),
        'current_price': current_price,
        'low_52w': low_52w,
        'low_26w': low_26w,
        'low_12w': low_12w,
        'deviation_52w': dev_52w,
        'deviation_26w': dev_26w,
        'deviation_12w': dev_12w,
        'dca_multiplier': mult,
        'alert_emoji': emoji,
        'alert_desc': desc
    }


# ============================================================
# 推播訊息建構
# ============================================================
def build_alert_message(results: List[Dict], alert_etfs: List[Dict], kline_hot_etfs: List[Dict] = None) -> str:
    """建構推播訊息"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = []
    lines.append(f'📡 *Ray DCA 即時監控*')
    lines.append(f'🕐 {now} | 掃描 {len(results)} 檔 ETF')
    lines.append('━' * 20)

    # 只推播低於 60% 的標的
    alert_etfs.sort(key=lambda x: x['position_pct'])

    if not alert_etfs and not kline_hot_etfs:
        lines.append('')
        lines.append('✅ 目前無進場訊號')
        lines.append('所有 ETF 位置 > 60%')
    else:
        lines.append('')
        lines.append(f'🔥 *進場機會 ({len(alert_etfs)} 檔)*')
        lines.append('')
        for e in alert_etfs:
            level, color, desc = get_alert_level(e['position_pct'])
            fi_str = f"{e['fi_net']//1_000_000:+d}M" if abs(e['fi_net']) >= 1_000_000 else f"{e['fi_net']//1000:+d}K"
            it_str = f"{e['it_net']//1_000_000:+d}M" if abs(e['it_net']) >= 1_000_000 else f"{e['it_net']//1000:+d}K"
            lines.append(f'{color} *{e["name"]}* (`{e["etf_id"]}`)')
            lines.append(f'   位置: {e["position_pct"]}% | 等級: {level}')
            lines.append(f'   價格: ${e["price"]:.2f} | RSI: {e["rsi"]}')
            lines.append(f'   近1年: ${e["low_1y"]:.2f} ~ ${e["high_1y"]:.2f}')
            lines.append(f'   外資: {fi_str} | 投信: {it_str}')
            lines.append(f'   5日: {e["recent_5d_pct"]:+.2f}%')
            lines.append('')

        # K線低點推播（×2.0 / ×1.5 標的）
        if kline_hot_etfs:
            lines.append('')
            lines.append(f'📊 *K線低點積極DCA ({len(kline_hot_etfs)} 檔)*')
            lines.append('')
            for e in kline_hot_etfs:
                lines.append(f'{e["alert_emoji"]} *{e["name"]}* (`{e["etf_id"]}`)')
                lines.append(f'   {e["alert_desc"]}')
                lines.append(f'   現價: ${e["current_price"]:.2f} | 52W低: ${e["low_52w"]:.2f}')
                lines.append(f'   偏離52W: {e["deviation_52w"]:+.2f}% | 偏離26W: {e["deviation_26w"]:+.2f}%')
                lines.append(f'   DCA 倍數: ×{e["dca_multiplier"]}')
                lines.append('')

    lines.append('━' * 20)
    lines.append('🤖 Ray Alert | Tina System')

    return '\n'.join(lines)


def log_alert(alert_etfs: List[Dict]):
    """寫入 Ray_alerts.md 記錄"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    if os.path.exists(RAY_ALERTS_FILE):
        with open(RAY_ALERTS_FILE, 'r', encoding='utf-8') as f:
            existing = f.read()
    else:
        existing = f'# Ray DCA Alerts 記錄\n\n'

    entry_lines = [f'\n## {now}\n']
    if not alert_etfs:
        entry_lines.append('- ✅ 無進場訊號（所有 ETF 位置 > 60%）\n')
    else:
        for e in alert_etfs:
            level, color, _ = get_alert_level(e['position_pct'])
            entry_lines.append(f'- {color} `{e["etf_id"]}` {e["name"]} | 位置 {e["position_pct"]}% | {level}\n')

    entry = ''.join(entry_lines)

    # 保留前 100 行（避免檔案過大）
    lines = existing.split('\n')
    if len(lines) > 100:
        lines = lines[:100]
    lines.append(entry)

    with open(RAY_ALERTS_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'[Ray Alert] 記錄已寫入: {RAY_ALERTS_FILE}')


# ============================================================
# 主程式
# ============================================================
def main():
    print(f'\n[Ray Alert] 開始監控 — {datetime.now().strftime("%Y-%m-%d %H:%M")}')
    print(f'[Ray Alert] 掃描 ETF 數量: {len(MAJOR_ETFS)}')

    results = []
    for etf_id in MAJOR_ETFS:
        sys.stdout.write(f'[Ray Alert] 抓取 {etf_id}... ')
        sys.stdout.flush()
        data = get_etf_data(etf_id)
        if data:
            score = calc_dca_score(data)
            data['dca_score'] = score
            results.append(data)
            print(f'OK (位置={data["position_pct"]}%, DCA分={score})')
        else:
            print('失敗')

    print(f'\n[Ray Alert] 掃描完成，共 {len(results)} 檔成功')

    # K線低點資料蒐集
    kline_hot_etfs = []
    for etf_id in MAJOR_ETFS:
        kline_data = get_etf_kline_low_points(etf_id)
        if kline_data and kline_data['dca_multiplier'] >= 1.5:
            kline_hot_etfs.append(kline_data)

    # 只對位置 < 60% 發送推播
    alert_etfs = [r for r in results if r['position_pct'] < 60]

    # 建構訊息（含 K線推播）
    msg = build_alert_message(results, alert_etfs, kline_hot_etfs)

    # 發送推播
    sent = send_telegram(msg)
    if sent:
        print('[Ray Alert] ✅ 推播已發送')
    else:
        print('[Ray Alert] ❌ 推播發送失敗')

    # 記錄
    log_alert(alert_etfs)

    # 同時輸出到 stdout（供 Cron 捕獲）
    print()
    print('━' * 40)
    print(f'Ray Alert 監控完成')
    print(f'掃描: {len(results)} 檔 | 進場機會: {len(alert_etfs)} 檔 | K線積極DCA: {len(kline_hot_etfs)} 檔')
    if alert_etfs:
        for e in alert_etfs:
            level, color, _ = get_alert_level(e['position_pct'])
            print(f'  {color} {e["etf_id"]} {e["name"]} | 位置 {e["position_pct"]}% | {level}')
    if kline_hot_etfs:
        print('  [K線積極DCA]')
        for e in kline_hot_etfs:
            print(f'  {e["alert_emoji"]} {e["etf_id"]} {e["name"]} | ×{e["dca_multiplier"]} | {e["alert_desc"]}')
    print('━' * 40)

    return 0


if __name__ == '__main__':
    sys.exit(main())
