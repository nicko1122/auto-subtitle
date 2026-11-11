@echo off
title AutoSubtitle Web Studio
cd /d "%~dp0"
echo ===================================================
echo   Starting AutoSubtitle Web Studio (port 8000)...
echo   URL: http://localhost:8000
echo ===================================================
wsl bash -c "cd /mnt/d/projects/auto-subtitle && .venv/bin/python src/cli/main.py serve --host 0.0.0.0 --port 8000"
pause
