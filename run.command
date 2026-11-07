#!/bin/bash
# macOS source launcher. Double-click or pass --setup / --check in Terminal.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"

if [ -x .venv/bin/python ]; then
    runtime=.venv/bin/python
else
    runtime=
    for candidate in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
           "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
            runtime=$candidate
            break
        fi
    done
fi
if [ -z "$runtime" ]; then
    echo 'Serpentis requires Python 3.10 or newer. Install Python, then retry.' >&2
    status=127
else
    "$runtime" launcher.py "$@"
    status=$?
fi
if [ "$status" -ne 0 ] && [ -t 0 ] && [ "$#" -eq 0 ]; then
    read -r -p 'Press Enter to close...' _reply
fi
exit "$status"
