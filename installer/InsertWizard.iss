; =====================================================================
; InsertWizard – Fusion 360 Add-In Installer (Windows 11)
; Repo root:        C:\Data\github\InsertWizard
; Add-In source:    C:\Data\github\InsertWizard\InsertWizard
; Installer script: C:\Data\github\InsertWizard\installer\InsertWizard.iss
; =====================================================================

#define MyAppName "InsertWizard"
#define MyAppPublisher "know-how-schmiede"
#define MyAppURL "https://github.com/know-how-schmiede/InsertWizard"
#define MyAppVersion "0.4.1"

[Setup]
AppId={{9C9F5D3C-9B61-4E7F-9A9A-0A1A2B6D8B1F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={userappdata}\Autodesk\Autodesk Fusion 360\API\AddIns\{#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
DisableWelcomePage=no
DisableReadyPage=no
OutputDir={#SourcePath}\..\dist
OutputBaseFilename={#MyAppName}_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[InstallDelete]
; Remove old installation completely (clean install)
Type: filesandordirs; Name: "{app}"

[Files]
; Copy the REAL Fusion Add-In folder
; {#SourcePath} = C:\Data\github\InsertWizard\installer
; ..\InsertWizard = C:\Data\github\InsertWizard\InsertWizard
Source: "{#SourcePath}\..\InsertWizard\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion; \
    Excludes: ".git\*;.vscode\*;__pycache__\*"

[Run]
Filename: "explorer.exe"; Parameters: """{app}"""; \
    Flags: postinstall shellexec skipifsilent

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
