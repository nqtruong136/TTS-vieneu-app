@echo off
title VieNeu-TTS Studio
chcp 65001 > nul

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [THÔNG BÁO] Chưa tìm thấy môi trường ảo .venv. Đang tạo tự động...
    uv venv .venv
    echo [THÔNG BÁO] Đang cài đặt thư viện cần thiết...
    uv pip install --python .venv\Scripts\python.exe -r requirements.txt
)

echo [INFO] Đang khởi động VieNeu-TTS Studio...
start "" ".venv\Scripts\pythonw.exe" main.py
exit

