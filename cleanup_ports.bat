@echo off
echo 正在清理端口占用...

REM 清理5187-5200端口范围的所有进程
for /L %%i in (5187,1,5200) do (
    echo 清理端口 %%i
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%%i ^| findstr LISTENING') do (
        echo 终止PID: %%a
        taskkill //PID %%a //F >nul 2>&1
    )
)

echo 清理完成！
pause