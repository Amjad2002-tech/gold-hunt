@echo off
rem Checks prices every 30 minutes in the background and sends WhatsApp alerts
schtasks /Create /F /SC MINUTE /MO 30 /TN "Gold Hunt" /TR "cmd /c cd /d \"%~dp0.\" && python gold_hunt.py"
echo Done. To stop it later: schtasks /Delete /TN "Gold Hunt" /F
pause
