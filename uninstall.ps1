# Gold Hunt uninstaller - started from Settings > Apps > Installed apps > Gold Hunt > Uninstall.
# Removes the app, its shortcuts and its Apps entry. Your settings are backed up to Documents first.
# The GitHub alerts are separate and keep running (turn them off on GitHub if you want).
Add-Type -AssemblyName PresentationFramework
$dest    = Join-Path $env:LOCALAPPDATA 'Programs\Gold Hunt'
$regKey  = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldHunt'
$answer = [System.Windows.MessageBox]::Show(
    "Remove Gold Hunt from this PC?`n`nYour settings will be saved to Documents\Gold Hunt settings backup.ini.`nWhatsApp alerts from GitHub keep running until you turn them off there.",
    'Uninstall Gold Hunt', 'YesNo', 'Question')
if ($answer -ne 'Yes') { exit }

# Stop the app if it is open
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like "*$dest*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 500

$settings = Join-Path $dest 'settings.ini'
if (Test-Path $settings) {
    Copy-Item $settings (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Gold Hunt settings backup.ini') -Force
}
Remove-Item (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Gold Hunt.lnk') -ErrorAction SilentlyContinue
Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Gold Hunt.lnk') -ErrorAction SilentlyContinue
Remove-Item $regKey -Recurse -ErrorAction SilentlyContinue
Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue

[System.Windows.MessageBox]::Show('Gold Hunt was removed.', 'Uninstall Gold Hunt') | Out-Null
