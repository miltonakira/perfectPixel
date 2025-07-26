@echo off
>nul 2>&1 net session
if %errorlevel% neq 0 (
    echo Solicitando permissao de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

set "SERVICE_NAME=PerfectPixel"
set "NSSM_PATH=%~dp0nssm.exe"

echo Parando servico (se estiver em execucao)...
sc stop %SERVICE_NAME% >nul 2>&1

echo Removendo servico...
"%NSSM_PATH%" remove %SERVICE_NAME% confirm >nul 2>&1

echo Servico removido com sucesso.
pause