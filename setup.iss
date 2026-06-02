; ============================================================
; 按键宏管理器 - Inno Setup 安装脚本
; ============================================================
; 用法:
;   1. 先运行 compile.cmd 生成 standalone 文件夹 (macro.dist)
;   2. 再运行 iscc setup.iss (或双击此文件用 Inno Setup Compiler 打开编译)
;   3. 生成的安装包在 release\ 目录下
;
; 也可直接运行 build_release.cmd 一键完成所有步骤
;
; build_release.cmd 会通过命令行 /D 参数传入版本号和路径:
;   iscc /DAppVersion=1.0.0 /DSourceDir=... setup.iss
; ============================================================

; —— 以下值可通过命令行 /D 覆盖 ——
#ifndef AppName
  #define AppName "按键宏管理器"
#endif
#ifndef AppNameEn
  #define AppNameEn "macro"
#endif
#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif
#ifndef AppPublisher
  #define AppPublisher "xhn272"
#endif
#ifndef AppURL
  #define AppURL ""
#endif
#ifndef SourceDir
  #define SourceDir "C:\Users\Administrator\Desktop\macro.dist"
#endif
#ifndef IconFile
  #define IconFile "C:\Users\Administrator\PycharmProjects\macro\keyboard_5643.ico"
#endif

[Setup]
; 基本信息
AppName={#AppName}
AppId={{A1B2C3D4-1234-5678-9ABC-DEF012345678}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}

; 安装路径（默认 Program Files\MacroManager）
DefaultDirName={autopf}\{#AppNameEn}
; 开始菜单文件夹
DefaultGroupName={#AppName}
; 允许用户选择安装路径
DisableDirPage=no
; 不允许取消 "选择开始菜单文件夹" 页面
DisableProgramGroupPage=no

; 输出文件
OutputDir=C:\Users\Administrator\PycharmProjects\macro\release\{#AppVersion}
OutputBaseFilename=MacroManager_Setup_v{#AppVersion}

; 安装器外观
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\macro.exe
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes

; 权限（本程序需要管理员权限）
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 安装器元数据
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Windows 键盘宏管理器

; 64位（Python 通常打包为 64 位）
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; 桌面快捷方式
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; 程序所有文件
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#AppName}"; Filename: "{app}\macro.exe"; WorkingDir: "{app}"; IconFilename: "{app}\macro.exe"
; 开始菜单 → 卸载
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
; 桌面快捷方式（可选）
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\macro.exe"; WorkingDir: "{app}"; IconFilename: "{app}\macro.exe"; Tasks: desktopicon

[Run]
; 安装完成后询问是否启动
Filename: "{app}\macro.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallRun]
; 卸载前确保程序已关闭
Filename: "taskkill"; Parameters: "/f /im macro.exe"; Flags: runhidden skipifdoesntexist; RunOnceId: "KillMacro"

[Code]
// 安装前检查是否有旧版本在运行
function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  // 尝试结束旧进程
  Exec('taskkill', '/f /im macro.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;
