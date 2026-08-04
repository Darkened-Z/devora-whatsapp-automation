; ============================================================
;  WhatsApp Auto Replier — Inno Setup installer script
;  Build with:  ISCC.exe installer.iss
;  Output:      installer-output\WhatsAppAutoReplier-Setup.exe
; ============================================================

#define AppName "WhatsApp Auto Replier"
#define AppVer "1.0.0"
#define AppPublisher "Daiki Media"   ; <- change to your business name

[Setup]
; A unique ID for this app (keep it the same across versions so updates work).
AppId={{8F4A1C2E-7B3D-4E5F-9A6B-1C2D3E4F5A6B}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher={#AppPublisher}
; Install per-user so no admin/UAC prompt is needed AND the app can write its
; own config.json + .session (Program Files would be read-only for the client).
DefaultDirName={localappdata}\Programs\WhatsApp Auto Replier
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer-output
OutputBaseFilename=WhatsAppAutoReplier-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\node.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "autostart"; Description: "Start automatically when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "server.js";                DestDir: "{app}"; Flags: ignoreversion
Source: "node.exe";                 DestDir: "{app}"; Flags: ignoreversion
Source: "package.json";             DestDir: "{app}"; Flags: ignoreversion
Source: "start.bat";                DestDir: "{app}"; Flags: ignoreversion
Source: "install-autostart.bat";    DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall-autostart.bat";  DestDir: "{app}"; Flags: ignoreversion
Source: "README.txt";               DestDir: "{app}"; Flags: ignoreversion isreadme
; Never overwrite the client's saved settings on re-install / update:
Source: "config.json";              DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "public\*";                 DestDir: "{app}\public";       Flags: recursesubdirs createallsubdirs ignoreversion
Source: "node_modules\*";           DestDir: "{app}\node_modules"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\WhatsApp Auto Replier";            Filename: "{app}\start.bat"; WorkingDir: "{app}"; IconFilename: "{app}\node.exe"
Name: "{group}\Uninstall WhatsApp Auto Replier";  Filename: "{uninstallexe}"
Name: "{userdesktop}\WhatsApp Auto Replier";      Filename: "{app}\start.bat"; WorkingDir: "{app}"; IconFilename: "{app}\node.exe"; Tasks: desktopicon
Name: "{userstartup}\WhatsApp Auto Replier";      Filename: "{app}\start.bat"; WorkingDir: "{app}"; IconFilename: "{app}\node.exe"; Tasks: autostart

[Run]
Filename: "{app}\start.bat"; Description: "Launch WhatsApp Auto Replier now"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}\.session"
Type: filesandordirs; Name: "{app}\.wwebjs_cache"
Type: filesandordirs; Name: "{app}\.wwebjs_auth"

[Code]
function InitializeSetup(): Boolean;
var
  hasChrome, hasEdge: Boolean;
begin
  hasChrome := FileExists(ExpandConstant('{localappdata}\Google\Chrome\Application\chrome.exe'))
    or FileExists('C:\Program Files\Google\Chrome\Application\chrome.exe')
    or FileExists('C:\Program Files (x86)\Google\Chrome\Application\chrome.exe');
  hasEdge := FileExists('C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    or FileExists('C:\Program Files\Microsoft\Edge\Application\msedge.exe');
  if (not hasChrome) and (not hasEdge) then
  begin
    MsgBox('Google Chrome was not found on this PC.' + #13#10 +
           'The Auto Replier needs Chrome (or Microsoft Edge) to run.' + #13#10#13#10 +
           'Please install Chrome from https://www.google.com/chrome, then run this installer again.',
           mbError, MB_OK);
    Result := False;
  end
  else
    Result := True;
end;
