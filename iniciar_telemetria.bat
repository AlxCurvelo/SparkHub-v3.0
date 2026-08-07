@echo off
title SparkHub - Telemetry Agent
echo ===================================================
echo   SparkHub v3.0 - Agente de Telemetria Continua
echo ===================================================
:loop
echo [%time%] Iniciando varredura proativa (Nivel 3)...
python mempalace_autocollect_master.py
echo.
echo [%time%] Varredura concluida. Aguardando 10 minutos para o proximo ciclo...
timeout /t 600 /nobreak
goto loop
