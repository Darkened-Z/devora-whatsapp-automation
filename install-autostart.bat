@echo off
title Enable Auto-Start
color 0A

:: Pass paths to PowerShell via environment variables to avoid quoting issues.
set "TARGET=%~dp0start.bat"
set "WORKDIR=%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Startup')+'\WhatsApp Auto Replier.lnk'); $s.TargetPath=$env:TARGET; $s.WorkingDirectory=$env:WORKDIR; $s.WindowStyle=7; $s.Description='WhatsApp Auto Replier'; $s.Save()"

echo.
echo  ============================================
echo   Auto-Start ENABLED
echo  ============================================
echo.
echo  The Auto Replier will now launch automatically
echo  whenever this PC starts (minimised to the taskbar).
echo.
echo  To turn this off, run: uninstall-autostart.bat
echo.
pause
