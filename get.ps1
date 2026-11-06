# Tharwa - download and install on any Windows PC (no git needed):
#   irm https://raw.githubusercontent.com/Amjad2002-tech/gold-hunt/main/get.ps1 | iex
# Downloads the latest app code from GitHub and runs install.ps1. The code contains nobody's
# holdings: each PC starts with empty settings and keeps its own data in %USERPROFILE%\Gold Hunt Data.
$ErrorActionPreference = 'Stop'
$zipUrl = 'https://github.com/Amjad2002-tech/gold-hunt/archive/refs/heads/main.zip'
$work = Join-Path $env:TEMP ('tharwa-setup-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
New-Item -ItemType Directory -Force $work | Out-Null
try {
    Write-Host 'Downloading Tharwa...'
    $zip = Join-Path $work 'app.zip'
    Invoke-WebRequest $zipUrl -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $work -Force
    $src = Get-ChildItem $work -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'install.ps1') } | Select-Object -First 1
    if (-not $src) { throw 'install.ps1 not found in the download' }
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host 'Python is needed. Installing it with winget (you may be asked to approve)...'
        winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
    }
    & powershell -ExecutionPolicy Bypass -File (Join-Path $src.FullName 'install.ps1')
} finally {
    Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
}
