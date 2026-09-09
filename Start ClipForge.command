#!/bin/bash
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
if curl -fsS http://127.0.0.1:43177/api/health >/dev/null 2>&1; then
  echo 'ClipForge is already running. Open it from the Chrome toolbar.'
  exit 0
fi
echo 'Manual recovery mode: ClipForge is starting. Normally the Chrome extension does this automatically.'
exec .venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 43177
