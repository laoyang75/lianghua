@echo off
echo 启动量化回测系统图形化控制台...
echo.
echo ⚠️  注意：此脚本已更新，现在只启动Vite服务
echo 💡 建议：使用 service_manager_gui.py 进行完整的分步控制
echo.
cd /d "%~dp0\frontend"
call npm run dev