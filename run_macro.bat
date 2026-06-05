@echo off
:: Auto-elevate to admin if needed
net session >nul 2>&1
if %errorlevel% equ 0 goto :run

set "vbs=%temp%\elevate.vbs"
echo Set UAC = CreateObject^("Shell.Application"^) >"%vbs%"
echo UAC.ShellExecute "%~f0", "", "", "runas", 1 >>"%vbs%"
cscript //nologo "%vbs%"
del "%vbs%"
exit /b

:run
cd /d "%~dp0"
".venv\Scripts\python.exe" "macro.py" 2>nul
pause
