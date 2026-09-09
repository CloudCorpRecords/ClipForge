#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  CLIPFORGE_PYTHON=""
  for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
      CLIPFORGE_PYTHON="$candidate"
      break
    fi
  done
  if [ -z "$CLIPFORGE_PYTHON" ]; then
    echo 'Install Python 3.11 or newer from python.org, then run this installer again.'
    exit 1
  fi
  "$CLIPFORGE_PYTHON" -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi

.venv/bin/python tools/install_companion.py

echo "ClipForge's automatic engine is installed."
echo "Load or reload the extension at chrome://extensions, then click ClipForge from any video page."
open -a "Google Chrome" "chrome://extensions"
