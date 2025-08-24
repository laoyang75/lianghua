@echo off
echo ===============================================
echo    Node.js 进程彻底清理工具
echo ===============================================
echo.

echo 🔍 检查当前Node.js进程数量...
for /f %%i in ('tasklist /fi "imagename eq node.exe" 2^>nul ^| find /c "node.exe"') do set NODE_COUNT=%%i
echo 发现 %NODE_COUNT% 个 node.exe 进程

if %NODE_COUNT% GTR 0 (
    echo.
    echo ⚠️  警告：发现异常多的Node.js进程！
    echo 📋 当前Node.js进程列表：
    tasklist | findstr node.exe
    echo.
    
    set /p choice="是否要终止所有Node.js进程？(y/N): "
    if /i "!choice!"=="y" (
        echo.
        echo 🗑️  正在终止所有Node.js进程...
        taskkill /f /im node.exe >nul 2>&1
        
        echo ✅ Node.js进程清理完成
        echo.
        echo 🔍 验证清理结果...
        for /f %%i in ('tasklist /fi "imagename eq node.exe" 2^>nul ^| find /c "node.exe"') do set REMAINING=%%i
        echo 剩余Node.js进程: !REMAINING! 个
        
        if !REMAINING! EQU 0 (
            echo ✅ 所有Node.js进程已成功清理
        ) else (
            echo ⚠️  仍有 !REMAINING! 个进程未清理，可能需要管理员权限
        )
    ) else (
        echo 👌 已取消清理操作
    )
) else (
    echo ✅ 未发现Node.js进程
)

echo.
echo 🔍 检查重要端口占用情况...
echo 端口 5187 (前端):
netstat -ano | findstr :5187
echo 端口 5318 (后端):
netstat -ano | findstr :5318

echo.
echo ===============================================
echo 清理完成！现在可以安全启动服务了
echo ===============================================
pause