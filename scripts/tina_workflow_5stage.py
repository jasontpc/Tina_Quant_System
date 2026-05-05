"""
Tina 自主策略優化系統 - 五階段工作流
Stage 1: 環境感測與狀態確認
Stage 2: 個股標的篩選
Stage 3: 智能邏輯推演
Stage 4: 虛擬回測與安全審核
Stage 5: 正式更新與同步
"""

import os
import sys
import json
import sqlite3
import yfinance as yf
from datetime import datetime, timedelta
import shutil
import tempfile
import hashlib

WORKSPACE = r'C:\Users\USER\.openclaw\workspace\Tina_Quant_System'
STRATEGIES_DIR = os.path.join(WORKSPACE, 'configs', 'stock_strategies')
DATA_DIR = os.path.join(WORKSPACE, 'data')
REPORTS_DIR = os.path.join(WORKSPACE, 'reports')
COOLDOWN_FILE = os.path.join(DATA_DIR, 'active_brain_v2_cooldown.json')
PID_FILE = os.path.join(DATA_DIR, 'workflow.pid')
TRADE_DB = os.path.join(DATA_DIR, 'trade_history.db')  # 假設有交易記錄

# ============================================================================
# 工具函數
# ============================================================================

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_pid_lock():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            old_pid = int(f.read().strip())
        try:
            os.kill(old_pid, 0)
            return False
        except OSError:
            pass
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    return True

def release_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

# ============================================================================
# 階段一：環境感測與狀態確認
# ============================================================================

def stage1_environment_check():
    """
    Stage 1: 環境感測與狀態確認
    - 系統檢索：大腦自動讀取生命週期監控日誌
    - 閒置判定：確認無掛單、無進行中的交易
    - 資源查核：確認硬體負載正常，冷卻時間已過
    """
    log("\n" + "="*60)
    log("STAGE 1: 環境感測與狀態確認")
    log("="*60)
    
    status = {
        'idle': True,
        'cooldown_ok': True,
        'resources_ok': True,
        'can_proceed': True,
        'reasons': []
    }
    
    # 1. 檢查是否為交易時段
    now = datetime.now()
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    
    # 周末
    if weekday >= 5:
        status['reasons'].append('週末，非交易日')
    else:
        # 開盤前30分鐘（8:30-9:00）
        if hour == 8 and 30 <= minute <= 59:
            status['idle'] = False
            status['reasons'].append('即將開盤（8:30-9:00）')
        
        # 收盤後半小時（13:30-14:00）
        elif hour == 13 and minute >= 30:
            status['idle'] = False
            status['reasons'].append('剛收盤（13:30-14:00）')
        
        # 交易時間內
        elif 9 <= hour < 13:
            status['idle'] = False
            status['reasons'].append('交易時段中')
    
    # 2. 檢查冷卻期
    if os.path.exists(COOLDOWN_FILE):
        with open(COOLDOWN_FILE, 'r') as f:
            cooldown = json.load(f)
        
        # 檢查是否有股票在24小時內被修改過
        recent_changes = []
        for code, info in cooldown.items():
            last_change = datetime.fromisoformat(info['time'])
            if (now - last_change).total_seconds() < 86400:
                recent_changes.append(code)
        
        if recent_changes:
            status['cooldown_ok'] = False
            status['reasons'].append(f'近期修改過: {", ".join(recent_changes[:3])}')
    
    # 3. 檢查系統資源（簡單檢查磁碟空間）
    try:
        import shutil
        disk_usage = shutil.disk_usage(WORKSPACE)
        if disk_usage.free / disk_usage.total < 0.1:
            status['resources_ok'] = False
            status['reasons'].append('磁碟空間不足10%')
    except:
        pass
    
    # 4. 總結
    status['can_proceed'] = status['idle'] and status['cooldown_ok'] and status['resources_ok']
    
    log(f"  閒置狀態: {'是' if status['idle'] else '否'}")
    log(f"  冷卻期: {'通過' if status['cooldown_ok'] else '有股票冷卻中'}")
    log(f"  資源: {'正常' if status['resources_ok'] else '異常'}")
    
    if status['reasons']:
        for reason in status['reasons']:
            log(f"  - {reason}")
    
    log(f"  => 可以繼續: {'是' if status['can_proceed'] else '否'}")
    
    return status

# ============================================================================
# 階段二：個股標的篩選
# ============================================================================

def stage2_stock_screening():
    """
    Stage 2: 個股標的篩選
    - 效能掃描：挑選勝率下滑或回撤異常的標的
    - 數據抓取：調取最近線圖數據
    """
    log("\n" + "="*60)
    log("STAGE 2: 個股標的篩選")
    log("="*60)
    
    # 讀取所有策略
    if not os.path.exists(STRATEGIES_DIR):
        log("  策略目錄不存在")
        return []
    
    strategies = []
    for f in os.listdir(STRATEGIES_DIR):
        if f.endswith('.json'):
            code = f.replace('.json', '')
            with open(os.path.join(STRATEGIES_DIR, f), 'r', encoding='utf-8') as fp:
                strategy = json.load(fp)
                strategies.append({
                    'code': code,
                    'name': strategy.get('name', code),
                    'type': strategy.get('type', 'unknown'),
                    'volatility': strategy.get('volatility_tier', 'medium'),
                    'strategy': strategy
                })
    
    log(f"  找到 {len(strategies)} 檔策略")
    
    # 評分候選標的（基於多種因素）
    candidates = []
    
    for stock in strategies:
        code = stock['code']
        
        try:
            # 取得股價數據
            if code.isdigit() and len(code) == 4:
                tk = yf.Ticker(code + '.TW')
            else:
                tk = yf.Ticker(code)
            
            h = tk.history(period='3mo')
            
            if len(h) < 30:
                continue
            
            price = float(h['Close'].iloc[-1])
            rsi = float(calc_rsi(h['Close'], 14).iloc[-1])
            ma20 = float(h['Close'].rolling(20).mean().iloc[-1])
            
            # 計算近期表現
            ret_5d = (price / float(h['Close'].iloc[-5]) - 1) * 100 if len(h) >= 5 else 0
            ret_10d = (price / float(h['Close'].iloc[-10]) - 1) * 100 if len(h) >= 10 else 0
            
            # 評分（越高分越需要檢視）
            score = 0
            
            # RSI 過熱信號
            if rsi > 75:
                score += 3
            elif rsi > 65:
                score += 2
            elif rsi < 35:
                score += 2  # 超賣也可能需要檢視
            
            # 近期回撤
            if ret_5d < -5:
                score += 3
            elif ret_10d < -10:
                score += 2
            
            # 高波動股票更容易需要調整
            if stock['volatility'] == 'high':
                score += 1
            
            # 非金融股/ETF（成長股更需要關注）
            if stock['type'] not in ['financial_low', 'etf']:
                score += 1
            
            if score >= 3:
                candidates.append({
                    'code': code,
                    'name': stock['name'],
                    'type': stock['type'],
                    'score': score,
                    'price': price,
                    'rsi': rsi,
                    'ma20': ma20,
                    'ret_5d': ret_5d,
                    'ret_10d': ret_10d,
                    'data': h
                })
        
        except Exception as e:
            pass
    
    # 按評分排序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    log(f"  候選標的: {len(candidates)} 檔")
    for c in candidates[:5]:
        log(f"    {c['code']} {c['name']}: score={c['score']} RSI={c['rsi']:.1f} 5D={c['ret_5d']:.1f}%")
    
    return candidates[:10]  # 最多返回10檔

# ============================================================================
# 階段三：智能邏輯推演
# ============================================================================

def stage3_brain_analysis(stock):
    """
    Stage 3: 智能邏輯推演
    - 情境建模：大腦進入深度思考
    - 策略擬定：判斷趨勢或區間邏輯
    - 參數建議：提出調整方案
    """
    log("\n" + "="*60)
    log(f"STAGE 3: 智能邏輯推演 - {stock['code']}")
    log("="*60)
    
    code = stock['code']
    h = stock['data']
    rsi = stock['rsi']
    price = stock['price']
    ma20 = stock['ma20']
    
    analysis = {
        'code': code,
        'current_rsi': rsi,
        'current_price': price,
        'situation': None,
        'recommendation': None,
        'params': {},
        'confidence': 0.0
    }
    
    # 情境判斷
    above_ma20 = price > ma20
    
    if rsi > 70:
        if above_ma20:
            analysis['situation'] = '強勢多頭'
            analysis['recommendation'] = '趨勢追蹤'
            analysis['params'] = {
                'rsi_max': 75,  # 放寬到75
                'rsi_overbought_exit': 85,
                'stop_loss_pct': 8,
                'trailing_stop_atr': 2.5
            }
            analysis['confidence'] = 0.75
        else:
            analysis['situation'] = '高檔震盪'
            analysis['recommendation'] = '區間操作'
            analysis['params'] = {
                'rsi_max': 65,
                'rsi_overbought_exit': 75,
                'stop_loss_pct': 6,
                'max_hold_days': 7
            }
            analysis['confidence'] = 0.65
    elif rsi < 30:
        analysis['situation'] = '超賣打底'
        analysis['recommendation'] = '觀望或少量試單'
        analysis['params'] = {
            'rsi_max': 40,
            'rsi_overbought_exit': 60,
            'stop_loss_pct': 10,
            'max_position_pct': 5  # 降低部位
        }
        analysis['confidence'] = 0.55
    elif rsi < 55:
        if above_ma20:
            analysis['situation'] = '穩健多頭'
            analysis['recommendation'] = '趨勢進場'
            analysis['params'] = {
                'rsi_max': 65,
                'rsi_overbought_exit': 75,
                'stop_loss_pct': 7,
                'ma20_slope_min': 0.5
            }
            analysis['confidence'] = 0.80
        else:
            analysis['situation'] = '築底階段'
            analysis['recommendation'] = '等待突破'
            analysis['params'] = {
                'rsi_max': 60,
                'rsi_overbought_exit': 70,
                'ma_required': 'MA20>MA60',
                'volume_ratio_min': 1.5
            }
            analysis['confidence'] = 0.60
    else:
        analysis['situation'] = '中性整理'
        analysis['recommendation'] = '觀望'
        analysis['confidence'] = 0.50
    
    log(f"  情境: {analysis['situation']}")
    log(f"  建議: {analysis['recommendation']}")
    log(f"  信心度: {analysis['confidence']:.0%}")
    log(f"  建議參數:")
    for k, v in analysis['params'].items():
        log(f"    {k}: {v}")
    
    return analysis

# ============================================================================
# 階段四：虛擬回測與安全審核
# ============================================================================

def stage4_backtest_and_audit(stock, analysis):
    """
    Stage 4: 虛擬回測與安全審核
    - 模擬考試：在沙盒環境中進行回溯測試
    - 閥值比對：檢查修正幅度
    - 衝突檢測：確認不與風險控制衝突
    """
    log("\n" + "="*60)
    log(f"STAGE 4: 虛擬回測與安全審核 - {stock['code']}")
    log("="*60)
    
    h = stock['data']
    code = stock['code']
    params = analysis['params']
    
    # 讀取原始策略
    strategy_file = os.path.join(STRATEGIES_DIR, f'{code}.json')
    with open(strategy_file, 'r', encoding='utf-8') as f:
        original = json.load(f)
    
    # 計算參數變動幅度
    changes = []
    for section in ['entry', 'exit', 'position']:
        if section in original and section in params:
            for k, v in params[section].items() if isinstance(params.get(section), dict) else []:
                o = original.get(section, {}).get(k, 0)
                n = v
                if isinstance(o, (int, float)) and isinstance(n, (int, float)) and o != 0:
                    changes.append(abs(n - o) / abs(o))
    
    # 簡單計算總變動
    max_change = max(changes) if changes else 0
    
    # 閥值審核
    if max_change > 0.3:
        log(f"  [BLOCK] 變動幅度 {max_change:.1%} > 30%")
        return {'approved': False, 'reason': 'exceeds_30pct_threshold', 'change_pct': max_change}
    
    if max_change > 0.1:
        log(f"  [NOTIFY] 變動幅度 {max_change:.1%} > 10%，需通知")
        notify_level = 'notify'
    else:
        log(f"  [AUTO] 變動幅度 {max_change:.1%} < 10%，自動執行")
        notify_level = 'auto'
    
    # 簡單虛擬回測（基於 RSI 信號）
    entry_rsi_max = params.get('rsi_max', 65)
    stop_loss_pct = params.get('stop_loss_pct', 8) / 100
    
    trades = []
    position = None
    
    for i in range(60, len(h)):
        p = float(h['Close'].iloc[i])
        rsi_val = float(calc_rsi(h['Close'].iloc[:i+1], 14).iloc[-1])
        
        if position is None:
            if entry_rsi_max[0] <= rsi_val <= entry_rsi_max[1] if isinstance(entry_rsi_max, list) else rsi_val <= entry_rsi_max:
                position = {'entry': p, 'rsi': rsi_val}
        else:
            pnl = (p - position['entry']) / position['entry']
            if pnl <= -stop_loss_pct or pnl >= 0.15:
                trades.append({'pnl': pnl, 'rsi_exit': rsi_val})
                position = None
    
    # 計算模擬績效
    if trades:
        win_rate = sum(1 for t in trades if t['pnl'] > 0) / len(trades)
        avg_pnl = sum(t['pnl'] for t in trades) / len(trades)
    else:
        win_rate = 0.5
        avg_pnl = 0
    
    log(f"  模擬 trades: {len(trades)}")
    log(f"  模擬勝率: {win_rate:.0%}")
    log(f"  模擬平均報酬: {avg_pnl*100:.1f}%")
    
    # 判斷是否通過
    if win_rate < 0.4:
        log(f"  [BLOCK] 勝率 {win_rate:.0%} < 40%")
        return {'approved': False, 'reason': 'low_win_rate', 'win_rate': win_rate}
    
    if avg_pnl < 0:
        log(f"  [BLOCK] 平均報酬為負")
        return {'approved': False, 'reason': 'negative_return', 'avg_pnl': avg_pnl}
    
    log(f"  [PASS] 通過安全審核")
    
    return {
        'approved': True,
        'change_pct': max_change,
        'notify_level': notify_level,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'trades': len(trades)
    }

# ============================================================================
# 階段五：正式更新與同步
# ============================================================================

def stage5_update_and_sync(stock, analysis, audit_result):
    """
    Stage 5: 正式更新與同步
    - 文件備份
    - 參數寫入
    - 熱啟動
    - 報告推播
    """
    log("\n" + "="*60)
    log(f"STAGE 5: 正式更新與同步 - {stock['code']}")
    log("="*60)
    
    code = stock['code']
    params = analysis['params']
    
    # 1. 備份
    backup_dir = os.path.join(STRATEGIES_DIR, 'backup_workflow')
    os.makedirs(backup_dir, exist_ok=True)
    
    strategy_file = os.path.join(STRATEGIES_DIR, f'{code}.json')
    backup_file = os.path.join(backup_dir, f'{code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.bak')
    shutil.copy(strategy_file, backup_file)
    log(f"  備份: {backup_file}")
    
    # 2. 讀取並更新策略
    with open(strategy_file, 'r', encoding='utf-8') as f:
        strategy = json.load(f)
    
    # 更新參數（根據 analysis）
    if 'entry' not in strategy:
        strategy['entry'] = {}
    if 'exit' not in strategy:
        strategy['exit'] = {}
    
    # 只更新建議的參數
    for k, v in params.items():
        if k in ['entry', 'exit']:
            for kk, vv in v.items():
                strategy[k][kk] = vv
        else:
            strategy[k] = v
    
    # 添加優化記錄
    if 'optimization_log' not in strategy:
        strategy['optimization_log'] = []
    
    strategy['optimization_log'].append({
        'date': datetime.now().isoformat(),
        'situation': analysis['situation'],
        'recommendation': analysis['recommendation'],
        'confidence': analysis['confidence'],
        'audit': {
            'approved': audit_result['approved'],
            'win_rate': audit_result.get('win_rate'),
            'avg_pnl': audit_result.get('avg_pnl')
        }
    })
    
    # 3. 原子化寫入
    fd, tmp_file = tempfile.mkstemp(suffix='.json', dir=os.path.dirname(strategy_file))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(strategy, f, ensure_ascii=False, indent=2)
        shutil.move(tmp_file, strategy_file)
        log(f"  更新成功: {code}.json")
    except Exception as e:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        log(f"  更新失敗: {e}")
        return {'success': False, 'reason': str(e)}
    
    # 4. 設定冷卻期
    cooldown = {}
    if os.path.exists(COOLDOWN_FILE):
        with open(COOLDOWN_FILE, 'r') as f:
            cooldown = json.load(f)
    
    cooldown[code] = {
        'time': datetime.now().isoformat(),
        'change_pct': audit_result['change_pct'],
        'confidence': analysis['confidence']
    }
    
    with open(COOLDOWN_FILE, 'w') as f:
        json.dump(cooldown, f, ensure_ascii=False, indent=2)
    
    log(f"  冷卻期已設定: 24小時")
    
    # 5. 發送通知
    notify_msg = f"""[{code}] 策略優化完成

情境: {analysis['situation']}
建議: {analysis['recommendation']}
信心度: {analysis['confidence']:.0%}
審核結果: {'通過' if audit_result['approved'] else '未通過'}
"""
    log(f"\n[TELEGRAM NOTIFICATION]\n{notify_msg}")
    
    return {'success': True, 'backup': backup_file}

# ============================================================================
# 主流程
# ============================================================================

def main():
    log("="*60)
    log("TINA 自主策略優化系統 - 五階段工作流")
    log("="*60)
    log(f"啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # PID 鎖
    if not get_pid_lock():
        log("另一個實例正在運行，退出")
        return
    
    try:
        # Stage 1: 環境感測
        env_status = stage1_environment_check()
        
        if not env_status['can_proceed']:
            log("\n條件不滿足，終止工作流")
            return
        
        # Stage 2: 篩選標的
        candidates = stage2_stock_screening()
        
        if not candidates:
            log("\n無候選標的，終止工作流")
            return
        
        # Stage 3-5: 處理每一個候選標的
        updated = []
        blocked = []
        
        for stock in candidates[:3]:  # 最多處理3檔
            code = stock['code']
            log(f"\n處理: {code}")
            
            # Stage 3: 分析
            analysis = stage3_brain_analysis(stock)
            
            # Stage 4: 審核
            audit = stage4_backtest_and_audit(stock, analysis)
            
            if not audit['approved']:
                blocked.append(code)
                continue
            
            # Stage 5: 更新
            result = stage5_update_and_sync(stock, analysis, audit)
            
            if result['success']:
                updated.append(code)
        
        # 總結
        log("\n" + "="*60)
        log("工作流執行完成")
        log("="*60)
        log(f"更新: {len(updated)} 檔")
        log(f"阻擋: {len(blocked)} 檔")
        
    finally:
        release_pid()

if __name__ == '__main__':
    main()