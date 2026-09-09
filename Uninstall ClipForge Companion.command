#!/bin/bash
set -e

HOST="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.clipforge.engine.json"
if [ -f "$HOST" ]; then
  mv "$HOST" "$HOME/.Trash/com.clipforge.engine.json"
fi
echo "The ClipForge automatic-start registration was moved to Trash. Your projects and extension files were kept."
