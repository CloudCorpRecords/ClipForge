"""Run with a standard Windows Python installation; no administrator needed."""
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]

def main():
    if sys.platform != 'win32':
        raise SystemExit('Use Install ClipForge.command on macOS.')
    if not (3, 11) <= sys.version_info[:2] <= (3, 13):
        raise SystemExit('Install 64-bit Python 3.11, 3.12 or 3.13 from python.org. Enable Add python.exe to PATH.')
    os.chdir(ROOT)
    python = ROOT / '.venv/Scripts/python.exe'
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(ROOT / '.venv')
    for args in [
        ['-m', 'pip', 'install', '--upgrade', 'pip'],
        ['-m', 'pip', 'install', '-r', 'requirements.txt'],
        ['-m', 'pip', 'install', '--no-deps', '-e', '.'],
        ['tools/install_companion.py'],
    ]:
        subprocess.run([str(python), *args], check=True)

if __name__ == '__main__':
    main()
