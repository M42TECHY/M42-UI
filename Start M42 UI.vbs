' Starts M42 UI with no console window (pythonw). Messages go to m42\logs\app.log.
' To see the console for troubleshooting, use "Start M42 (debug).bat" instead.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir
On Error Resume Next
py = "pythonw"  ' (the installer's own Python first: install.bat makes .venv)
If fso.FileExists(dir & "\.venv\Scripts\pythonw.exe") Then py = """" & dir & "\.venv\Scripts\pythonw.exe"""
sh.Run py & " """ & dir & "\m42\app.py""", 0, False
If Err.Number <> 0 Then
  MsgBox "Could not start M42 UI: pythonw was not found." & vbCrLf & vbCrLf & _
         "Run install.bat first (it sets up Python and the AI model).", vbCritical, "M42 UI"
End If
