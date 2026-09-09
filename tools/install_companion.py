"""Install a deterministic native launcher outside macOS protected document folders."""
import json
import os
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def install():
    support = Path.home() / 'Library/Application Support/ClipForge'
    support.mkdir(parents=True, exist_ok=True)
    python = ROOT / '.venv/bin/python'
    if not python.exists():
        raise SystemExit('Run Install ClipForge.command to install the Python environment first.')
    launcher = support / 'launch-engine'
    log = support / 'native-host.log'
    launcher.write_text('#!/bin/sh\n' +
        'exec ' + shlex.quote(str(python)) + ' -u ' + shlex.quote(str(ROOT/'native_host.py')) +
        ' "$@" 2>>' + shlex.quote(str(log)) + '\n')
    launcher.chmod(0o755)
    manifest = json.loads((ROOT/'native-host/com.clipforge.engine.json').read_text())
    manifest['path'] = str(launcher)
    hosts = Path.home() / 'Library/Application Support/Google/Chrome/NativeMessagingHosts'
    hosts.mkdir(parents=True, exist_ok=True)
    (hosts/'com.clipforge.engine.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Installed deterministic Chrome launcher. Diagnostic log: '+str(log))

if __name__ == '__main__':
    install()
