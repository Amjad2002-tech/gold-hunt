# Tharwa installer (formerly Gold Hunt) (this user only - no admin needed).
# Run again any time to update the installed app; your data in %USERPROFILE%\Gold Hunt Data is kept.
#   powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = 'Stop'
$src     = $PSScriptRoot
$dest    = Join-Path $env:LOCALAPPDATA 'Programs\Gold Hunt'
$start   = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Tharwa.lnk'
$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Tharwa.lnk'
$regKey  = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Tharwa'
$oldRegKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GoldHunt'
$pythonw = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\pythonw.exe'
$python  = (Get-Command python -ErrorAction SilentlyContinue).Source

Write-Host "Installing Tharwa to $dest"
if (-not $python) { throw "Python is not installed. Install Python 3.11+ from the Microsoft Store, then run this again." }
if (-not (Test-Path $pythonw)) { $pythonw = Join-Path (Split-Path $python) 'pythonw.exe' }

# 1. Libraries the app needs (+ the Chromium browser Playwright uses to read the gold price)
& $python -m pip install --quiet --disable-pip-version-check -r (Join-Path $src 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw "Installing Python libraries failed (check your internet connection)." }
& $python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { Write-Warning "Playwright Chromium did not install - gold price will fall back to world price." }

# 2. App files. Your own data lives separately in %USERPROFILE%\Gold Hunt Data, so updates never touch it.
$data = Join-Path $env:USERPROFILE 'Gold Hunt Data'
New-Item -ItemType Directory -Force $dest, $data | Out-Null
$files = 'gold_hunt.py','outlook.py','settings_page.py','app_paths.py','widget.pyw','widget_launcher.pyw','settings_page.html',
         'dashboard_template.html','i18n.js','gold_hunt.ico','requirements.txt','settings.example.ini','uninstall.ps1'
foreach ($f in $files) { Copy-Item (Join-Path $src $f) $dest -Force }
Set-Content (Join-Path $dest 'data_dir.txt') '%USERPROFILE%\Gold Hunt Data' -Encoding ascii
# Older installs kept data next to the app: move it to the data folder once
foreach ($f in 'settings.ini','alerts_state.json','gold_ref.json','widget_state.json') {
    $old = Join-Path $dest $f
    if ((Test-Path $old) -and -not (Test-Path (Join-Path $data $f))) { Move-Item $old $data }
}
# A brand-new user starts from the example file - never from anyone else's settings
if (-not (Test-Path (Join-Path $data 'settings.ini'))) {
    Copy-Item (Join-Path $src 'settings.example.ini') (Join-Path $data 'settings.ini')
    Write-Host "Created a fresh settings file - open Tharwa and enter your own holdings."
}

# 3. Start menu + Desktop shortcuts (remove the old "Gold Hunt" ones from before the rename)
foreach ($old in (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Gold Hunt.lnk'),
                 (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Gold Hunt Widget.lnk'),
                 (Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\Gold Hunt Widget.lnk'),
                 (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Gold Hunt.lnk')) {
    Remove-Item $old -ErrorAction SilentlyContinue
}
if (Test-Path $oldRegKey) { Remove-Item $oldRegKey -Recurse -ErrorAction SilentlyContinue }
$ws = New-Object -ComObject WScript.Shell
foreach ($path in $start, $desktop) {
    $lnk = $ws.CreateShortcut($path)
    $lnk.TargetPath       = $pythonw
    $lnk.Arguments        = "`"$dest\settings_page.py`""
    $lnk.WorkingDirectory = $dest
    $lnk.IconLocation     = "$dest\gold_hunt.ico,0"
    $lnk.Description      = 'Tharwa - gold and stock prices, dashboard and alerts'
    $lnk.Save()
}

# 3b. Desktop widget: Start menu entry + start automatically when Windows starts
$widgetStart = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Tharwa Widget.lnk'
$widgetBoot  = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Startup\Tharwa Widget.lnk'
foreach ($path in $widgetStart, $widgetBoot) {
    $lnk = $ws.CreateShortcut($path)
    $lnk.TargetPath       = $pythonw
    $lnk.Arguments        = "`"$dest\widget_launcher.pyw`""
    $lnk.WorkingDirectory = $dest
    $lnk.IconLocation     = "$dest\gold_hunt.ico,0"
    $lnk.Description      = 'Tharwa desktop widget - live prices and profit/loss'
    $lnk.Save()
}
# Restart the widget so it runs the newly installed version
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like '*widget*.pyw*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Process -FilePath $pythonw -ArgumentList "`"$dest\widget_launcher.pyw`"" -WorkingDirectory $dest

# 4. Entry in Settings > Apps > Installed apps (with Uninstall button)
$size = [int]((Get-ChildItem $dest -Recurse | Measure-Object Length -Sum).Sum / 1KB)
New-Item -Path $regKey -Force | Out-Null
$values = @{
    DisplayName     = 'Tharwa'
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

Write-Host "Done. Open 'Tharwa' from the Start menu or Desktop. Your data: $data"
