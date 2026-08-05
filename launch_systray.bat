@echo off
REM ============================================================
REM  SparkHub Systray Launcher
REM  Garante que o ícone aparece na bandeja do Windows
REM ============================================================

SET SCRIPT_DIR=%~dp0
SET PYTHON_EXE=pythonw.exe

echo [LAUNCHER] Verificando processos anteriores do systray...
taskkill /F /FI "WINDOWTITLE eq SparkHubSystray" /T >nul 2>&1

REM Mata qualquer pythonw que possa estar travado
for /f "tokens=2" %%i in ('tasklist /fi "IMAGENAME eq pythonw.exe" /fo csv /nh 2^>nul') do (
    taskkill /F /PID %%~i >nul 2>&1
)

echo [LAUNCHER] Aguardando 1 segundo...
timeout /t 1 /nobreak >nul

echo [LAUNCHER] Iniciando SparkHub Systray...
cd /d "%SCRIPT_DIR%"

REM Usa pythonw.exe para rodar SEM janela de console
start "SparkHubSystray" %PYTHON_EXE% sparkhub_systray.py

echo [LAUNCHER] Systray iniciado! Verifique a bandeja do Windows.
echo [LAUNCHER] Se o icone estiver oculto, clique na seta "^" da bandeja.
timeout /t 3 /nobreak >nul
exit /b 0
