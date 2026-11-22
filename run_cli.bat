@echo off
cd /d "%~dp0"
echo ========================================================
echo Starting PaymentGraph CLI Interactive System...
echo ========================================================
call .venv\Scripts\activate.bat
python src\cli.py
pause
