"""Exercise the installed launcher shape with Chrome's minimal environment."""
import json
import os
import struct
import subprocess
from pathlib import Path
from tools import install_companion


def test_launcher_does_not_depend_on_shell_python(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    install_companion.install()
    manifest = json.loads((tmp_path/'Library/Application Support/Google/Chrome/NativeMessagingHosts/com.clipforge.engine.json').read_text())
    launcher = Path(manifest['path'])
    assert launcher.is_file()
    assert os.access(launcher, os.X_OK)
    # Unknown action does not start an engine or access the network, but proves
    # the interpreter, spaced paths, framing, and response work together.
    payload = json.dumps({'action':'test-unsupported'}).encode()
    process = subprocess.run([str(launcher)], input=struct.pack('=I',len(payload))+payload,
                             env={'PATH':'/usr/bin:/bin','HOME':str(tmp_path)},
                             capture_output=True, timeout=10)
    assert process.returncode == 0, process.stderr.decode()
    length = struct.unpack('=I',process.stdout[:4])[0]
    result = json.loads(process.stdout[4:4+length])
    assert result == {'ok':False,'error':'Unknown ClipForge action.'}
    assert manifest['allowed_origins'] == ['chrome-extension://hllhhgmemaeimjjecboegbfgbkbehokk/']
