# -*- coding: utf-8 -*-
"""
Sector Rotation Module - Tina 台股產業輪動追蹤系統
===================================================

功能:
1. 11大產業輪動追蹤
2. 產業相對強弱分析
3. 輪動訊號偵測
4. 產業ETF對應追蹤

使用方法:
    from sector_rotation import SectorRotation
    
    sr = SectorRotation()
    result = sr.analyze()
    
    if result['rotation_signal']:
        print(f"輪動訊號: {result['leading_sector']}")
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional

# 台股 11 大類股 + 對應 ETF
SECTOR_ETF_MAP = {
    '半導體': {'code': '00891', 'name': '半導體'},
    '電子': {'code': '0053', 'name': '電子'},
    '金融': {'code': '0050', 'name': '金融'},
    '傳產': {'code': '00661', 'name': '傳產'},
    '塑膠': {'code': '00702', 'name': '塑膠'},
    '橡膠': {'code': '00702', 'name': '橡膠'},
    '鋼鐵': {'code': '00702', 'name': '鋼鐵'},
    '航運': {'code': '00702', 'name': '航運'},
    '紡織': {'code': '00702', 'name': '紡織'},
    '食品': {'code': '00702', 'name': '食品'},
    '營建': {'code': '00702', 'name': '營建'},
}

# 主要個股代替產業ETF (更精確)
SECTOR_STOCKS = {
    '半導體': ['2330', '2454', '3034'],
    '電子': ['2317', '2382', '2492'],
    '金融': ['2881', '2882', '2891'],
    '傳產': ['1301', '1326', '2002'],
    '塑膠': ['1303', '1326'],
    '橡膠': ['2105'],
    '鋼鐵': ['2002'],
    '航運': ['2603', '2610'],
    '紡織': ['1476', '1477'],
    '食品': ['1216', '1702'],
    '營建': ['2542', '5519'],
}


class SectorRotation:
    """
    產業輪動追蹤系統
    
    分析11大類股的相對強弱，
    找出領漲族群和弱勢族群
    """
    
    def __init__(
        self,
        period: int = 20,
        rebalance_days: int = 5
    ):
        """
        初始化 SectorRotation
        
        參數:
            period: 分析週期 (default 20日)
            rebalance_days: 換股週期 (default 5日)
        """
        self.period = period
        self.rebalance_days = rebalance_days
        
        # 產業資料
        self.sector_data = {}
        self.sector_returns = {}
        self.sector_strength = {}
        
        # 輪動狀態
        self.leading_sector = None
        self.weakening_sectors = []
        self.rotation_signal = False
        self.last_update = None
    
    def fetch_sector_data(self) -> bool:
        """
        抓取各產業代表個股資料
        
        返回:
            bool: 是否成功
        """
        print(' 抓取產業資料...')
        
        all_data = {}
        
        for sector, stocks in SECTOR_STOCKS.items():
            sector_df = []
            
            for stock in stocks[:2]:  # 每個產業取2檔
                try:
                    df = yf.download(f'{stock}.TW', period=f'{self.period + 30}d', auto_adjust=True, progress=False)
                    if df is not None and len(df) >= self.period:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = [c[0] for c in df.columns]
                        sector_df.append(df)
                except:
                    continue
            
            if sector_df:
                # 取平均
                combined = pd.concat(sector_df, axis=1)
                combined = combined[~combined.index.duplicated(keep='first')]
                all_data[sector] = combined
        
        if not all_data:
            return False
        
        self.sector_data = all_data
        return True
    
    def calculate_returns(self) -> Dict:
        """
        計算各產業報酬率
        
        返回:
            Dict: 各產業報酬率
        """
        returns = {}
        
        for sector, df in self.sector_data.items():
            if df is None or len(df) < self.period:
                continue
            
            # 確保 Close 是單一欄位
            close = df['Close']
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]  # 取第一欄
            elif isinstance(close, pd.Series) == False:
                continue
            
            # 計算不同週期報酬
            current = float(close.iloc[-1])
            ma5 = float(close.iloc[-1])
            ma20 = float(close.rolling(20).mean().iloc[-1])
            
            # 報酬率
            ret_1d = float(close.pct_change(1).iloc[-1]) if len(close) > 1 else 0
            ret_5d = float(close.pct_change(5).iloc[-1]) if len(close) > 5 else 0
            ret_20d = float((close.iloc[-1] / close.iloc[0] - 1)) if len(close) >= self.period else 0
            
            # 強度指標 (相對大盤)
            # 使用 0050 作為大盤代理
            try:
                tw50 = yf.download('0050.TW', period=f'{self.period + 5}d', auto_adjust=True, progress=False)
                if tw50 is not None and len(tw50) >= self.period:
                    if isinstance(tw50.columns, pd.MultiIndex):
                        tw50.columns = [c[0] for c in tw50.columns]
                    tw50_ret = (tw50['Close'].iloc[-1] / tw50['Close'].iloc[0] - 1)
                    relative_strength = ret_20d - tw50_ret
                else:
                    relative_strength = 0
            except:
                relative_strength = 0
            
            # vs_ma20 (需確保是單一值)
            ma20_val = float(ma20.iloc[-1]) if hasattr(ma20, 'iloc') else float(ma20) if ma20 else 0
            
            returns[sector] = {
                'ret_1d': float(ret_1d * 100),
                'ret_5d': float(ret_5d * 100),
                'ret_20d': float(ret_20d * 100),
                'relative_strength': float(relative_strength * 100),
                'vs_ma20': float(((current / ma20) - 1) * 100) if ma20 else 0
            }
        
        self.sector_returns = returns
        return returns
    
    def analyze_rotation(self) -> Dict:
        """
        分析輪動狀態
        
        返回:
            Dict with rotation analysis
        """
        if not self.sector_returns:
            self.calculate_returns()
        
        # 排序
        sorted_sectors = sorted(
            self.sector_returns.items(),
            key=lambda x: x[1]['relative_strength'],
            reverse=True
        )
        
        # 領漲族群
        self.leading_sector = sorted_sectors[0][0] if sorted_sectors else None
        
        # 弱勢族群
        self.weakening_sectors = [s[0] for s in sorted_sectors[-3:]]
        
        # 輪動訊號
        # 條件: 落後族群開始轉強 或 領漲族群更強
        rotation_detected = False
        rotation_type = None
        
        if sorted_sectors:
            top = sorted_sectors[0][1]
            bottom = sorted_sectors[-1][1]
            
            # 落後開始補漲
            if bottom['ret_5d'] > top['ret_5d'] * 0.8:
                rotation_detected = True
                rotation_type = 'catching_up'
            
            # 領先族群加速
            if top['ret_1d'] > 1.5:
                rotation_detected = True
                rotation_type = 'acceleration'
        
        self.rotation_signal = rotation_detected
        self.last_update = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        return {
            'rotation_signal': rotation_detected,
            'rotation_type': rotation_type,
            'leading_sector': self.leading_sector,
            'weakening_sectors': self.weakening_sectors,
            'sector_rankings': sorted_sectors,
            'all_returns': self.sector_returns,
            'last_update': self.last_update
        }
    
    def get_trade_signal(self, sector: str) -> Dict:
        """
        取得特定產業的交易訊號
        
        參數:
            sector: 產業名稱
        
        返回:
            Dict with signal
        """
        if sector not in self.sector_returns:
            return {'signal': 'no_data'}
        
        data = self.sector_returns[sector]
        
        # 訊號邏輯
        signal = 'neutral'
        confidence = 0
        
        # 強勢區 (相對強度 > 5%)
        if data['relative_strength'] > 5:
            signal = 'outperform'
            confidence = min(1.0, data['relative_strength'] / 10)
        
        # 弱勢區 (相對強度 < -5%)
        elif data['relative_strength'] < -5:
            signal = 'underperform'
            confidence = min(1.0, abs(data['relative_strength']) / 10)
        
        # 上升趨勢 (站上MA20)
        if data['vs_ma20'] > 0:
            if signal == 'outperform':
                signal = 'strong_buy'
                confidence = min(1.0, confidence + 0.2)
        
        # 下降趨勢 (跌破MA20)
        elif data['vs_ma20'] < -5:
            if signal == 'underperform':
                signal = 'strong_sell'
        
        return {
            'sector': sector,
            'signal': signal,
            'confidence': confidence,
            'returns': data
        }
    
    def get_sector_allocation(self, max_sectors: int = 3) -> Dict:
        """
        取得建議產業配置
        
        參數:
            max_sectors: 最多配置幾個產業
        
        返回:
            Dict with allocation recommendations
        """
        if not self.sector_returns:
            self.analyze_rotation()
        
        # 按相對強度排序
        sorted_sectors = sorted(
            self.sector_returns.items(),
            key=lambda x: x[1]['relative_strength'],
            reverse=True
        )
        
        # 只取正相對強度的
        positive = [(s, d) for s, d in sorted_sectors if d['relative_strength'] > 0]
        
        allocations = []
        for i, (sector, data) in enumerate(positive[:max_sectors]):
            weight = 0.3 - (i * 0.1)  # 30%, 20%, 10%
            allocations.append({
                'sector': sector,
                'weight': weight,
                'signal': self.get_trade_signal(sector)['signal'],
                'relative_strength': data['relative_strength']
            })
        
        return {
            'allocations': allocations,
            'total_weight': sum(a['weight'] for a in allocations),
            'leading': self.leading_sector,
            'rotation_active': self.rotation_signal
        }
    
    def get_report(self) -> str:
        """產生產業輪動報告"""
        if not self.sector_returns:
            self.analyze_rotation()
        
        report = []
        report.append('='*50)
        report.append(' 台股產業輪動分析報告')
        report.append('='*50)
        report.append(f' 時間: {self.last_update}')
        report.append('')
        
        # 輪動狀態
        if self.rotation_signal:
            report.append(f' 🔄 輪動訊號: {self.rotation_signal}')
            report.append(f'    領漲: {self.leading_sector}')
            report.append('')
        
        # 排名
        report.append(' 產業強弱排名:')
        report.append('-'*50)
        report.append('%-10s %-8s %-8s %-8s' % ('產業', '5日%', '20日%', '相對強度'))
        report.append('-'*50)
        
        sorted_sectors = sorted(
            self.sector_returns.items(),
            key=lambda x: x[1]['relative_strength'],
            reverse=True
        )
        
        for sector, data in sorted_sectors:
            arrow = '↑' if data['relative_strength'] > 0 else '↓'
            report.append('%-10s %-8.1f %-8.1f %-8.1f %s' % (
                sector,
                data['ret_5d'],
                data['ret_20d'],
                data['relative_strength'],
                arrow
            ))
        
        report.append('')
        
        # 配置建議
        alloc = self.get_sector_allocation()
        if alloc['allocations']:
            report.append(' 配置建議:')
            for a in alloc['allocations']:
                report.append(f'   {a["sector"]}: {a["weight"]*100:.0f}% ({a["signal"]})')
        
        report.append('='*50)
        
        return '\n'.join(report)


def quick_test():
    """快速測試 Sector Rotation"""
    print('='*50)
    print(' Sector Rotation 模組測試')
    print('='*50)
    print()
    
    sr = SectorRotation(period=20)
    
    if sr.fetch_sector_data():
        sr.calculate_returns()
        result = sr.analyze_rotation()
        
        print(sr.get_report())
    else:
        print('無法抓取產業資料')


if __name__ == '__main__':
    quick_test()