@echo off
title SparkHub - Iniciando Systray...
echo ============================================
echo  SparkHub v3.0 - Iniciando Icone de Status
echo ============================================
echo.

cd /d D:\SparkHub

echo Matando processos anteriores...
taskkill /F /IM pythonw.exe /T >nul 2>&1
timeout /t 1 /nobreak >nul

echo Iniciando SparkHub Systray...
echo (Uma janela pequena aparecera no canto SUPERIOR DIREITO da tela)
echo.

start "" pythonw.exe D:\SparkHub\sparkhub_systray.py

timeout /t 4 /nobreak >nul

echo Verificando log...
type D:\SparkHub\systray.log

echo.
echo ============================================
echo Se nao apareceu uma janela, verifique o log
echo acima para mais detalhes.
echo ============================================
echo.
pause
