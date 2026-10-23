# Gold Hunt installer (this user only - no admin needed).
# Run again any time to update the installed app; your settings.ini is kept.
#   powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = 'Stop'
$src     = $PSScriptRoot
$dest    = Join-Path $env:LOCALAPPDATA 'Programs\Gold Hunt'
$start   = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Gold Hunt.lnk'
$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Gold Hunt.lnk'
$regKey  = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldHunt'
$pythonw = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\pythonw.exe'
$python  = (Get-Command python -ErrorAction SilentlyContinue).Source

Write-Host "Installing Gold Hunt to $dest"
if (-not $python) { throw "Python is not installed. Install Python 3.11+ from the Microsoft Store, then run this again." }
if (-not (Test-Path $pythonw)) { $pythonw = Join-Path (Split-Path $python) 'pythonw.exe' }

# 1. Libraries the app needs
& $python -m pip install --quiet --disable-pip-version-check -r (Join-Path $src 'requirements.txt')

# 2. App files (settings.ini only on first install, so your numbers are never overwritten)
New-Item -ItemType Directory -Force $dest | Out-Null
$files = 'gold_hunt.py','settings_page.py','widget.pyw','settings_page.html','dashboard_template.html','i18n.js',
         'gold_hunt.ico','requirements.txt','uninstall.ps1'
foreach ($f in $files) { Copy-Item (Join-Path $src $f) $dest -Force }
if (-not (Test-Path (Join-Path $dest 'settings.ini'))) {
    $settings = Join-Path $src 'settings.ini'
    if (-not (Test-Path $settings)) { $settings = Join-Path $src 'settings.example.ini' }
    Copy-Item $settings (Join-Path $dest 'settings.ini')
}

# 3. Start menu + Desktop shortcuts
$ws = New-Object -ComObject WScript.Shell
foreach ($path in $start, $desktop) {
    $lnk = $ws.CreateShortcut($path)
    $lnk.TargetPath       = $pythonw
    $lnk.Arguments        = "`"$dest\settings_page.py`""
    $lnk.WorkingDirectory = $dest
    $lnk.IconLocation     = "$dest\gold_hunt.ico,0"
    $lnk.Description      = 'Gold Hunt - gold and stock prices, dashboard and alerts'
    $lnk.Save()
}

# 3b. Desktop widget: Start menu entry + start automatically when Windows starts
$widgetStart = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Gold Hunt Widget.lnk'
$widgetBoot  = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\Gold Hunt Widget.lnk'
foreach ($path in $widgetStart, $widgetBoot) {
    $lnk = $ws.CreateShortcut($path)
    $lnk.TargetPath       = $pythonw
    $lnk.Arguments        = "`"$dest\widget.pyw`""
    $lnk.WorkingDirectory = $dest
    $lnk.IconLocation     = "$dest\gold_hunt.ico,0"
    $lnk.Description      = 'Gold Hunt desktop widget - live prices and profit/loss'
    $lnk.Save()
}
# Restart the widget so it runs the newly installed version
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like '*widget.pyw*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath $pythonw -ArgumentList "`"$dest\widget.pyw`"" -WorkingDirectory $dest

# 4. Entry in Settings > Apps > Installed apps (with Uninstall button)
$size = [int]((Get-ChildItem $dest -Recurse | Measure-Object Length -Sum).Sum / 1KB)
New-Item -Path $regKey -Force | Out-Null
$values = @{
    DisplayName     = 'Gold Hunt'
    DisplayVersion  = '1.0'
    Publisher       = 'Amjad2002-tech'
    DisplayIcon     = "$dest\gold_hunt.ico"
    InstallLocation = $dest
    InstallDate     = (Get-Date -Format 'yyyyMMdd')
    UninstallString = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$dest\uninstall.ps1`""
    URLInfoAbout    = 'https://github.com/Amjad2002-tech/gold-hunt'
}
foreach ($k in $values.Keys) { Set-ItemProperty -Path $regKey -Name $k -Value $values[$k] }
Set-ItemProperty -Path $regKey -Name EstimatedSize -Value $size -Type DWord
Set-ItemProperty -Path $regKey -Name NoModify -Value 1 -Type DWord
Set-ItemProperty -Path $regKey -Name NoRepair -Value 1 -Type DWord

Write-Host "Done. Open 'Gold Hunt' from the Start menu or Desktop."
