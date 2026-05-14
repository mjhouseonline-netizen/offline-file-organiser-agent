#ifndef MyAppName
#define MyAppName "Offline File Organiser Agent"
#endif
#ifndef MyAppVersion
#define MyAppVersion "1.0"
#endif
#ifndef MyAppPublisher
#define MyAppPublisher "Offline File Organiser Agent"
#endif
#ifndef MyAppExeName
#define MyAppExeName "Offline-File-Organiser-Agent.exe"
#endif
#ifndef MyAppSourceDir
#define MyAppSourceDir "dist\windows"
#endif
#ifndef MyAppIconFile
#define MyAppIconFile "assets\app.ico"
#endif

[Setup]
AppId={{5B96C1AE-4457-4C72-A311-8B9722A3C481}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=dist\setup
OutputBaseFilename=Offline-File-Organiser-Agent-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}
#ifexist "{#MyAppIconFile}"
SetupIconFile={#MyAppIconFile}
#endif

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "{#MyAppSourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
