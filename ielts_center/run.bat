@echo off
chcp 65001 >nul
echo ==========================================
echo   HE THONG QUAN LY TRUNG TAM IELTS
echo ==========================================
echo.

echo [1/3] Cai dat thu vien...
pip install -r requirements.txt

if not exist "instance\ielts_center.db" (
  echo.
  echo [2/3] Tao co so du lieu va du lieu mau...
  python seed.py
) else (
  echo.
  echo [2/3] Da co co so du lieu, bo qua buoc tao du lieu mau.
)

echo.
echo [3/3] Khoi dong website tai http://127.0.0.1:5000
echo Nhan Ctrl+C de dung.
echo.
python app.py
pause
