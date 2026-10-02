@echo off
cd /d "%~dp0.."
".venv\Scripts\python.exe" -m iaula check --notify >> data\check.log 2>&1
