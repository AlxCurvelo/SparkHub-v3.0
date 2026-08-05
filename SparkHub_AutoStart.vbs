Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run chr(34) & root & "\start_hub.bat" & chr(34), 0
WshShell.Run chr(34) & root & "\start_tunnel.bat" & chr(34), 0
Set fso = Nothing
Set WshShell = Nothing
