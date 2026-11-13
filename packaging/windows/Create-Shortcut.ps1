$ErrorActionPreference = "Stop"
$Exe = Join-Path $PSScriptRoot "Steady.exe"
if (-not (Test-Path $Exe)) { throw "Steady.exe was not found beside this script." }
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "Steady.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Exe
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.IconLocation = "$Exe,0"
$Shortcut.Description = "Steady — offline personal planner"
$Shortcut.Save()
Write-Host "Created desktop shortcut: $ShortcutPath"
