#!/bin/bash
echo "============================================"
echo " NMS — Hệ thống Quản lý Mạng LAN + Camera"
echo " ĐH Phương Đông · Đồ án tốt nghiệp 2024"
echo "============================================"
cd "$(dirname "$0")/backend"
echo "[1/3] Kiểm tra Python..."
python3 --version || { echo "Cần Python 3.9+"; exit 1; }
echo "[2/3] Cài thư viện..."
pip3 install -r requirements.txt -q
echo "[3/3] Khởi động server → http://localhost:8000"
echo "      Ctrl+C để dừng"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
