#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  HỆ THỐNG QUẢN LÝ TRUNG TÂM IELTS"
echo "=========================================="

echo "[1/3] Cài đặt thư viện..."
pip install -r requirements.txt

if [ ! -f "instance/ielts_center.db" ]; then
  echo "[2/3] Tạo cơ sở dữ liệu và dữ liệu mẫu..."
  python seed.py
else
  echo "[2/3] Đã có cơ sở dữ liệu, bỏ qua bước tạo dữ liệu mẫu."
fi

echo "[3/3] Khởi động website tại http://127.0.0.1:5000 (Ctrl+C để dừng)"
python app.py
