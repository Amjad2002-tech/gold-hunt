@echo off
cd /d "%~dp0"
python gold_hunt.py
start "" dashboard.html
