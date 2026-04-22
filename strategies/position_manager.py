"""
Position Manager - 動態倉位管理
根據歷史 PF 值計算倉位乘數

使用方法:
    from position_manager import calculate_target_shares
    
    shares = calculate_target_shares(
        ticker='3017',
        price=2600,
        base_capital=100000,  # 單筆10萬
        history_pf=1.5
    )
"""

import json
import os

# === 路徑設定 ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def load_blacklist():
    """載入黑名單"""
    path = os.path.join(DATA_DIR, 'blacklist.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'blacklist': []}

def get_multiplier(history_pf):
    """
    根據歷史 PF 值取得倉位乘數
    
    Args:
        history_pf: 歷史 Profit Factor
    
    Returns:
        float: 倉位乘數 (0.0 - 1.0)
    """
    if history_pf is None:
        return 0.5  # 預設中型部位
    
    if history_pf >= 1.5:
        return 1.0  # 核心獲利標的
    elif 1.2 <= history_pf < 1.5:
        return 0.75  # 穩健趨勢標的
    elif 1.0 <= history_pf < 1.2:
        return 0.5  # 防禦性配置
    else:
        return 0.0  # PF < 1.0 禁止進場

def get_risk_cap(history_pf):
    """
    取得風險上限 (單筆最大損失)
    
    Args:
        history_pf: 歷史 Profit Factor
    
    Returns:
        float: 最大損失上限 (%)
    """
    if history_pf >= 1.5:
        return 0.10  # 10% 止損
    elif 1.2 <= history_pf < 1.5:
        return 0.08  # 8% 止損
    elif 1.0 <= history_pf < 1.2:
        return 0.05  # 5% 止損 (嚴格)
    else:
        return 0.0  # 禁止進場

def calculate_target_shares(ticker, price, base_capital, history_pf=None, max_positions=5):
    """
    計算目標股數
    
    Args:
        ticker: 股票代碼
        price: 現價
        base_capital: 單筆基礎金額 (TWD)
        history_pf: 歷史 PF 值 (預設 0.5 = 最保守)
        max_positions: 最大持有檔數
    
    Returns:
        dict: {
            'shares': 股數,
            'amount': 投入金額,
            'multiplier': 倉位乘數,
            'risk_cap': 風險上限,
            'approved': 是否核准進場
        }
    """
    # 檢查黑名單
    blacklist_data = load_blacklist()
    for item in blacklist_data.get('blacklist', []):
        if item['symbol'] == ticker:
            return {
                'shares': 0,
                'amount': 0,
                'multiplier': 0,
                'risk_cap': 0,
                'approved': False,
                'reason': f"黑名單: {item.get('reason', 'N/A')}"
            }
    
    # 如果沒有 PF 資料，預設最保守的 50%
    if history_pf is None:
        history_pf = 0.5  # 新股預設最保守
    
    # 計算乘數
    multiplier = get_multiplier(history_pf)
    risk_cap = get_risk_cap(history_pf)
    
    # PF < 1.0 禁止進場
    if history_pf < 1.0:
        return {
            'shares': 0,
            'amount': 0,
            'multiplier': 0,
            'risk_cap': 0,
            'approved': False,
            'reason': f"PF={history_pf} < 1.0 禁止進場"
        }
    
    # 計算投入金額
    invest_amount = base_capital * multiplier
    
    # 計算股數 (取整百股)
    shares = int(invest_amount // price // 100) * 100
    
    return {
        'shares': shares,
        'amount': shares * price,
        'multiplier': multiplier,
        'risk_cap': risk_cap,
        'approved': shares > 0,
        'history_pf': history_pf
    }

def get_position_summary(positions, total_capital):
    """
    取得整體倉位摘要
    
    Args:
        positions: list of position dicts
        total_capital: 總資金
    
    Returns:
        dict: 倉位摘要
    """
    total_invested = sum(p.get('amount', 0) for p in positions)
    position_count = len([p for p in positions if p.get('shares', 0) > 0])
    
    return {
        'total_invested': total_invested,
        'cash': total_capital - total_invested,
        'position_count': position_count,
        'utilization': total_invested / total_capital * 100 if total_capital > 0 else 0
    }

# === 版本資訊 ===
__version__ = '1.0.0'
__author__ = 'Tina Quant'
