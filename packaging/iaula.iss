#define MyAppName "IAula Virtual"
#define MyAppPublisher "VxGM"
#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{B7C4E1A2-9F3D-4E58-A6D1-2C8F5B0E7A94}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\IAulaVirtual
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=IAulaVirtual-Setup-{#MyAppVersion}
SetupIconFile=iaula.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\IAulaVirtual.exe
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[CustomMessages]
spanish.CreateDesktopIcon=Crear un acceso directo en el escritorio

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\build\dist\IAulaVirtual\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\IAulaVirtual.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\IAulaVirtual.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\IAulaVirtual.exe"; Description: "Abrir {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "schtasks.exe"; Parameters: "/Delete /F /TN ""IAula-Check"""; Flags: runhidden; RunOnceId: "DelTask"

[UninstallDelete]
; Desinstalación profunda: datos del usuario, navegador interno y restos
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\IAulaVirtual"
Type: filesandordirs; Name: "{localappdata}\ms-playwright"
Type: filesandordirs; Name: "{userappdata}\IAulaVirtual"
Type: files; Name: "{userdocs}\IAula Virtual*"
