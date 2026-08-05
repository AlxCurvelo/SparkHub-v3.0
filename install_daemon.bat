@echo off
echo ========================================================
echo   SPARKHUB v3.0 - INSTALADOR DO DAEMON MASTER (BOOT)
echo ========================================================
echo.
echo Registrando o Maestro (sparkhub_master_live.py) no Agendador de Tarefas do Windows...
schtasks /create /tn "SparkHubMasterDaemon" /tr "pythonw "%~dp0sparkhub_master_live.py"" /sc onstart /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCESSO] Daemon registrado! Ele iniciara silenciosamente no proximo boot.
    echo Para iniciar agora manualmente, digite: schtasks /run /tn "SparkHubMasterDaemon"
) else (
    echo.
    echo [ERRO] Falha ao registrar o Daemon. Certifique-se de executar como Administrador.
)
pause
