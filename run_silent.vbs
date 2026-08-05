Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.Run "cmd /c " & chr(34) & root & "\iniciar_sparkhub.bat" & chr(34), 0, False
Set fso = Nothing
Set WshShell = Nothing
