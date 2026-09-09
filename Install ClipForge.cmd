@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python tools\setup_windows.py
) else (
  py -3 tools\setup_windows.py
)
if errorlevel 1 (
  echo Setup failed. Read the message above and README.md for help.
) else (
  echo Setup complete. Open chrome://extensions in Chrome and load the extension folder.
)
pause
