"""
VIF 計算工具 - Tina Quant System
計算成交量指標 (Volume Increase Factor)
"""

import sys
sys.path.insert(0, __file__.replace('filters.py', '../api'))

try:
    from twse_api_complete import get_all_stocks_today
except:
    get_all_stocks_today = None

def calc_vif(volume_today, volume_ma20):
    """
    計算 VIF (Volume Increase Factor)
    
    VIF = 當日成交量 / 20日平均成交量
    
    Args:
        volume_today: 當日成交量
        volume_ma20: 20日平均成交量
    
    Returns:
        float: VIF 值
        int: VIF 等級 (0-3)
    """
    if volume_ma20 <= 0:
        return 0, 0
    
    vif = volume_today / volume_ma20
    
    # 等級
    if vif >= 2.5:
        grade = 3  # 非常強
    elif vif >= 2.0:
        grade = 2  # 強
    elif vif >= 1.5:
        grade = 1  # 中等
    else:
        grade = 0  # 不足
    
    return vif, grade

def check_vif_grade(vif):
    """
    檢查 VIF 等級
    
    Args:
        vif: VIF 值
    
    Returns:
        bool: True = 通過 (VIF >= 1.5)
        str: 等級說明
    """
    if vif >= 2.5:
        return True, "VIF 非常強 (>=2.5) ✅"
    elif vif >= 2.0:
        return True, "VIF 強 (2.0-2.5) ✅"
    elif vif >= 1.5:
        return True, "VIF 中等 (1.5-2.0) ⚠️"
    else:
        return False, "VIF 不足 (<1.5) ❌"

# === VIF 閾值設定 ===
VIF_THRESHOLD = 1.5  # 最低門檻
VIF_OPTIMAL = 2.0     # 理想門檻

def should_filter_by_vif(vif, use_conservative=False):
    """
    根據 VIF 判斷是否要過濾
    
    Args:
        vif: VIF 值
        use_conservative: 是否使用嚴格模式 (VIF >= 2.0)
    
    Returns:
        bool: True = 過濾, False = 通過
    """
    threshold = VIF_OPTIMAL if use_conservative else VIF_THRESHOLD
    return vif < threshold

# === 版本資訊 ===
__version__ = '3.12.1'
__author__ = 'Tina Quant'
