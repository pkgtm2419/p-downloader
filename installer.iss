; Inno Setup Script for P-Downloader
#define MyAppName "P-Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "P-Downloader Project"
#define MyAppURL "https://github.com/p-downloader"
#define MyAppExeName "P-Downloader.exe"

[Setup]
AppId={{5A8D2F82-1234-4C5E-9876-A1B2C3D4E5F6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=P-Downloader-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
SetupIconFile=resources\logo.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch P-Downloader on Windows startup"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\P-Downloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Auto-start task
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PDownloader"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: autostart

; Register Chrome Native Messaging Host
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.pdownloader.host"; ValueType: string; ValueData: "{userappdata}\.pdownloader\com.pdownloader.host.json"; Flags: uninsdeletekey

; Register Edge Native Messaging Host
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\com.pdownloader.host"; ValueType: string; ValueData: "{userappdata}\.pdownloader\com.pdownloader.host.json"; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
