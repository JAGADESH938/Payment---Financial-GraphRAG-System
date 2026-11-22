@echo off
cd /d "%~dp0"
echo ========================================================
echo Starting PaymentGraph Streamlit UI...
echo ========================================================
call .venv\Scripts\activate.bat
streamlit run src\app.py
pause
