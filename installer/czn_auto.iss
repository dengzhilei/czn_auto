#define MyAppName "CZN Auto"
#define MyAppVersion "0.1.8"
#define MyAppPublisher "dengzhilei"
#define MyAppExeName "CZNAuto.exe"

[Setup]
AppId={{7F95F571-457B-45E0-97EA-9F132AD9B26A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=CZNAutoSetup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\CZNAuto\*"; DestDir: "{app}"; Excludes: "config.json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\start_czn_auto_exe.bat"; DestDir: "{app}"; DestName: "start_czn_auto.bat"; Flags: ignoreversion
Source: "..\start_czn_auto_simplified_exe.bat"; DestDir: "{app}"; DestName: "start_czn_auto_simplified.bat"; Flags: ignoreversion
Source: "..\start_czn_auto_traditional_exe.bat"; DestDir: "{app}"; DestName: "start_czn_auto_traditional.bat"; Flags: ignoreversion
Source: "..\run_one_click_exe.bat"; DestDir: "{app}"; DestName: "run_one_click.bat"; Flags: ignoreversion
Source: "..\stop_czn_auto_exe.bat"; DestDir: "{app}"; DestName: "stop_czn_auto.bat"; Flags: ignoreversion
Source: "..\open_config_exe.bat"; DestDir: "{app}"; DestName: "open_config.bat"; Flags: ignoreversion
Source: "..\choose_ui_language.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.example.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.example.json"; DestDir: "{app}"; DestName: "config.json"; Flags: ignoreversion onlyifdoesntexist
Source: "..\CONFIG.md"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: files; Name: "{app}\run_min_loop.bat"
Type: files; Name: "{app}\start_czn_auto_mouse.bat"

[Icons]
Name: "{group}\CZN Auto"; Filename: "{app}\start_czn_auto.bat"; WorkingDir: "{app}"
Name: "{group}\CZN Auto Simplified Chinese"; Filename: "{app}\start_czn_auto_simplified.bat"; WorkingDir: "{app}"
Name: "{group}\CZN Auto Traditional Chinese"; Filename: "{app}\start_czn_auto_traditional.bat"; WorkingDir: "{app}"
Name: "{group}\CZN Auto One Click Test"; Filename: "{app}\run_one_click.bat"; WorkingDir: "{app}"
Name: "{group}\Open CZN Auto Config"; Filename: "{app}\open_config.bat"; WorkingDir: "{app}"
Name: "{group}\Stop CZN Auto"; Filename: "{app}\stop_czn_auto.bat"; WorkingDir: "{app}"
Name: "{group}\Uninstall CZN Auto"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CZN Auto"; Filename: "{app}\start_czn_auto.bat"; WorkingDir: "{app}"; Tasks: desktopicon
