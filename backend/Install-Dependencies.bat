@echo off
setlocal EnableDelayedExpansion

title Setup do Projeto
color 0B
chcp 65001 >nul

:banner
cls

echo.
echo ============================================================
echo                 🚀 Stardew Parable - Instalador
echo ============================================================
echo.

echo [1/3] Verificando Python...

python --version >nul 2>&1

if %errorlevel% neq 0 (

    color 0E

    echo.
    echo ⚠ Python nao encontrado!
    echo.
    echo Tentando instalar automaticamente...
    echo.

    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements

    echo.
    echo ============================================================
    echo  A instalacao terminou.
    echo  Feche esta janela e execute novamente o Setup.
    echo ============================================================
    echo.

    pause
    exit /b
)

color 0A

echo ✔ Python encontrado:
python --version

echo.
echo ============================================================
echo [2/3] Instalando dependencias...
echo ============================================================
echo.

set "TEMPFLAG=%TEMP%\stardewparable_install.tmp"

echo running > "%TEMPFLAG%"

start "" /B cmd /c ^
"python -m pip install -q -r requirements.txt >nul 2>&1 && del "%TEMPFLAG%""

setlocal EnableDelayedExpansion

set BAR=
set COUNT=0

:loading

if not exist "%TEMPFLAG%" goto finished

set /a COUNT+=1

if !COUNT! gtr 20 (
    set COUNT=1
    set BAR=
)

set BAR=!BAR!█

cls

echo.
echo ============================================================
echo                 🚀 Stardew Parable - Instalador
echo ============================================================
echo.
echo [2/3] Instalando dependencias...
echo.
echo Aguarde enquanto instalamos tudo...
echo.
echo [!BAR!]
echo.

timeout /t 1 >nul

goto loading

:finished

endlocal

echo.
echo ✔ Dependencias instaladas com sucesso!

echo.
echo ============================================================
echo [3/3] Deseja iniciar o backend agora?
echo ============================================================
echo.

choice /C SN /N /M "[S] Sim   [N] Nao : "

if errorlevel 2 goto end
if errorlevel 1 goto backend

:backend

echo.
echo Iniciando backend...
echo.

call RunBackend.bat

goto end

:end

color 0B

echo.
echo ============================================================
echo               Setup finalizado com sucesso
echo ============================================================
echo.

pause