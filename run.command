#!/bin/bash
# macOS launcher — double-click to run Serpentis.
# Works whether pipenv is installed or not.

cd "$(dirname "$0")"

# macOS Terminal opens with a minimal PATH; add all common install locations
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

echo "Starting Serpentis..."

if command -v pipenv &>/dev/null; then
    pipenv run python main.py
elif command -v python3 &>/dev/null; then
    echo "pipenv not found — running with system python3"
    python3 -m pip install -r requirements.txt --quiet
    python3 main.py
else
    echo ""
    echo "ERROR: Python 3 not found."
    echo "Install it from https://www.python.org or via Homebrew: brew install python"
    read -p "Press Enter to close..."
fi
