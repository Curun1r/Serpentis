#!/bin/bash
# Linux source launcher. Dependencies stay inside this project's .venv.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$PATH"

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
    echo 'Serpentis requires Python 3.10 or newer. Install Python and its venv support, then retry.' >&2
    exit 127
fi
exec "$runtime" launcher.py "$@"
