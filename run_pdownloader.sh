#!/usr/bin/env bash
# P-Downloader launcher for Linux and macOS
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON_BIN="venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "[ERROR] Python 3 was not found on your system."
    echo "Please install Python 3.10+ (e.g. 'sudo apt install python3 python3-pip' or 'brew install python')."
    exit 1
fi

exec "$PYTHON_BIN" main.py "$@"
