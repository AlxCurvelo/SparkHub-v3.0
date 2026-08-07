@echo off
title SparkHub v3.0 - Auto-Healing Backend...
cd /d "%~dp0"

echo [Auto-Healing] Encerrando processos de backend...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM ngrok.exe /T >nul 2>&1

ping -n 3 127.0.0.1 >nul

echo [Auto-Healing] Iniciando API e Dashboard...
start "SparkHub API" /min "C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\python.exe" -u "%~dp0app.py"
start "SparkHub Dashboard" /min "C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0sparkhub_dashboard.py"
start "Ngrok" /min "%~dp0ngrok.exe" http --url=siesta-usage-cannabis.ngrok-free.dev 8000

ping -n 5 127.0.0.1 >nul
exit
