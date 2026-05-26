#define MyAppName "CZN Auto"
#define MyAppVersion "0.1.0"
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
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\CZNAuto\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\run_min_loop_exe.bat"; DestDir: "{app}"; DestName: "run_min_loop.bat"; Flags: ignoreversion
Source: "..\run_one_click_exe.bat"; DestDir: "{app}"; DestName: "run_one_click.bat"; Flags: ignoreversion
Source: "..\stop_czn_auto_exe.bat"; DestDir: "{app}"; DestName: "stop_czn_auto.bat"; Flags: ignoreversion

[Icons]
Name: "{group}\CZN Auto"; Filename: "{app}\run_min_loop.bat"; WorkingDir: "{app}"
Name: "{group}\CZN Auto One Click Test"; Filename: "{app}\run_one_click.bat"; WorkingDir: "{app}"
Name: "{group}\Stop CZN Auto"; Filename: "{app}\stop_czn_auto.bat"; WorkingDir: "{app}"
Name: "{group}\Uninstall CZN Auto"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CZN Auto"; Filename: "{app}\run_min_loop.bat"; WorkingDir: "{app}"; Tasks: desktopicon
