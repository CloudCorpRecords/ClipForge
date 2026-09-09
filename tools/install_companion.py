"""Install a deterministic native launcher outside macOS protected document folders."""
import json
import os
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def install():
    if sys.platform == 'win32':
        return install_windows()
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

def install_windows():
    import winreg
    launcher = ROOT / '.venv/Scripts/clipforge-native.exe'
    if not launcher.is_file():
        raise SystemExit('Run Install ClipForge.cmd first to install the native launcher.')
    support = Path(os.environ['LOCALAPPDATA']) / 'ClipForge'
    support.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT/'native-host/com.clipforge.engine.json').read_text())
    manifest['path'] = str(launcher)
    target = support / 'com.clipforge.engine.json'
    target.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
            r'Software\Google\Chrome\NativeMessagingHosts\com.clipforge.engine',
            0, winreg.KEY_WRITE | winreg.KEY_WOW64_32KEY) as key:
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, str(target))
    print('Chrome automatic engine installed for this Windows user.')

if __name__ == '__main__':
    install()
