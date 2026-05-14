# -*- coding: utf-8 -*-
"""
OpenClaw Gateway 自動監控腳本
每5分鐘檢查並重啟被關閉的服務
"""
import sys
import os
import time
import subprocess
import psutil
import logging
from datetime import datetime

# 日誌設定
LOG_FILE = 'Tina_Quant_System/logs/openclaw_monitor.log'
os.makedirs('Tina_Quant_System/logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_gateway_running():
    """檢查 OpenClaw Gateway 是否運行中"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline:
                cmd_str = ' '.join(cmdline).lower()
                # 檢查是否包含 openclaw gateway
                if 'openclaw' in cmd_str and ('gateway' in cmd_str or 'node' in cmd_str):
                    return True
                # 檢查 node.exe 運行 openclaw
                if 'node' in cmd_str.lower() and 'openclaw' in cmd_str.lower():
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def restart_gateway():
    """重新啟動 OpenClaw Gateway"""
    logger.info('檢測到 OpenClaw Gateway 未運行，正在重啟...')
    
    # 方法1: 使用 openclaw gateway start
    try:
        result = subprocess.run(
            ['openclaw', 'gateway', 'start'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.info('OpenClaw Gateway 啟動成功')
            return True
        else:
            logger.warning('openclaw gateway start 返回: %s' % result.stderr)
    except Exception as e:
        logger.warning('方法1失敗: %s' % str(e))
    
    # 方法2: 使用 bat 腳本
    bat_path = 'Tina_Quant_System/openclaw_gateway.bat'
    if os.path.exists(bat_path):
        try:
            subprocess.Popen(
                ['cmd', '/c', 'start', 'openclaw_gateway', bat_path],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            logger.info('使用 bat 腳本啟動 OpenClaw Gateway')
            return True
        except Exception as e:
            logger.warning('方法2失敗: %s' % str(e))
    
    # 方法3: 直接用 node 啟動
    try:
        node_path = subprocess.run(['where', 'node'], capture_output=True, text=True)
        if node_path.returncode == 0:
            npm_path = os.path.join(os.environ.get('APPDATA', ''), 'npm', 'node_modules', 'openclaw', 'bin', 'openclaw.js')
            if os.path.exists(npm_path):
                subprocess.Popen(
                    ['node', npm_path, 'gateway', 'start'],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
                logger.info('使用 node 直接啟動 OpenClaw Gateway')
                return True
    except Exception as e:
        logger.warning('方法3失敗: %s' % str(e))
    
    logger.error('所有啟動方法皆失敗')
    return False

def check_and_restart():
    """檢查並重啟"""
    if is_gateway_running():
        logger.info('OpenClaw Gateway 運行正常')
        return True
    else:
        return restart_gateway()

def main():
    logger.info('='*50)
    logger.info('OpenClaw Gateway 自動監控已啟動')
    logger.info('每5分鐘檢查一次')
    logger.info('='*50)
    
    check_count = 0
    restart_count = 0
    
    while True:
        check_count += 1
        logger.info('[檢查 #%d] %s' % (check_count, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        if not is_gateway_running():
            restart_count += 1
            logger.warning('檢測到服務未運行!')
            if restart_gateway():
                logger.info('重啟成功!')
            else:
                logger.error('重啟失敗，5分鐘後再試')
        else:
            logger.info('服務正常運行')
        
        logger.info('等待5分鐘...')
        time.sleep(300)  # 5 分鐘 = 300 秒

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('監控腳本已停止')
    except Exception as e:
        logger.error('腳本錯誤: %s' % str(e))
        sys.exit(1)