#!/usr/bin/env python3
"""Chrome Native Messaging bridge that starts ClipForge's private local engine."""
import json
import os
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
LOG = ROOT / "data" / "engine.log"
HOST = "127.0.0.1"
PORT = 43177
ENGINE_PROCESS = None


def engine_ready():
    try:
        request = urllib.request.Request(
            f"http://{HOST}:{PORT}/api/health",
            headers={"X-ClipForge": "1"},
        )
        with urllib.request.urlopen(request, timeout=0.4) as response:
            payload = json.loads(response.read(4096).decode("utf-8"))
            return response.status == 200 and payload.get("ok") is True
    except Exception:
        return False


def start_engine():
    global ENGINE_PROCESS
    if engine_ready():
        return {"ok": True, "alreadyRunning": True}
    if not PYTHON.is_file():
        raise RuntimeError("ClipForge is missing its Python environment. Run Install ClipForge again.")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    if os.name != 'nt':
        env["PATH"] = "/opt/homebrew/opt/node@22/bin:/opt/homebrew/bin:/usr/local/bin:" + env.get("PATH", "")
    with LOG.open("ab", buffering=0) as output:
        ENGINE_PROCESS = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "server.app:app", "--host", HOST, "--port", str(PORT)],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            **({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}),
        )
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if engine_ready():
            return {"ok": True, "alreadyRunning": False}
        time.sleep(0.2)
    raise RuntimeError("The editing engine did not become ready. See data/engine.log.")


def read_message():
    raw = sys.stdin.buffer.read(4)
    if len(raw) != 4:
        return None
    length = struct.unpack("=I", raw)[0]
    if length > 1024 * 1024:
        raise RuntimeError("Native message is too large.")
    payload = sys.stdin.buffer.read(length)
    if len(payload) != length:
        raise RuntimeError("Incomplete native message.")
    return json.loads(payload.decode("utf-8"))


def write_message(message):
    payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(payload)))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def main():
    if os.name == 'nt':
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    try:
        while True:
            message = read_message()
            if message is None:
                break
            if message.get("action") == "start":
                try:
                    write_message(start_engine())
                except Exception as error:
                    write_message({"ok": False, "error": str(error)})
            elif message.get("action") == "ping":
                write_message({"ok": engine_ready()})
            else:
                write_message({"ok": False, "error": "Unknown ClipForge action."})
    finally:
        if ENGINE_PROCESS is not None and ENGINE_PROCESS.poll() is None:
            ENGINE_PROCESS.terminate()
            try:
                ENGINE_PROCESS.wait(timeout=8)
            except subprocess.TimeoutExpired:
                ENGINE_PROCESS.kill()


if __name__ == "__main__":
    main()
