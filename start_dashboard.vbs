Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = root
WshShell.Run chr(34) & "python" & chr(34) & " " & chr(34) & root & "\sparkhub_dashboard.py" & chr(34), 0, False
Set fso = Nothing
