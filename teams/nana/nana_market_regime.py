# -*- coding: utf-8 -*-
"""
Market Regime Module - Tina 波段系統市場環境偵測
=================================================

功能:
1. TWII 大盤 RSI 偵測
2. Market regime 分類 (Bull/Bear/Neutral)
3. 動態調整進場 RSI 門檻

使用方式:
    from nana_market_regime import MarketRegime, get_regime
    
    mr = MarketRegime()
    regime = mr.get_regime()  # 'bull', 'bear', 'neutral'
    adjusted_rsi_threshold = mr.get_adjusted_rsi_threshold(regime)
    
    # 在 entry 條件中加入:
    # if can_trade and regime == 'overbought':
    #     additional_filter = rsi < adjusted_rsi_threshold
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

# TWII (台灣加權指數) ticker
TWII_TICKER = "^TWII"


class MarketRegime:
    """
    市場環境偵測模組
    
    根據 TWII RSI 判斷市場 regime 並提供動態調整建議:
    - Overbought (TWII RSI > 75): 謹慎進場，RSI 門檻從 65 降至 60
    - Neutral  (50 <= TWII RSI <= 75): 正常操作
    - Oversold (TWII RSI < 50): 積極進場，RSI 門檻維持 65
    """
    
    def __init__(self, lookback_days: int = 65):
        self.lookback_days = lookback_days
        self.twii_data = None
        self.regime = None
        self.twii_rsi = None
    
    def fetch_twii(self) -> Optional[Dict]:
        """"取得 TWII 歷史數據"""
        try:
            twii = yf.Ticker(TWII_TICKER)
            hist = twii.history(period=f"{self.lookback_days}d")
            if len(hist) < 60:
                return None
            # Drop NaN rows
            hist = hist.dropna(subset=['Close'])
            if len(hist) < 60:
                return None
            self.twii_data = hist
            return hist
        except Exception:
            return None
    
    @staticmethod
    def calc_rsi(closes: np.ndarray, period: int = 14) -> float:
        """計算 RSI"""
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def get_regime(self) -> Tuple[str, float]:
        """
        取得市場 regime 和 TWII RSI
        
        返回: (regime_name, twii_rsi)
            regime: 'overbought' | 'neutral' | 'oversold'
            rsi: TWII RSI 值
        """
        if self.twii_data is None:
            self.fetch_twii()
        
        if self.twii_data is None:
            return ('neutral', 50.0)  # fallback
        
        closes = np.array(self.twii_data['Close'])
        self.twii_rsi = self.calc_rsi(closes)
        
        if self.twii_rsi > 75:
            self.regime = 'overbought'
        elif self.twii_rsi < 50:
            self.regime = 'oversold'
        else:
            self.regime = 'neutral'
        
        return (self.regime, self.twii_rsi)
    
    def get_adjusted_rsi_threshold(self, base_threshold: float = 65) -> float:
        """
        根據 regime 取得調整後的 RSI 進場門檻
        
        參數:
            base_threshold: 基礎 RSI 門檻 (default 65)
        
        返回: 調整後的 RSI 門檻
            - Overbought: base - 5 (從 65 降至 60)
            - Neutral:   base (維持 65)
            - Oversold:  base (維持 65，可以更積極)
        """
        if self.regime is None:
            self.get_regime()
        
        if self.regime == 'overbought':
            return max(55, base_threshold - 5)  # 最低不低於 55
        return base_threshold  # neutral/oversold 維持原值
    
    def get_regime_report(self) -> Dict:
        """產出市場環境報告"""
        regime, rsi = self.get_regime()
        threshold = self.get_adjusted_rsi_threshold()
        
        return {
            'regime': regime,
            'twii_rsi': round(rsi, 1),
            'adjusted_rsi_threshold': threshold,
            'base_threshold': 65,
            'adjustment': threshold - 65,
            'recommendation': self._get_recommendation(regime),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    @staticmethod
    def _get_recommendation(regime: str) -> str:
        if regime == 'overbought':
            return "⚠️ 大盤過熱 (TWII RSI > 75)，建議提高進場標準，僅 RSI < 60 時進場"
        elif regime == 'oversold':
            return "✅ 大盤超賣 (TWII RSI < 50)，可以積極進場，標準不變"
        else:
            return "➡️ 大盤中性 (50 <= TWII RSI <= 75)，正常操作標準"


def quick_test():
    """快速測試"""
    print('='*60)
    print(' Market Regime 模組測試')
    print('='*60)
    print()
    
    mr = MarketRegime()
    report = mr.get_regime_report()
    
    print(f"市場環境: {report['regime']}")
    print(f"TWII RSI: {report['twii_rsi']}")
    print(f"進場 RSI 門檻: {report['adjusted_rsi_threshold']} (基礎 65, 調整 {report['adjustment']:+d})")
    print(f"建議: {report['recommendation']}")
    print(f"時間: {report['timestamp']}")


if __name__ == '__main__':
    quick_test()
