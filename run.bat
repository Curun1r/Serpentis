@echo off
:: Windows launcher — double-click to run Serpentis.
cd /d "%~dp0"
echo Starting Serpentis...

where pipenv >nul 2>&1
if %errorlevel% == 0 (
    pipenv run python main.py
) else (
    where python >nul 2>&1
    if %errorlevel% == 0 (
        echo pipenv not found -- running with system Python
        python -m pip install pygame --quiet
        python main.py
    ) else (
        echo.
        echo ERROR: Python not found.
        echo Install it from https://www.python.org
        echo Make sure to check "Add Python to PATH" during install.
        pause
    )
)
