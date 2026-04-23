# -*- coding: utf-8 -*-
"""
Position Sizing Module - Tina Quant System
Kelly Criterion + 風險管理

用法:
    from utils.position_sizing import PositionSizer
    sizer = PositionSizer(capital=2_000_000)
    size = sizer.calc_size(code='3017', win_rate=0.75, avg_win=0.05, avg_loss=-0.03)
    print(f"建議買入: {size['shares']} 股, 金額: {size['amount']:,}")
"""

import json
import math
from datetime import datetime
from pathlib import Path

# === 路徑設定 ===
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
BACKTEST_FILE = BASE_DIR / 'backtest' / 'v3x_full_results.json'
LOSS_RULES_FILE = DATA_DIR / 'loss_rules.json'

# === 預設參數 ===
DEFAULT_SINGLE_MAX_PCT = 0.20    # 單檔最大 20% 曝險
DEFAULT_PORTFOLIO_MAX = 5        # 最多同時持有 5 檔
DEFAULT_STOP_LOSS_PCT = 0.05     # 預設停損 5%

# === 歷史資料快取 ===
_hist_cache = {}

def load_backtest_data():
    """載入回測歷史資料"""
    if 'backtest' in _hist_cache:
        return _hist_cache['backtest']
    try:
        with open(BACKTEST_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _hist_cache['backtest'] = data
        return data
    except Exception:
        return {}

def get_stock_history(code):
    """取得股票歷史交易資料"""
    data = load_backtest_data()
    # 嘗試 H2_2025 + Q1_2026 合併
    h2 = data.get('H2_2025', {}).get(code, {})
    q1 = data.get('Q1_2026', {}).get(code, {})
    
    trades = []
    if h2:
        trades.append({'wr': h2.get('wr', 0), 'avg': h2.get('avg', 0), 't': h2.get('t', 0)})
    if q1:
        trades.append({'wr': q1.get('wr', 0), 'avg': q1.get('avg', 0), 't': q1.get('t', 0)})
    
    return trades

def get_loss_rule(code):
    """取得個人股票停損規則"""
    try:
        if Path(LOSS_RULES_FILE).exists():
            with open(LOSS_RULES_FILE, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            return rules.get(code, {})
    except Exception:
        pass
    return {}

# === Kelly Criterion 核心 ===

def calc_kelly_fractional(win_rate, avg_win_pct, avg_loss_pct, fraction=0.5):
    """
    計算 Fractional Kelly 部位
    
    Formula: f* = (b * p - q) / b
            where b = avg_win / |avg_loss|, p = win_rate, q = 1 - p
    
    套用 fraction (0.5 = Half-Kelly) 降低波動
    
    Args:
        win_rate: 勝率 (0-1)
        avg_win_pct: 平均獲利 (正數, 如 0.05 = 5%)
        avg_loss_pct: 平均虧損 (正數, 如 0.03 = 3%)
        fraction: Kelly 分數 (1=Full, 0.5=Half, 0.25=Quarter)
    
    Returns:
        float: 建議部位比例 (0-1)
    """
    if avg_loss_pct <= 0 or win_rate <= 0 or win_rate >= 1:
        return 0.0
    
    b = avg_win_pct / avg_loss_pct   # 盈虧比
    p = win_rate
    q = 1 - p
    
    # Full Kelly
    kelly = (b * p - q) / b
    
    # 檢查 kelly 是否為正
    if kelly <= 0:
        return 0.0
    
    return kelly * fraction

def calc_hybrid_kelly(win_rate, avg_win_pct, avg_loss_pct, 
                      inst_buy_pct=0, fraction=0.5, 
                      confidence_boost=0.1):
    """
    混合 Kelly：結合歷史 + 法人動能 + 信心調整
    
    Args:
        win_rate: 歷史勝率
        avg_win_pct: 平均獲利 %
        avg_loss_pct: 平均虧損 %
        inst_buy_pct: 法人買超比例 (0-1)
        fraction: Kelly 分數
        confidence_boost: 信心加成 (0-0.2)
    
    Returns:
        float: 調整後部位比例
    """
    kelly = calc_kelly_fractional(win_rate, avg_win_pct, avg_loss_pct, fraction=1.0)
    
    # 法人加成 (最多額外 10%)
    if inst_buy_pct > 0.5:
        inst_adj = min(confidence_boost, inst_buy_pct * 0.15)
    else:
        inst_adj = 0
    
    # 信心加成 (歷史樣本數)
    # 交易次數越多，信心越高
    # 但這個需要外面傳入 t (交易次數)
    
    return max(0, kelly * fraction + inst_adj)

def kelly_to_shares(capital, price, kelly_pct, min_shares=100):
    """
    將 Kelly % 轉換成股數
    
    Args:
        capital: 總資金
        price: 買入價格
        kelly_pct: Kelly 建議比例 (0-1)
        min_shares: 最低購買股數 (預設 100)
    
    Returns:
        dict: {shares, amount, pct}
    """
    max_amount = capital * kelly_pct
    shares = int(max_amount / price)
    
    # 補足為 100 的倍數 (台股)
    if shares < min_shares:
        return {'shares': 0, 'amount': 0, 'pct': 0, 'reason': '金額過低'}
    
    shares = math.floor(shares / 100) * 100
    amount = shares * price
    actual_pct = amount / capital
    
    return {
        'shares': shares,
        'amount': amount,
        'pct': actual_pct,
        'price': price
    }

# === PositionSizer 類別 ===

class PositionSizer:
    """
    部位計算器 - 結合 Kelly Criterion + 風險管理
    """
    
    def __init__(self, capital=2_000_000, single_max=0.20, max_positions=5):
        """
        Args:
            capital: 總資金 (預設 200萬)
            single_max: 單檔最大曝險 (預設 20%)
            max_positions: 最大同時持有檔數 (預設 5)
        """
        self.capital = capital
        self.single_max = single_max
        self.max_positions = max_positions
    
    def calc_from_signal(self, code, price, signal_confidence=0.5,
                         inst_buy_pct=0, use_history=True, t_count=None):
        """
        從信號計算建議部位
        
        Args:
            code: 股票代碼
            price: 進場價格
            signal_confidence: 信號信心度 (0-1, 預設 0.5)
            inst_buy_pct: 法人買超比例 (0-1)
            use_history: 是否使用歷史資料計算 Kelly
            t_count: 歷史交易次數 (可選)
        
        Returns:
            dict: 部位建議
        """
        history = get_stock_history(code) if use_history else []
        loss_rule = get_loss_rule(code)
        
        # 停損設定
        stop_loss_pct = loss_rule.get('stop_loss_pct', DEFAULT_STOP_LOSS_PCT)
        
        if history and len(history) > 0:
            # 合併歷史資料
            total_t = sum(h.get('t', 0) for h in history)
            if total_t > 0:
                # 加權平均
                wr = sum(h.get('wr', 0) * h.get('t', 0) for h in history) / total_t / 100
                avg = sum(h.get('avg', 0) * h.get('t', 0) for h in history) / total_t
                avg_win = max(avg, 0.01)
                avg_loss = abs(min(avg, -0.01))
                
                kelly_pct = calc_hybrid_kelly(
                    wr, avg_win, avg_loss,
                    inst_buy_pct=inst_buy_pct,
                    fraction=0.5
                )
                source = 'kelly_hist'
            else:
                kelly_pct = signal_confidence * 0.1
                source = 'signal_only'
        else:
            # 無歷史資料，使用信號信心度
            kelly_pct = signal_confidence * 0.15
            source = 'signal_only'
        
        # 套用單檔上限
        kelly_pct = min(kelly_pct, self.single_max)
        
        # 轉換成股數
        size = kelly_to_shares(self.capital, price, kelly_pct)
        size['source'] = source
        size['stop_loss_pct'] = stop_loss_pct
        size['stop_loss_price'] = round(price * (1 - stop_loss_pct), 2)
        
        return size
    
    def calc_kelly_only(self, win_rate, avg_win_pct, avg_loss_pct, price):
        """
        純 Kelly 計算 (無歷史資料)
        
        Args:
            win_rate: 勝率 (0-1)
            avg_win_pct: 平均獲利 %
            avg_loss_pct: 平均虧損 %
            price: 進場價格
        
        Returns:
            dict: 部位建議
        """
        kelly_pct = calc_kelly_fractional(win_rate, avg_win_pct, avg_loss_pct, fraction=0.5)
        kelly_pct = min(kelly_pct, self.single_max)
        
        size = kelly_to_shares(self.capital, price, kelly_pct)
        size['kelly_pct'] = round(kelly_pct * 100, 1)
        size['stop_loss_pct'] = DEFAULT_STOP_LOSS_PCT
        size['stop_loss_price'] = round(price * (1 - DEFAULT_STOP_LOSS_PCT), 2)
        
        return size
    
    def summary(self, sizes):
        """
        產生部位摘要
        
        Args:
            sizes: list of calc result
        
        Returns:
            dict: 摘要資訊
        """
        total_pct = sum(s.get('pct', 0) for s in sizes)
        total_amount = sum(s.get('amount', 0) for s in sizes)
        count = len(sizes)
        
        return {
            'total_pct': round(total_pct * 100, 1),
            'total_amount': total_amount,
            'remaining_cash': self.capital - total_amount,
            'position_count': count,
            'slots_remaining': self.max_positions - count
        }

# === CLI 工具 ===

def main():
    """命令列工具"""
    import sys
    
    print("=" * 60)
    print("Tina Position Sizing - Kelly Criterion Calculator")
    print("=" * 60)
    
    sizer = PositionSizer(capital=2_000_000)
    
    print(f"\n💰 總資金: 2,000,000")
    print(f"📊 單檔上限: 20% (400,000)")
    print(f"🎯 最大持倉: 5 檔")
    print("-" * 60)
    
    if len(sys.argv) > 1:
        # 命令列模式
        code = sys.argv[1] if len(sys.argv) > 1 else '3017'
        price = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
        
        print(f"\n📈 計算 {code} @ {price}")
        
        result = sizer.calc_from_signal(code, price, use_history=True)
        
        print(f"\n建議買入:")
        print(f"  股數: {result['shares']}")
        print(f"  金額: {result['amount']:,}")
        print(f"  占比: {result['pct']*100:.1f}%")
        print(f"  停損: {result['stop_loss_price']} ({result['stop_loss_pct']*100:.0f}%)")
        print(f"  來源: {result['source']}")
    else:
        # 互動模式 - 測試幾個例子
        test_cases = [
            {'code': '3017', 'price': 150, 'wr': 0.786, 'avg_win': 0.054, 'avg_loss': 0.033},
            {'code': '3665', 'price': 85, 'wr': 0.667, 'avg_win': 0.039, 'avg_loss': 0.032},
            {'code': '2408', 'price': 180, 'wr': 0.783, 'avg_win': 0.084, 'avg_loss': 0.060},
        ]
        
        print("\n📊 Kelly Criterion 測試:")
        print("-" * 60)
        
        all_sizes = []
        for tc in test_cases:
            result = sizer.calc_kelly_only(tc['wr'], tc['avg_win'], tc['avg_loss'], tc['price'])
            result['code'] = tc['code']
            all_sizes.append(result)
            
            print(f"\n{tc['code']} @ {tc['price']}")
            print(f"  Win Rate: {tc['wr']*100:.1f}% | Avg Win: {tc['avg_win']*100:.1f}% | Avg Loss: {tc['avg_loss']*100:.1f}%")
            print(f"  → 建議買入: {result['shares']} 股, 金額: {result['amount']:,} ({result['pct']*100:.1f}%)")
        
        print("\n" + "=" * 60)
        summary = sizer.summary(all_sizes)
        print(f"\n📋 部位摘要:")
        print(f"  總曝險: {summary['total_pct']:.1f}% ({summary['total_amount']:,})")
        print(f"  剩餘現金: {summary['remaining_cash']:,}")
        print(f"  已使用槽位: {summary['position_count']}/5")
        print(f"  剩餘槽位: {summary['slots_remaining']}")

if __name__ == '__main__':
    main()