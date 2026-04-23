# -*- coding: utf-8 -*-
"""
Failure Analysis Module - Tina 失敗交易分析系統
================================================

功能:
1. 定義失敗交易標準（虧損 > 2% 或 RSI 背離）
2. 記錄失敗交易的特徵（進場價格、日期、原因）
3. 建立失敗案例資料庫 (CSV 格式)
4. 提供分析報告功能

失敗分類:
- ENTRY_TIMING: 進場時機錯誤（RSI > 75 進場）
- INST_REVERSAL: 法人逆轉（連續買超後突然賣出）
- MARKET_REGIME: 市場條件改變（多頭轉空頭）
- STOP_LOSS: 停損觸發（跌破 ATR 2x）

使用方法:
    from core.failure_analysis import FailureAnalyzer
    
    fa = FailureAnalyzer()
    fa.log_failure(trade_data)
    report = fa.generate_report()
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

# ==================== 路徑設定 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data')
FAILURE_CSV = os.path.join(DATA_DIR, 'failure_log.csv')

# ==================== 失敗原因分類 ====================
class FailureType:
    ENTRY_TIMING   = 'ENTRY_TIMING'    # 進場時機錯誤
    INST_REVERSAL  = 'INST_REVERSAL'   # 法人逆轉
    MARKET_REGIME  = 'MARKET_REGIME'   # 市場多空轉變
    STOP_LOSS      = 'STOP_LOSS'       # ATR 停損
    RSI_DIVERGENCE = 'RSI_DIVERGENCE'  # RSI 背離
    VOLUME_SPIKE   = 'VOLUME_SPIKE'    # 量能異常
    MA_BREAK       = 'MA_BREAK'        # 均線跌破

@dataclass
class FailureRecord:
    """單筆失敗交易記錄"""
    id: str                    # UUID
    code: str                  # 股票代碼
    name: str                  # 股票名稱
    entry_date: str            # 進場日期
    exit_date: str             # 出場日期
    entry_price: float         # 進場價格
    exit_price: float          # 出場價格
    return_pct: float          # 報酬率 %
    rsi_entry: float           # 進場時 RSI
    atr_entry: float           # 進場時 ATR (點數)
    atr_pct: float             # ATR 百分比
    bias: float                # MA20 偏離 %
    volume_ratio: float        # 進場時量比
    f_days_before: int         # 進場前外资買超天數
    t_days_before: int         # 進場前投信買超天數
    failure_type: str          # 失敗類型
    failure_reason: str        # 失敗原因描述
    market_status: str         # 當時市場狀態
    notes: str = ''            # 備註
    system_version: str = 'Nana_v5.0'  # 分析系統版本

class FailureAnalyzer:
    """
    失敗交易分析器
    
    使用方式:
        fa = FailureAnalyzer()
        fa.log_failure(trade_data)
        report = fa.generate_report()
    """
    
    # 失敗閾值
    LOSS_THRESHOLD_PCT = -2.0        # 虧損 > 2% 視為失敗
    RSI_OVERBOUGHT = 75               # RSI > 75 過熱進場
    RSI_WARNING    = 65               # RSI > 65 警告
    ATR_STOP_MULT  = 2.0             # ATR 2x 停損
    VR_LOW         = 1.0             # 量比 < 1 為低量
    MAX_BIAS       = 8.0             # MA20 偏離 > 8% 為過大
    
    def __init__(self, csv_path: str = FAILURE_CSV):
        self.csv_path = csv_path
        self._ensure_csv()
    
    def _ensure_csv(self):
        """確保 CSV 存在並有標題"""
        if not os.path.exists(self.csv_path):
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
            # UTF-8-BOM for Excel compatibility
            with open(self.csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id','code','name','entry_date','exit_date',
                    'entry_price','exit_price','return_pct',
                    'rsi_entry','atr_entry','atr_pct','bias',
                    'volume_ratio','f_days_before','t_days_before',
                    'failure_type','failure_reason','market_status',
                    'notes','system_version'
                ])
    
    def classify_failure(
        self,
        entry_rsi: float,
        atr_pct: float,
        bias: float,
        vr: float,
        f_days: int,
        t_days: int,
        return_pct: float,
        market_status: str,
        inst_flow_reversal: bool = False,
        ma_broken: bool = False,
        rsi_divergence: bool = False
    ) -> Tuple[str, str]:
        """
        根據交易特徵分類失敗原因
        
        回傳: (failure_type, failure_reason)
        """
        reasons = []
        
        # 1. RSI 進場時機錯誤
        if entry_rsi > self.RSI_OVERBOUGHT:
            reasons.append(f'RSI過熱進場({entry_rsi:.1f})')
        elif entry_rsi > self.RSI_WARNING:
            reasons.append(f'RSI偏高進場({entry_rsi:.1f})')
        
        # 2. 法人逆轉
        if inst_flow_reversal:
            reasons.append('法人逆轉(買超後突然賣出)')
        
        # 3. 市場條件改變
        if market_status == 'OVERBOUGHT':
            reasons.append('市場過熱/多頭尾端')
        
        # 4. ATR 停損觸發
        if return_pct < -3 and atr_pct > 0:
            reasons.append(f'跌破ATR停損({return_pct:.1f}%)')
        
        # 5. MA 偏離過大
        if bias > self.MAX_BIAS:
            reasons.append(f'MA20偏離過大({bias:.1f}%)')
        
        # 6. 量能不足
        if vr < self.VR_LOW:
            reasons.append(f'量能不足(VR={vr:.2f})')
        
        # 7. MA20 跌破
        if ma_broken:
            reasons.append('MA20均線跌破')
        
        # 8. RSI 背離
        if rsi_divergence:
            reasons.append('RSI價格背離')
        
        # 主要失敗原因（取最重要的一個）
        if inst_flow_reversal:
            return FailureType.INST_REVERSAL, '; '.join(reasons) if reasons else '法人逆轉'
        elif entry_rsi > self.RSI_OVERBOUGHT:
            return FailureType.ENTRY_TIMING, '; '.join(reasons) if reasons else 'RSI過熱進場'
        elif ma_broken:
            return FailureType.MA_BREAK, '; '.join(reasons) if reasons else '均線跌破'
        elif market_status == 'OVERBOUGHT' and return_pct < -2:
            return FailureType.MARKET_REGIME, '; '.join(reasons) if reasons else '市場多空轉變'
        elif return_pct < self.LOSS_THRESHOLD_PCT:
            return FailureType.STOP_LOSS, '; '.join(reasons) if reasons else f'虧損超標({return_pct:.1f}%)'
        elif rsi_divergence:
            return FailureType.RSI_DIVERGENCE, '; '.join(reasons) if reasons else 'RSI背離'
        else:
            return FailureType.ENTRY_TIMING, '; '.join(reasons) if reasons else '進場時機不佳'
    
    def log_failure(self, record: FailureRecord) -> str:
        """寫入一筆失敗記錄到 CSV"""
        self._ensure_csv()
        row = [
            record.id, record.code, record.name,
            record.entry_date, record.exit_date,
            record.entry_price, record.exit_price, record.return_pct,
            record.rsi_entry, record.atr_entry, record.atr_pct, record.bias,
            record.volume_ratio, record.f_days_before, record.t_days_before,
            record.failure_type, record.failure_reason, record.market_status,
            record.notes, record.system_version
        ]
        with open(self.csv_path, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(row)
        return record.id
    
    def log_failure_from_dict(self, data: dict) -> str:
        """從 dict 格式自動創建失敗記錄"""
        import uuid
        entry_rsi = data.get('rsi_entry', 50)
        atr_pct = data.get('atr_pct', 0)
        bias = data.get('bias', 0)
        vr = data.get('volume_ratio', 1.0)
        f_days = data.get('f_days_before', 0)
        t_days = data.get('t_days_before', 0)
        return_pct = data.get('return_pct', 0)
        market_status = data.get('market_status', 'NEUTRAL')
        inst_flow_reversal = data.get('inst_flow_reversal', False)
        ma_broken = data.get('ma_broken', False)
        rsi_divergence = data.get('rsi_divergence', False)
        
        failure_type, failure_reason = self.classify_failure(
            entry_rsi, atr_pct, bias, vr, f_days, t_days,
            return_pct, market_status, inst_flow_reversal, ma_broken, rsi_divergence
        )
        
        record = FailureRecord(
            id=str(uuid.uuid4())[:8],
            code=data.get('code',''),
            name=data.get('name',''),
            entry_date=data.get('entry_date',''),
            exit_date=data.get('exit_date',''),
            entry_price=data.get('entry_price',0),
            exit_price=data.get('exit_price',0),
            return_pct=return_pct,
            rsi_entry=entry_rsi,
            atr_entry=data.get('atr_entry',0),
            atr_pct=atr_pct,
            bias=bias,
            volume_ratio=vr,
            f_days_before=f_days,
            t_days_before=t_days,
            failure_type=failure_type,
            failure_reason=failure_reason,
            market_status=market_status,
            notes=data.get('notes',''),
            system_version=data.get('system_version','Nana_v5.0')
        )
        return self.log_failure(record)
    
    def load_records(self) -> pd.DataFrame:
        """讀取所有失敗記錄"""
        if not os.path.exists(self.csv_path):
            return pd.DataFrame()
        try:
            df = pd.read_csv(self.csv_path, encoding='utf-8')
            if 'return_pct' in df.columns:
                df['return_pct'] = pd.to_numeric(df['return_pct'], errors='coerce')
            return df
        except:
            return pd.DataFrame()
    
    def generate_report(self, min_records: int = 3) -> Dict:
        """
        產生失敗分析報告
        
        參數:
            min_records: 最少需要多少筆才產生統計（避免樣本過少）
        """
        df = self.load_records()
        
        if len(df) == 0:
            return {
                'status': 'no_data',
                'message': '尚無失敗記錄',
                'total_failures': 0
            }
        
        if len(df) < min_records:
            return {
                'status': 'insufficient',
                'message': f'失敗記錄僅 {len(df)} 筆，需至少 {min_records} 筆才有統計意義',
                'total_failures': len(df)
            }
        
        # 依失敗類型分組統計
        type_stats = {}
        for ftype in df['failure_type'].unique():
            sub = df[df['failure_type'] == ftype]
            type_stats[ftype] = {
                'count': len(sub),
                'avg_loss': round(sub['return_pct'].mean(), 2),
                'max_loss': round(sub['return_pct'].min(), 2),
                'total_loss': round(sub['return_pct'].sum(), 2),
                'pct': round(len(sub) / len(df) * 100, 1)
            }
        
        # 進場 RSI 分布
        rsi_bins = [0, 55, 65, 75, 100]
        rsi_labels = ['<55正常', '55-65警告', '65-75危險', '>75過熱']
        df['rsi_bin'] = pd.cut(df['rsi_entry'], bins=rsi_bins, labels=rsi_labels)
        rsi_dist = df['rsi_bin'].value_counts().to_dict()
        
        # 均線偏離分布
        bias_bins = [-100, -2, 4, 8, 100]
        bias_labels = ['<-2%偏離下', '-2~4%適中', '4~8%警告', '>8%過大']
        df['bias_bin'] = pd.cut(df['bias'], bins=bias_bins, labels=bias_labels)
        bias_dist = df['bias_bin'].value_counts().to_dict()
        
        # 市場狀態分布
        market_dist = df['market_status'].value_counts().to_dict()
        
        # 依日期統計（觀察是否有系統性問題）
        df['entry_month'] = pd.to_datetime(df['entry_date']).dt.to_period('M')
        monthly = df.groupby('entry_month').agg(
            count=('id','count'),
            avg_loss=('return_pct','mean')
        ).to_dict('index')
        
        # 總體統計
        total = len(df)
        avg_loss = round(df['return_pct'].mean(), 2)
        worst = df.loc[df['return_pct'].idxmin()]
        
        return {
            'status': 'ok',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'total_failures': total,
            'avg_loss_pct': avg_loss,
            'worst_case': {
                'code': worst['code'],
                'name': worst['name'],
                'return_pct': round(worst['return_pct'], 2),
                'reason': worst['failure_reason']
            },
            'by_failure_type': dict(sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True)),
            'rsi_distribution': rsi_dist,
            'bias_distribution': bias_dist,
            'market_status_distribution': market_dist,
            'monthly_trend': {str(k): v for k, v in monthly.items()},
            'top_failure_type': max(type_stats, key=lambda x: type_stats[x]['count']),
            'recommendations': self._generate_recommendations(type_stats, rsi_dist, bias_dist)
        }
    
    def _generate_recommendations(self, type_stats: Dict, rsi_dist: Dict, bias_dist: Dict) -> List[str]:
        """根據統計結果產生優化建議"""
        recs = []
        
        if 'ENTRY_TIMING' in type_stats and type_stats['ENTRY_TIMING']['count'] >= 3:
            recs.append(f"【進場時機】ENTRY_TIMING 失敗 {type_stats['ENTRY_TIMING']['count']} 次，建議提高 RSI 進場門檻至 <65")
        
        if 'INST_REVERSAL' in type_stats and type_stats['INST_REVERSAL']['count'] >= 2:
            recs.append(f"【法人逆轉】{type_stats['INST_REVERSAL']['count']} 次失敗，建議加入法人賣超後 3 日冷卻期")
        
        if 'MARKET_REGIME' in type_stats and type_stats['MARKET_REGIME']['count'] >= 2:
            recs.append(f"【市場轉向】{type_stats['MARKET_REGIME']['count']} 次失敗於市場過熱時，建議 OVERBOUGHT 時降低倉位")
        
        if 'STOP_LOSS' in type_stats and type_stats['STOP_LOSS']['count'] >= 3:
            recs.append(f"【停損觸發】{type_stats['STOP_LOSS']['count']} 次，建議縮緊 ATR 倍數或加入分批停損")
        
        if '>75過熱' in rsi_dist and rsi_dist['>75過熱'] >= 3:
            recs.append("【RSI過熱】>75 進場的失敗率過高，建議完全禁止 RSI>75 進場")
        
        if '>8%過大' in bias_dist and bias_dist['>8%過大'] >= 3:
            recs.append("【MA偏離】Bias>8% 失敗偏多，建議限制最大 Bias<6%")
        
        if len(recs) == 0:
            recs.append("目前失敗樣本數不足，需累積更多資料後才能產生具體建議")
        
        return recs
    
    def print_report(self, report: Dict = None):
        """格式化輸出報告"""
        if report is None:
            report = self.generate_report()
        
        print('=' * 70)
        print('  Tina 失敗交易分析報告')
        print('=' * 70)
        
        if report['status'] != 'ok':
            print(f"  狀態: {report['status']}")
            print(f"  {report['message']}")
            print('=' * 70)
            return
        
        print(f"  產生時間: {report['generated_at']}")
        print(f"  總失敗筆數: {report['total_failures']}")
        print(f"  平均虧損: {report['avg_loss_pct']:.2f}%")
        print()
        
        print('  【最慘案例】')
        wc = report['worst_case']
        print(f"    {wc['code']} {wc['name']}: {wc['return_pct']:.1f}% | {wc['reason']}")
        print()
        
        print('  【失敗類型分布】')
        print(f"    {'類型':<20} {'次數':>6} {'佔比':>6} {'平均虧損':>8}")
        print(f"    {'-'*44}")
        for ftype, stat in report['by_failure_type'].items():
            print(f"    {ftype:<20} {stat['count']:>6} {stat['pct']:>5.1f}% {stat['avg_loss']:>+8.2f}%")
        print()
        
        print('  【RSI 進場分布】')
        for k, v in report['rsi_distribution'].items():
            print(f"    {k}: {v} 次")
        print()
        
        print('  【MA20 偏離分布】')
        for k, v in report['bias_distribution'].items():
            print(f"    {k}: {v} 次")
        print()
        
        print('  【市場狀態分布】')
        for k, v in report['market_status_distribution'].items():
            print(f"    {k}: {v} 次")
        print()
        
        print('  【優化建議】')
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"    {i}. {rec}")
        
        print()
        print('=' * 70)
    
    def get_recent_failures(self, days: int = 30) -> pd.DataFrame:
        """取得最近 N 天內的失敗記錄"""
        df = self.load_records()
        if len(df) == 0:
            return df
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        return df[df['entry_date'] >= cutoff]


# ==================== 快速測試 ====================
if __name__ == '__main__':
    fa = FailureAnalyzer()
    
    # 建立範例資料（如果是新建立的 CSV，自動寫入3筆範例）
    df = fa.load_records()
    if len(df) == 0:
        print('[ 初始化 ] 建立範例失敗記錄...')
        sample_data = [
            {
                'code': '3231', 'name': '緯創', 'entry_date': '2026-04-10', 'exit_date': '2026-04-17',
                'entry_price': 142.0, 'exit_price': 136.5, 'return_pct': -3.87,
                'rsi_entry': 77.3, 'atr_entry': 4.1, 'atr_pct': 2.9, 'bias': 8.2,
                'volume_ratio': 0.9, 'f_days_before': 4, 't_days_before': 0,
                'market_status': 'OVERBOUGHT', 'inst_flow_reversal': True,
                'notes': '法人連續買超後突然賣出，RSI>75進場過熱'
            },
            {
                'code': '3017', 'name': '奇鋐', 'entry_date': '2026-04-08', 'exit_date': '2026-04-15',
                'entry_price': 2650.0, 'exit_price': 2570.0, 'return_pct': -3.02,
                'rsi_entry': 68.5, 'atr_entry': 120.0, 'atr_pct': 4.5, 'bias': 12.1,
                'volume_ratio': 0.8, 'f_days_before': 0, 't_days_before': 6,
                'market_status': 'OVERBOUGHT', 'ma_broken': True,
                'notes': 'MA20偏離過大12%，市場過熱時跌破均線'
            },
            {
                'code': '2379', 'name': '瑞昱', 'entry_date': '2026-04-05', 'exit_date': '2026-04-11',
                'entry_price': 520.0, 'exit_price': 500.0, 'return_pct': -3.85,
                'rsi_entry': 72.1, 'atr_entry': 15.0, 'atr_pct': 2.9, 'bias': 5.3,
                'volume_ratio': 0.7, 'f_days_before': 3, 't_days_before': 0,
                'market_status': 'NEUTRAL', 'inst_flow_reversal': False, 'ma_broken': False,
                'notes': '量能不足，進場後缺乏支撐'
            }
        ]
        for d in sample_data:
            fa.log_failure_from_dict(d)
        print(f'[ 完成 ] 寫入 {len(sample_data)} 筆範例失敗記錄')
    
    # 產生報告
    report = fa.generate_report()
    fa.print_report(report)
    
    # 最近30天失敗
    recent = fa.get_recent_failures(30)
    if len(recent) > 0:
        print(f'\n[ 最近30天 ] 失敗記錄: {len(recent)} 筆')