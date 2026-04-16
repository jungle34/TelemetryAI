@echo off
setlocal

echo ======================================
echo   Instalador do Projeto Python Alpha
echo ======================================

:: Verifica se o Python existe
python --version >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo Python encontrado.
    goto INSTALL_DEPS
)

echo Python nao encontrado. Instalando...

:: Baixa o instalador oficial do Python
set PYTHON_INSTALLER=python-installer.exe

curl -L -o %PYTHON_INSTALLER% https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe

if not exist %PYTHON_INSTALLER% (
    echo Erro ao baixar o instalador do Python.
    pause
    exit /b 1
)

echo Instalando Python silenciosamente...

start /wait %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

del %PYTHON_INSTALLER%

echo Python instalado com sucesso!

:INSTALL_DEPS

echo.
echo Atualizando pip...
python -m pip install --upgrade pip

if %ERRORLEVEL% NEQ 0 (
    echo Erro ao atualizar pip.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias do requirements.txt...

if not exist requirements.txt (
    echo requirements.txt nao encontrado!
    pause
    exit /b 1
)

python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Erro ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo ======================================
echo   Instalacao concluida com sucesso!
echo ======================================

pause
endlocal