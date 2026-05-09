@echo off
:: Tina Streamlit Launcher — Double-click to open GUI
:: Streamlit path: C:\Users\USER\.openclaw\workspace\Tina_Quant_System\streamlit_tw_stock.py

cd /d C:\Users\USER\.openclaw\workspace\Tina_Quant_System
start "" "http://localhost:8501"
streamlit run streamlit_tw_stock.py --server.port 8501 --server.headless true
pause