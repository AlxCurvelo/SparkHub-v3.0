' SparkHub Systray Launcher
' Executa o systray.py diretamente na sessão do usuário, sem janela de console
' Salve este arquivo e execute com duplo clique

Dim oShell
Set oShell = CreateObject("WScript.Shell")

' Mata processos anteriores
oShell.Run "cmd /c taskkill /F /IM pythonw.exe /T 2>nul", 0, True
WScript.Sleep 500

' Inicia o systray sem janela
oShell.Run "pythonw.exe D:\SparkHub\sparkhub_systray.py", 0, False

WScript.Sleep 2000
MsgBox "SparkHub Systray iniciado!" & Chr(13) & Chr(13) & _
       "Procure o icone circular na bandeja do sistema." & Chr(13) & _
       "Se nao aparecer na barra, clique na seta ^ para ver icones ocultos.", _
       64, "SparkHub v3.0"
