Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run """C:\Users\ac_cu\AppData\Local\Programs\Python\Python312\pythonw.exe"" """ & root & "\sparkhub_systray.py""", 0, False
Set fso = Nothing
Set WshShell = Nothing
