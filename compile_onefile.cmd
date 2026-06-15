@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================================
::  按键宏管理器 - 单文件版构建
::  输出: release\%VERSION%\MacroManager_v%VERSION%.exe
:: ============================================================

:: ---------- 配置 ----------
set VERSION=1.3.2
set PROJECT_DIR=C:\Users\Administrator\PycharmProjects\macro
set DESKTOP=C:\Users\Administrator\Desktop
set PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe
set ICON=%PROJECT_DIR%\keyboard_5643.ico
set RELEASE_DIR=%PROJECT_DIR%\release\%VERSION%
set UPX_DIR=C:\Users\Administrator\PycharmProjects\macro\upx-5.1.1-win64
set MAIN_SCRIPT=%PROJECT_DIR%\macro.py

echo.
echo  构建单文件版 v%VERSION%...

:: ---------- 清理 ----------
if exist "%DESKTOP%\macro.exe" del /q "%DESKTOP%\macro.exe"
if exist "%DESKTOP%\macro.onefile-build" rmdir /s /q "%DESKTOP%\macro.onefile-build"

:: ---------- 构建 ----------
%PYTHON% -m nuitka --onefile --standalone --windows-disable-console --remove-output --show-progress --show-memory --windows-icon-from-ico=%ICON% --output-dir=%DESKTOP% --enable-plugin=tk-inter,upx --upx-binary=%UPX_DIR% --follow-imports --lto=yes --windows-uac-admin %MAIN_SCRIPT%
if %ERRORLEVEL% neq 0 (
    echo [错误] 构建失败!
    pause
    exit /b 1
)

:: ---------- 移动并重命名 ----------
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
move /y "%DESKTOP%\macro.exe" "%RELEASE_DIR%\MacroManager_v%VERSION%.exe" >nul

echo  完成: release\%VERSION%\MacroManager_v%VERSION%.exe
echo.

endlocal