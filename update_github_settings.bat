@echo off
rem Sends your settings.ini (grams, prices, stocks, alert levels) to GitHub
cd /d "%~dp0"
echo Uploading settings.ini to GitHub...
"C:\Program Files\GitHub CLI\gh.exe" secret set GOLD_HUNT_SETTINGS -R Amjad2002-tech/gold-hunt < settings.ini
if errorlevel 1 (
  echo.
  echo FAILED - nothing was changed on GitHub.
) else (
  echo.
  echo Done! GitHub will use your new settings from the next check.
)
pause
