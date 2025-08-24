@echo off
echo 启动量化回测系统图形化控制台...
cd /d "%~dp0\frontend"
call npm run electron:dev