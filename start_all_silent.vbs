Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)

WshShell.Run "taskkill /F /IM python.exe /T", 0, True
WshShell.Run "taskkill /F /IM pythonw.exe /T", 0, True
WshShell.Run "taskkill /F /IM ngrok.exe /T", 0, True

WScript.Sleep 1000

python_exe = "C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\python.exe"
pythonw_exe = "C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\pythonw.exe"

WshShell.Run """" & python_exe & """ -u """ & root & "\app.py""", 0, False
WshShell.Run """" & python_exe & """ """ & root & "\sparkhub_dashboard.py""", 0, False
WshShell.Run """" & root & "\ngrok.exe"" http --url=siesta-usage-cannabis.ngrok-free.dev 8000", 0, False
WshShell.Run """" & pythonw_exe & """ """ & root & "\sparkhub_systray.py""", 0, False
