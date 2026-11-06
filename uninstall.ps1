# Tharwa uninstaller - started from Settings > Apps > Installed apps > Tharwa > Uninstall.
# Removes the app, its shortcuts and its Apps entry. Your own data in %USERPROFILE%\Gold Hunt Data is KEPT,
# so reinstalling brings everything back. Your settings are also backed up to Documents.
# The GitHub alerts are separate and keep running (turn them off on GitHub if you want).
Add-Type -AssemblyName PresentationFramework
$dest    = Join-Path $env:LOCALAPPDATA 'Programs\Gold Hunt'
$regKey  = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Tharwa'
$oldRegKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldHunt'
$answer = [System.Windows.MessageBox]::Show(
    "Remove Tharwa from this PC?`n`nYour data stays in %USERPROFILE%\Gold Hunt Data (delete that folder to erase it) and is backed up to Documents\Tharwa settings backup.ini.`nWhatsApp alerts from GitHub keep running until you turn them off there.",
    'Uninstall Tharwa', 'YesNo', 'Question')
if ($answer -ne 'Yes') { exit }

# Stop the app if it is open
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like "*$dest*" } |  # app and widget
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 500

$settings = Join-Path $env:USERPROFILE 'Gold Hunt Data\settings.ini'
if (-not (Test-Path $settings)) { $settings = Join-Path $env:APPDATA 'Gold Hunt\settings.ini' }
if (-not (Test-Path $settings)) { $settings = Join-Path $dest 'settings.ini' }  # older installs
if (Test-Path $settings) {
    Copy-Item $settings (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Tharwa settings backup.ini') -Force
}
Remove-Item (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Gold Hunt.lnk') -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Gold Hunt Widget.lnk') -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\Gold Hunt Widget.lnk') -ErrorAction SilentlyContinue
Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Gold Hunt.lnk') -ErrorAction SilentlyContinue
foreach ($n in 'Tharwa.lnk','Tharwa Widget.lnk','Startup\Tharwa Widget.lnk') { Remove-Item (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$n") -ErrorAction SilentlyContinue }
Remove-Item (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Tharwa.lnk') -ErrorAction SilentlyContinue
Remove-Item $regKey, $oldRegKey -Recurse -ErrorAction SilentlyContinue
Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue

[System.Windows.MessageBox]::Show('Tharwa was removed.', 'Uninstall Tharwa') | Out-Null
