#!/bin/bash
# Linux launcher — run from terminal or file manager.

cd "$(dirname "$0")"

export PATH="$HOME/.local/bin:$PATH"

if command -v pipenv &>/dev/null; then
    pipenv run python main.py
elif command -v python3 &>/dev/null; then
    echo "pipenv not found — running with system python3"
    python3 -m pip install pygame --quiet --break-system-packages 2>/dev/null || \
    python3 -m pip install pygame --quiet
    python3 main.py
else
    echo "ERROR: Python 3 not found. Install it via your package manager."
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Fedora:        sudo dnf install python3 python3-pip"
fi
