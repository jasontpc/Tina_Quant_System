# -*- coding: utf-8 -*-
"""Maggy Team Definition - 美股波段交易團隊"""
import sys, json
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

TEAM_DIR = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System\teams\maggy'

# Team config
config = {
    'team': 'Maggy',
    'role': '美股波段交易專家',
    'created': '2026-04-28',
    'version': '2.0',
    'focus': 'US Stock Band Trading (NYSE/NASDAQ)',
    
    'database': {
        'path': 'data/maggy.db',
        'stocks': 15,
        'records': 6600,
        'coverage': '2 years daily OHLCV + technical indicators',
        'updated': '2026-04-27'
    },
    
    'strategies': {
        'RSI_Rev': {
            'name': 'RSI 均值回歸（標準）',
            'entry_rsi': 30,
            'exit_rsi': 55,
            'max_hold_days': 20,
            'backtest_avg_return': 76.2,
            'backtest_avg_wr': 100.0,
            'best_stock': 'TQQQ (+134.6%)'
        },
        'RSI_Oversold_Aggressive': {
            'name': 'RSI 均值回歸（積極）',
            'entry_rsi': 35,
            'exit_rsi': 60,
            'max_hold_days': 15,
            'backtest_avg_return': 79.4,
            'backtest_avg_wr': 99.4,
            'best_stock': 'TSLA (+141.2%)'
        },
        'MA_Golden_Cross': {
            'name': 'MA 黃金交叉',
            'ma_short': 20,
            'ma_long': 60,
            'backtest_avg_return': -98.5,
            'note': '不適用美股，已淘汰'
        },
        'BB_Break_Long': {
            'name': 'BB 突破策略',
            'atr_stop_mult': 2,
            'atr_target_mult': 4,
            'backtest_avg_return': -66.4,
            'note': '不適用美股，已淘汰'
        }
    },
    
    'watchlist': {
        'ETFs': ['SPY', 'QQQ', 'SSO', 'QLD', 'TQQQ', 'SPXL', 'FANG', 'ARKK'],
        'Tech': ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD'],
        'Others': ['NFLX', 'COIN']
    },
    
    'current_signals': {
        'timestamp': '2026-04-28 15:42',
        'oversold_rsi_lt_35': [],
        'bull_ma20': ['FANG', 'COIN', 'AAPL'],
        'overbought_rsi_gt_75': ['NVDA', 'QQQ', 'TQQQ', 'SPY', 'SSO', 'SPXL', 'AMD', 'AMZN', 'META', 'GOOGL', 'MSFT']
    },
    
    'recommended_strategy': 'RSI_Oversold_Aggressive',
    'recommended_stocks': ['TSLA', 'TQQQ', 'SPXL', 'NVDA', 'FANG'],
    
    'scripts': {
        'screener': 'maggy_screener.py',
        'backtest': 'maggy_full_backtest.py',
        'sim_trades': 'maggy_sim_trades.py',
        'daily_report': 'maggy_daily_report.py',
        'autonomous': 'maggy_autonomous.py',
        'build_db': 'build_maggy_db.py'
    },
    
    'next_actions': [
        'Expand watchlist to 30+ stocks',
        'Add MACD strategy backtest',
        'Implement leverage ETF special handling',
        'Build options income strategy (covered calls)',
        'Add earnings date calendar',
        'Create weekly automated report cron'
    ]
}

# Save
output_path = f'{TEAM_DIR}\\team_definition.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print('=== Maggy 團隊定義已更新 ===')
print(f'策略數: {len(config["strategies"])}')
print(f'追蹤標的: {len(config["watchlist"]["ETFs"]) + len(config["watchlist"]["Tech"]) + len(config["watchlist"]["Others"])}檔')
print(f'最佳策略: {config["recommended_strategy"]}')
print(f'推薦標的: {", ".join(config["recommended_stocks"])}')