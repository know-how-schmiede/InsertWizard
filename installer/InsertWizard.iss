; =====================================================================
; InsertWizard – Fusion 360 Add-In Installer (Windows 11)
; Repo root:      C:\Data\github\InsertWizard
; Add-In source:   C:\Data\github\InsertWizard\InsertWizard
; Installer script: C:\Data\github\InsertWizard\installer\InsertWizard.iss
; =====================================================================

#define MyAppName "InsertWizard"
#define MyAppPublisher "know-how-schmiede"
#define MyAppURL "https://github.com/know-how-schmiede/InsertWizard"
#define MyAppVersion "0.4.3"

[Setup]
; --- Identität ---
AppId={{9C9F5D3C-9B61-4E7F-9A9A-0A1A2B6D8B1F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}

; --- Dateieigenschaften (Wichtig gegen False-Positives) ---
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Fusion 360 Add-In Installer für {#MyAppName}
VersionInfoCopyright=Copyright (C) 2026 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}

; --- Installationspfad ---
DefaultDirName={userappdata}\Autodesk\Autodesk Fusion 360\API\AddIns\{#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=yes

; --- Optik & Verhalten ---
DisableWelcomePage=no
DisableReadyPage=no
OutputDir={#SourcePath}\..\dist
; Kleiner Trick: "Setup" im Namen vermeiden, falls Defender weiterhin blockt
OutputBaseFilename={#MyAppName}_v{#MyAppVersion}_Win64
Compression=lzma2/max
SolidCompression=no
PrivilegesRequired=lowest
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[InstallDelete]
; Saubere Neuinstallation sicherstellen
Type: filesandordirs; Name: "{app}"

[Files]
; Hauptquelle des Add-Ins
Source: "{#SourcePath}\..\InsertWizard\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion; \
    Excludes: ".git\*;.vscode\*;__pycache__\*;*.pyc"

[Code]
function InitializeSetup(): Boolean;
var
  AddInsPath: string;
begin
  AddInsPath := ExpandConstant('{userappdata}\Autodesk\Autodesk Fusion 360\API\AddIns');

  if not DirExists(AddInsPath) then
  begin
    MsgBox(
      'Fusion 360 AddIns-Ordner nicht gefunden:' + #13#10 +
      AddInsPath + #13#10#13#10 +
      'Bitte Fusion 360 mindestens einmal starten und den Installer erneut ausführen.',
      mbError, MB_OK);
    Result := False;
    exit;
  end;

  Result := True;
end;