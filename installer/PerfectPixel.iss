[Setup]
AppName=PerfectPixel
AppVersion=1.0
DefaultDirName={pf}\PerfectPixel
DefaultGroupName=PerfectPixel
OutputDir=..\dist
OutputBaseFilename=PerfectPixel-Setup
Compression=lzma
SolidCompression=yes

[Files]
; Copia todos os arquivos empacotados (inclusive _internal)
Source: "..\dist\PerfectPixel\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Copia os utilitários, mas não executa o install_service.bat
Source: "nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "install_service.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall_service.bat"; DestDir: "{app}"; Flags: ignoreversion

[Run]
; Roda o app uma vez após instalação (sem iniciar serviço)
Filename: "{app}\PerfectPixel.exe"; \
  Description: "Start PerfectPixel"; \
  Flags: nowait postinstall skipifsilent
  
[Icons]
; Atalho do app (executa o PerfectPixel.exe)
Name: "{group}\PerfectPixel"; \
  Filename: "{app}\PerfectPixel.exe"; \
  WorkingDir: "{app}"

; Atalho no desktop que executa o app
Name: "{commondesktop}\PerfectPixel"; \
  Filename: "{app}\PerfectPixel.exe"; \
  WorkingDir: "{app}"; \
  Tasks: desktopicon

; (Opcional) Atalho para abrir no navegador
Name: "{group}\Abrir no navegador"; \
  Filename: "{cmd}"; \
  Parameters: "/c start http://localhost:5000"; \
  WorkingDir: "{app}"

; Atalho para desinstalar serviço
Name: "{group}\Uninstall Service"; Filename: "{app}\uninstall_service.bat"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Opções de ícone:"
