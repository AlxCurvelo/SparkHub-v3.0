@echo off
title SparkHub ngrok Tunnel (Permanente)
cd /d "%~dp0"
echo ========================================================
echo     INICIANDO TUNEL NGROK PERMANENTE PARA O SPARKHUB     
echo ========================================================
echo URL Fixa: https://siesta-usage-cannabis.ngrok-free.dev
echo.

if exist "ngrok.exe" (
    ngrok.exe http --domain=siesta-usage-cannabis.ngrok-free.dev 8000
) else (
    echo [ERRO] ngrok.exe nao encontrado na pasta %~dp0.
)

pause
