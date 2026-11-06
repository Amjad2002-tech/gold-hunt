# Builds dist\GoldHunt-Setup.zip - the app for another PC, WITHOUT any of your private data.
#   powershell -ExecutionPolicy Bypass -File build_installer.ps1
$ErrorActionPreference = 'Stop'
$src   = $PSScriptRoot
$dist  = Join-Path $src 'dist'
$stage = Join-Path $dist 'GoldHunt'
$zip   = Join-Path $dist 'GoldHunt-Setup.zip'

# Allow-list: only these files ever go in the zip (settings.ini, state files, logs, dashboards, tokens never do)
$files = 'gold_hunt.py','outlook.py','settings_page.py','app_paths.py','widget.pyw','widget_launcher.pyw',
         'settings_page.html','dashboard_template.html','i18n.js','gold_hunt.ico','requirements.txt',
         'settings.example.ini','install.ps1','uninstall.ps1','README_INSTALL.md'
$forbidden = 'settings.ini','alerts_state.json','gold_ref.json','widget_state.json','dashboard.html',
             'last_run.log','chart.png','data_dir.txt','news_cache.json'

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
foreach ($f in $files) { Copy-Item (Join-Path $src $f) $stage }
# Double-click helper for the new PC
Set-Content (Join-Path $stage 'Install Gold Hunt.bat') @'
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
'@ -Encoding ascii

# Safety checks: no private file names, and no tokens / phone keys inside the files
$bad = Get-ChildItem $stage -Recurse | Where-Object { $forbidden -contains $_.Name -or $_.Name -eq '__pycache__' }
if ($bad) { throw "Private file in package: $($bad.Name -join ', ')" }
$leak = Select-String -Path (Join-Path $stage '*') -Pattern 'EAA[A-Za-z0-9]{20,}','ghp_[A-Za-z0-9]{20,}','github_pat_' -List
if ($leak) { throw "Possible token in: $($leak.Filename -join ', ')" }

if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip
Remove-Item $stage -Recurse -Force
Write-Host "Built $zip"
