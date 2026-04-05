@echo off
title FraudGuard Server
echo Starting the FraudGuard API & Frontend...
set PYTHONPATH=.
call venv\Scripts\activate.bat
python api\app.py
pause
