@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-all.ps1" %*
exit /b %ERRORLEVEL%
