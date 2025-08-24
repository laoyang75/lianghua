@echo off
REM 后端服务启动脚本
cd /d "%~dp0\backend"
python app/main.py --port 5318 --host 127.0.0.1