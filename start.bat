@echo off
setlocal enabledelayedexpansion

echo ===============================
echo      Iniciando PerfectPixel...
echo ===============================

REM Verifica se o ambiente virtual já existe
if exist "venv\" (
    echo Ambiente virtual encontrado.
) else (
    echo Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo Erro ao criar o ambiente virtual.
        pause
        exit /b 1
    )
)

REM Ativa o ambiente virtual
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Erro ao ativar o ambiente virtual.
    pause
    exit /b 1
)

REM Atualiza pip
echo Atualizando pip...
python -m pip install --upgrade pip

REM Instala as dependências
echo Instalando dependências...
pip install Flask requests beautifulsoup4 chardet

REM Inicia o app
echo.
echo Iniciando o servidor...
python -m perfectpixel

echo.
echo ===============================
echo        Encerrado
echo ===============================
pause
