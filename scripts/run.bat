@echo off
cd /d "%~dp0.."
.venv\Scripts\python.exe scripts\seed.py
echo EXIT:%ERRORLEVEL%
