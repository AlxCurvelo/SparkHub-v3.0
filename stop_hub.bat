@echo off
title Encerrar SparkHub
cd /d "%~dp0"
echo ========================================================
echo          ENCERRANDO SPARKHUB E CLOUDFLARE TUNNEL        
echo ========================================================
echo.

taskkill /F /FI "WINDOWTITLE eq SparkHub*" >nul 2>nul
taskkill /F /IM cloudflared.exe >nul 2>nul
wmic process where "commandline like '%%app.py%%'" call terminate >nul 2>nul

echo [SUCESSO] Todos os processos do SparkHub foram encerrados.
echo.
pause
