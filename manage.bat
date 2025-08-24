@echo off
REM 量化回测系统服务管理脚本
REM 用法: manage.bat [start|stop|restart|status|logs]

cd /d "%~dp0"

if "%1"=="" (
    echo 用法: %0 [start^|stop^|restart^|status^|logs^|config]
    echo.
    echo   start   - 启动后端服务
    echo   stop    - 停止后端服务  
    echo   restart - 重启后端服务
    echo   status  - 查看服务状态
    echo   logs    - 查看服务日志
    echo   config  - 显示配置
    goto end
)

python unified_service_manager.py %*

:end
pause