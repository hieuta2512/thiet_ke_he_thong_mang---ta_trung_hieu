@echo off
chcp 65001 > nul
echo ============================================
echo  NMS - He thong Quan ly Mang LAN + Camera IP
echo  DH Phuong Dong - Do an tot nghiep 2024
echo ============================================
echo.

cd /d "%~dp0backend"

echo [1/3] Kiem tra Python...
python --version 2>nul || (echo KHONG TIM THAY PYTHON! Cai Python 3.9+ va thu lai. && pause && exit /b 1)

echo [2/3] Cai dat thu vien...
pip install -r requirements.txt -q

echo [3/3] Khoi dong NMS server...
echo.
echo  ^>^>^> Truy cap: http://localhost:8000
echo  ^>^>^> Bam Ctrl+C de dung server
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
