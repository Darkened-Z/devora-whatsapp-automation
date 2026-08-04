@echo off
title Disable Auto-Start
color 0C

powershell -NoProfile -ExecutionPolicy Bypass -Command "Remove-Item ([Environment]::GetFolderPath('Startup')+'\WhatsApp Auto Replier.lnk') -ErrorAction SilentlyContinue"

echo.
echo  ============================================
echo   Auto-Start DISABLED
echo  ============================================
echo.
echo  The Auto Replier will no longer start automatically.
echo  You can still run it manually with start.bat
echo.
pause
