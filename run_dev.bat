@echo off
cd /d "%~dp0"
if "%DJANGO_DEV_PORT%"=="" set DJANGO_DEV_PORT=8777
echo Starting Django on http://127.0.0.1:%DJANGO_DEV_PORT%/ (set DJANGO_DEV_PORT to change)
venv\Scripts\python.exe manage.py runserver 127.0.0.1:%DJANGO_DEV_PORT%
