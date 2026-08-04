@echo off
title WhatsApp Auto Replier
color 0A
echo.
echo  ============================================
echo   WhatsApp Auto Replier - Starting...
echo  ============================================
echo.
echo  Dashboard will open at: http://localhost:3000
echo  Keep this window open while the bot is running.
echo  Close this window to stop the bot.
echo.

:: Open browser after 4 seconds
start "" cmd /c "timeout /t 4 /nobreak > nul && start http://localhost:3000"

:: Start the bot — use the bundled Node runtime if present, else system Node
if exist "%~dp0node.exe" (
    "%~dp0node.exe" "%~dp0server.js"
) else (
    node "%~dp0server.js"
)

echo.
echo  Bot has stopped.
pause
