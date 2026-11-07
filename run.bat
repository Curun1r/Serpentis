@echo off
setlocal
:: Windows source launcher. Dependencies stay inside the project's .venv.
cd /d "%~dp0"
if errorlevel 1 exit /b 1

if exist ".venv\Scripts\python.exe" goto local_python
where py >nul 2>&1
if errorlevel 1 goto system_python
py -3.12 -c "pass" >nul 2>&1
if errorlevel 1 goto default_py
py -3.12 launcher.py %*
goto finished

:default_py
py -3 -c "import sys; raise SystemExit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto system_python
py -3 launcher.py %*
goto finished

:system_python
where python >nul 2>&1
if errorlevel 1 goto no_python
python -c "import sys; raise SystemExit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto no_python
python launcher.py %*
goto finished

:local_python
".venv\Scripts\python.exe" launcher.py %*
goto finished

:no_python
echo Serpentis requires Python 3.10 or newer. Install Python from python.org, then retry.
set "result=127"
goto report

:finished
set "result=%errorlevel%"
:report
if "%result%"=="0" exit /b 0
if defined CI exit /b %result%
if not "%~1"=="" exit /b %result%
pause
exit /b %result%
