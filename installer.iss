; Inno Setup Script for P-Downloader
#define MyAppName "P-Downloader"
#ifndef MyAppVersion
#define MyAppVersion "1.0.3"
#endif
#define MyAppPublisher "P-Downloader Project"
#define MyAppURL "https://github.com/pkgtm2419/p-downloader"
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
CloseApplications=yes
RestartApplications=no
CloseApplicationsFilter=P-Downloader.exe

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
; Auto-start task (HKCU Run)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PDownloader"; ValueData: """{app}\{#MyAppExeName}"" --tray"; Flags: uninsdeletevalue; Tasks: autostart

; Register Chrome Native Messaging Host
Root: HKCU; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.pdownloader.host"; ValueType: string; ValueData: "{app}\com.pdownloader.host.json"; Flags: uninsdeletekey

; Register Edge Native Messaging Host
Root: HKCU; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\com.pdownloader.host"; ValueType: string; ValueData: "{app}\com.pdownloader.host.json"; Flags: uninsdeletekey

; Register Brave Native Messaging Host
Root: HKCU; Subkey: "Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\com.pdownloader.host"; ValueType: string; ValueData: "{app}\com.pdownloader.host.json"; Flags: uninsdeletekey

; Register Chromium Native Messaging Host
Root: HKCU; Subkey: "Software\Chromium\NativeMessagingHosts\com.pdownloader.host"; ValueType: string; ValueData: "{app}\com.pdownloader.host.json"; Flags: uninsdeletekey

; Register Firefox Native Messaging Host
Root: HKCU; Subkey: "Software\Mozilla\NativeMessagingHosts\com.pdownloader.host"; ValueType: string; ValueData: "{app}\com.pdownloader.host.firefox.json"; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  IsUpgradeInstall: Boolean;
  ExistingInstallDir: String;

function GetExistingInstallInfo(var PrevVersion, PrevDir, PrevUninstall: String): Boolean;
var
  AppKey: String;
begin
  Result := False;
  AppKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{5A8D2F82-1234-4C5E-9876-A1B2C3D4E5F6}_is1';

  // Check HKCU (preferred for lowest privilege)
  if RegQueryStringValue(HKCU, AppKey, 'DisplayVersion', PrevVersion) then
  begin
    RegQueryStringValue(HKCU, AppKey, 'InstallLocation', PrevDir);
    RegQueryStringValue(HKCU, AppKey, 'UninstallString', PrevUninstall);
    Result := True;
    Exit;
  end;

  // Fallback to HKLM
  if RegQueryStringValue(HKLM, AppKey, 'DisplayVersion', PrevVersion) then
  begin
    RegQueryStringValue(HKLM, AppKey, 'InstallLocation', PrevDir);
    RegQueryStringValue(HKLM, AppKey, 'UninstallString', PrevUninstall);
    Result := True;
    Exit;
  end;
end;

function InitializeSetup(): Boolean;
var
  PrevVersion, PrevDir, PrevUninstall: String;
  PromptMsg: String;
  BtnSelected: Integer;
  ResultCode: Integer;
begin
  Result := True;
  IsUpgradeInstall := False;
  ExistingInstallDir := '';

  if GetExistingInstallInfo(PrevVersion, PrevDir, PrevUninstall) then
  begin
    PromptMsg := 'P-Downloader version ' + PrevVersion + ' is already installed on your computer.' + #13#10 + #13#10 +
                 'Would you like to upgrade to version {#MyAppVersion}?' + #13#10 + #13#10 +
                 '• Click [Yes] to upgrade (keeps all settings and download history).' + #13#10 +
                 '• Click [No] to perform a clean reinstallation.' + #13#10 +
                 '• Click [Cancel] to exit installer.';

    BtnSelected := MsgBox(PromptMsg, mbConfirmation, MB_YESNOCANCEL);

    if BtnSelected = IDYES then
    begin
      IsUpgradeInstall := True;
      ExistingInstallDir := PrevDir;
    end
    else if BtnSelected = IDNO then
    begin
      IsUpgradeInstall := False;
      if (PrevUninstall <> '') and FileExists(RemoveQuotes(PrevUninstall)) then
      begin
        if MsgBox('Would you like to uninstall the previous version before continuing?', mbConfirmation, MB_YESNO) = IDYES then
        begin
          Exec(RemoveQuotes(PrevUninstall), '/VERYSILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
        end;
      end;
    end
    else
    begin
      Result := False;
      Exit;
    end;
  end;
end;

procedure InitializeWizard();
begin
  if IsUpgradeInstall and (ExistingInstallDir <> '') then
  begin
    WizardForm.DirEdit.Text := ExistingInstallDir;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppExePath: String;
  ManifestJson: String;
  FirefoxManifestJson: String;
begin
  if CurStep = ssPostInstall then
  begin
    AppExePath := ExpandConstant('{app}\{#MyAppExeName}');
    StringChangeEx(AppExePath, '\', '\\', True);

    // Native host manifest for Chrome, Edge, Brave, Chromium
    ManifestJson := '{' + #13#10 +
      '  "name": "com.pdownloader.host",' + #13#10 +
      '  "description": "P-Downloader Ultra Native Messaging Host",' + #13#10 +
      '  "path": "' + AppExePath + '",' + #13#10 +
      '  "type": "stdio",' + #13#10 +
      '  "allowed_origins": [' + #13#10 +
      '    "chrome-extension://mngjniiiieccogdpplbdmmmmnemocbkb/"' + #13#10 +
      '  ]' + #13#10 +
      '}';
    SaveStringToFile(ExpandConstant('{app}\com.pdownloader.host.json'), ManifestJson, False);

    // Native host manifest for Firefox
    FirefoxManifestJson := '{' + #13#10 +
      '  "name": "com.pdownloader.host",' + #13#10 +
      '  "description": "P-Downloader Ultra Native Messaging Host",' + #13#10 +
      '  "path": "' + AppExePath + '",' + #13#10 +
      '  "type": "stdio",' + #13#10 +
      '  "allowed_extensions": [' + #13#10 +
      '    "pdownloader@ultra.download"' + #13#10 +
      '  ]' + #13#10 +
      '}';
    SaveStringToFile(ExpandConstant('{app}\com.pdownloader.host.firefox.json'), FirefoxManifestJson, False);
  end;
end;
