@echo off
REM Ray DCA 回測批次腳本
REM 用法: run_dca_backtest.bat [ETF代碼] [金額]
set SCRIPT_DIR=%~dp0
cd /d C:\Users\USER\.openclaw\workspace\Tina_Quant_System
python -c "from teams.ray.scripts.dca_backtest import dca_backtest; import sys; etf=sys.argv[1] if len(sys.argv)>1 else '00919'; amt=int(sys.argv[2]) if len(sys.argv)>2 else 1000; r=dca_backtest(etf, amt)" %1 %2