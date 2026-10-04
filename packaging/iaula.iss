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
spanish.DownloadChromium=Descargar el navegador interno ahora (~180 MB, una sola vez)

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "Accesos directos:"
Name: "chromium"; Description: "{cm:DownloadChromium}"; GroupDescription: "Componentes opcionales:"

[Files]
Source: "..\build\dist\IAulaVirtual\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\IAulaVirtual.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\IAulaVirtual.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\IAulaVirtual.exe"; Parameters: "--ensure-deps"; Flags: runhidden waituntilterminated; Tasks: chromium; StatusMsg: "Descargando el navegador interno…"
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

[Code]
const
  WebView2RegLM = 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2RegCU = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  WebView2URL = 'https://go.microsoft.com/fwlink/p/?LinkId=2124701';

var
  DepPage: TWizardPage;
  DepStatus: TNewStaticText;
  DepBar: TNewProgressBar;

procedure SetStatus(const Text: String);
begin
  DepStatus.Caption := Text;
  WizardForm.Repaint;
end;

procedure SetProgress(Value: Integer);
begin
  DepBar.Position := Value;
  WizardForm.Repaint;
end;

function IsWebView2Installed: Boolean;
begin
  Result := RegKeyExists(HKLM, WebView2RegLM) or RegKeyExists(HKCU, WebView2RegCU);
end;

function ChromiumExePath: String;
var
  FindRec: TFindRec;
  Base: String;
begin
  Result := '';
  Base := ExpandConstant('{localappdata}\ms-playwright');
  if FindFirst(Base + '\chromium-*', FindRec) then
  begin
    repeat
      if ((FindRec.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
         FileExists(Base + '\' + FindRec.Name + '\chrome-win\chrome.exe') then
      begin
        Result := Base + '\' + FindRec.Name + '\chrome-win\chrome.exe';
        Break;
      end;
    until not FindNext(FindRec);
    FindClose(FindRec);
  end;
end;

function InstallWebView2: Boolean;
var
  Dl: TDownloadURL;
  SetupPath: String;
  Res: Integer;
begin
  Result := False;
  SetupPath := ExpandConstant('{tmp}\EdgeWebView2Setup.exe');
  SetStatus('WebView2 Runtime no detectado. Descargando…');
  SetProgress(20);
  Dl := TDownloadURL.Create;
  try
    Dl.URL := WebView2URL;
    Dl.FileName := SetupPath;
    try
      Dl.Execute;
    except
      SetProgress(0);
      MsgBox('No se pudo descargar WebView2 Runtime. Revisa tu conexión a Internet.', mbError, MB_OK);
      Exit;
    end;
  finally
    Dl.Free;
  end;
  SetStatus('Instalando WebView2 Runtime…');
  SetProgress(60);
  if Exec(SetupPath, '/silent /install', '', SW_SHOW, ewWaitUntilTerminated, Res) then
  begin
    SetProgress(100);
    Result := (Res = 0) and IsWebView2Installed();
    if not Result then
      MsgBox('WebView2 Runtime no pudo instalarse (código ' + IntToStr(Res) + ').', mbError, MB_OK);
  end
  else
  begin
    SetProgress(0);
    MsgBox('No se pudo ejecutar el instalador de WebView2 Runtime.', mbError, MB_OK);
  end;
end;

function VerifyDependencies: Boolean;
var
  ChromiumPath: String;
begin
  Result := False;
  if IsWebView2Installed() then
    SetStatus('WebView2 Runtime: instalado')
  else if InstallWebView2() then
    SetStatus('WebView2 Runtime: instalado')
  else
    Exit;

  ChromiumPath := ChromiumExePath();
  if ChromiumPath <> '' then
    SetStatus(DepStatus.Caption + #13#10 + 'Navegador interno: instalado')
  else if IsTaskSelected('chromium') then
    SetStatus(DepStatus.Caption + #13#10 + 'Navegador interno: se descargará al finalizar')
  else
    SetStatus(DepStatus.Caption + #13#10 + 'Navegador interno: se descargará en el primer inicio');

  Result := True;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = DepPage.ID then
    Result := VerifyDependencies();
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = DepPage.ID then
  begin
    if IsWebView2Installed() then
      SetStatus('WebView2 Runtime: instalado')
    else
      SetStatus('WebView2 Runtime: no detectado (se instalará al pulsar Siguiente)');
    if ChromiumExePath() <> '' then
      SetStatus(DepStatus.Caption + #13#10 + 'Navegador interno: instalado')
    else if IsTaskSelected('chromium') then
      SetStatus(DepStatus.Caption + #13#10 + 'Navegador interno: se descargará al finalizar')
    else
      SetStatus(DepStatus.Caption + #13#10 + 'Navegador interno: se descargará en el primer inicio');
  end;
end;

procedure InitializeWizard;
begin
  DepPage := CreateCustomPage(wpSelectTasks, 'Dependencias del sistema',
    'IAula Virtual verifica e instala lo que necesita para funcionar.');
  DepStatus := TNewStaticText.Create(DepPage);
  DepStatus.Parent := DepPage.Surface;
  DepStatus.AutoSize := True;
  DepStatus.Width := DepPage.SurfaceWidth;
  DepStatus.Caption := 'Verificando…';
  DepBar := TNewProgressBar.Create(DepPage);
  DepBar.Parent := DepPage.Surface;
  DepBar.Top := DepStatus.Top + DepStatus.Height + 16;
  DepBar.Width := DepPage.SurfaceWidth;
  DepBar.Height := 18;
  DepBar.Position := 0;
end;
