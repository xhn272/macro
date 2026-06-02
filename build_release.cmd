@echo off
chcp 65001 >nul

:: ============================================================
::  按键宏管理器 - 一键发布打包脚本
:: ============================================================
::  生成三种发布格式:
::    1. 单文件 exe         (MacroManager_vX.X.X.exe)
::    2. 便携版 zip          (MacroManager_vX.X.X_portable.zip)
::    3. 安装包 exe         (MacroManager_Setup_vX.X.X.exe)
:: ============================================================

:: ---------- 配置 ----------
set VERSION=1.1.0
set PROJECT_DIR=C:\Users\Administrator\PycharmProjects\macro
set DESKTOP=C:\Users\Administrator\Desktop
set PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe
set ICON=%PROJECT_DIR%\keyboard_5643.ico
set RELEASE_DIR=%PROJECT_DIR%\release\%VERSION%
set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
set UPX_DIR=C:\Users\Administrator\PycharmProjects\macro\upx-5.1.1-win64
set MAIN_SCRIPT=%PROJECT_DIR%\macro.py

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║     按键宏管理器 v%VERSION% 发布打包              ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ---------- 清理 ----------
echo [1/5] 清理旧构建产物...
if exist "%DESKTOP%\macro.dist" rmdir /s /q "%DESKTOP%\macro.dist"
if exist "%DESKTOP%\macro.build" rmdir /s /q "%DESKTOP%\macro.build"
if exist "%DESKTOP%\macro.onefile-build" rmdir /s /q "%DESKTOP%\macro.onefile-build"
if exist "%DESKTOP%\macro.exe" del /q "%DESKTOP%\macro.exe"
if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
echo        清理完成.

:: ---------- 构建 standalone（多文件版）----------
echo.
echo [2/5] 构建 standalone 版本（多文件）...
echo        这需要几分钟...
call %PYTHON% -m nuitka --standalone --windows-disable-console --remove-output --show-progress --show-memory --windows-icon-from-ico=%ICON% --output-dir=%DESKTOP% --enable-plugin=tk-inter --follow-imports --lto=yes --windows-uac-admin %MAIN_SCRIPT%
if errorlevel 1 goto :error_standalone
echo        standalone 构建完成.

:: ---------- 创建 zip ----------
echo.
echo [3/5] 创建便携版 zip...
call powershell -NoProfile -Command "$dest = '%RELEASE_DIR%\MacroManager_v%VERSION%_portable.zip'; if (Test-Path $dest) { Remove-Item $dest -Force }; Compress-Archive -Path '%DESKTOP%\macro.dist\*' -DestinationPath $dest -CompressionLevel Optimal"
if errorlevel 1 goto :error_zip
echo        zip 创建完成.

:: ---------- 构建安装包 ----------
echo.
echo [4/5] 构建安装包...
if not exist "%ISCC%" goto :skip_iscc
echo        正在编译 Inno Setup 安装包...
call "%ISCC%" /Qp "%PROJECT_DIR%\setup.iss"
if errorlevel 1 goto :error_iscc
echo        安装包构建完成.
goto :after_iscc

:skip_iscc
echo        [警告] 未找到 Inno Setup Compiler，跳过安装包构建.
echo        安装路径应为: %ISCC%
echo        请从 https://jrsoftware.org/isdl.php 下载安装 Inno Setup.
:after_iscc

:: ---------- 构建 onefile（单文件版）----------
echo.
echo [5/5] 构建 onefile 版本（单文件 + UPX）...
echo        这需要几分钟...
call %PYTHON% -m nuitka --onefile --standalone --windows-disable-console --remove-output --show-progress --show-memory --windows-icon-from-ico=%ICON% --output-dir=%DESKTOP% --enable-plugin=tk-inter,upx --upx-binary=%UPX_DIR% --follow-imports --lto=yes --windows-uac-admin %MAIN_SCRIPT%
if errorlevel 1 goto :error_onefile

move /y "%DESKTOP%\macro.exe" "%RELEASE_DIR%\MacroManager_v%VERSION%.exe" >nul
echo        onefile 构建完成.

:: ---------- 完成 ----------
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  ✅ 打包完成!                                   ║
echo  ╠══════════════════════════════════════════════════╣
echo  ║  输出目录: release\%VERSION%\                    ║
echo  ╚══════════════════════════════════════════════════╝
echo.
dir /b "%RELEASE_DIR%"
echo.
pause
exit /b 0

:: ---------- 错误处理 ----------
:error_standalone
echo [错误] standalone 构建失败!
pause
exit /b 1

:error_zip
echo [错误] zip 创建失败!
pause
exit /b 1

:error_iscc
echo [错误] 安装包编译失败!
pause
exit /b 1

:error_onefile
echo [错误] onefile 构建失败!
pause
exit /b 1
