@echo off
title SparkHub v3.0 - Iniciando...
cd /d "%~dp0"
echo =====================================================
echo     SPARKHUB v3.0 ? INICIANDO SISTEMA COMPLETO
echo =====================================================
echo.

REM ?? 1. Mata processos anteriores ??????????????????????
echo [1/5] Encerrando processos anteriores...
taskkill /F /IM pythonw.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM ngrok.exe /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq SparkHub*" /T >nul 2>&1

echo [1/5] Aguardando 4 segundos para liberar as portas de rede...
ping -n 5 127.0.0.1 >nul

REM ?? 2. API Core (app.py) ??????????????????????????????
echo [2/5] API Core (app.py)...
start "SparkHub API" /min "C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\python.exe" -u "%~dp0app.py"

REM ?? 3. Dashboard (sparkhub_dashboard.py) ?????????????
echo [3/5] Dashboard...
start "SparkHub Dashboard" /min "C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0sparkhub_dashboard.py"

REM ?? 4. Ngrok Tunnel ??????????????????????????????????
echo [4/5] Ngrok Tunnel...
start "Ngrok" /min "%~dp0ngrok.exe" http --url=siesta-usage-cannabis.ngrok-free.dev 8000

REM ?? 5. Widget de Status (Systray) ???
echo [5/5] Widget de Status (Systray)...
ping -n 3 127.0.0.1 >nul
start "SparkHub Systray" "C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\pythonw.exe" "%~dp0sparkhub_systray.py"

echo.
echo =====================================================
echo  SparkHub v3.0 ATIVO!
echo  Widget de status aparecera no canto da tela.
echo  Acesse: http://localhost:8085 ou pelo celular.
echo =====================================================
echo.
ping -n 4 127.0.0.1 >nul
