import json, subprocess, sys, time, urllib.request
from pathlib import Path

import websocket

UD = r"C:\Users\ASUS\AppData\Local\BraveSoftware\Brave-Browser\User Data"
BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
OUT = Path(r"C:\Users\ASUS\.notebooklm\profiles\default\storage_state.json")
PORT = 9224
sys.stdout.reconfigure(encoding="utf-8")


def brave_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq brave.exe"], capture_output=True, text=True)
    return "brave.exe" in out.stdout


def main() -> int:
    deadline = time.time() + 150
    while brave_running():
        if time.time() > deadline:
            print("Brave esta abierto. Cierralo por completo y reintenta.")
            return 3
        print("esperando cierre de Brave...")
        time.sleep(5)

    proc = subprocess.Popen(
        [BRAVE, f"--user-data-dir={UD}", f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
         "--no-first-run", "--no-default-browser-check", "--window-position=-32000,-32000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ver = None
        for _ in range(30):
            try:
                ver = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2))
                break
            except Exception:
                time.sleep(1)
        if not ver:
            print("sin puerto de depuracion")
            return 4
        ws = websocket.create_connection(ver["webSocketDebuggerUrl"], timeout=60)
        ws.send(json.dumps({"id": 1, "method": "Storage.getCookies", "params": {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                break
        ws.close()
        allc = msg.get("result", {}).get("cookies", [])
        g = [c for c in allc if "google" in c.get("domain", "") or "youtube" in c.get("domain", "")]
        sid = any(c["name"] == "SID" and c["domain"] == ".google.com" and c.get("value") for c in g)
        print(f"cookies: {len(allc)} total, {len(g)} google/youtube, SID ok: {sid}")
        if not sid:
            return 1
        keep = ("name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite")
        state = {"cookies": [{k: c[k] for k in keep if k in c} for c in g], "origins": []}
        if OUT.exists():
            OUT.with_name(f"storage_state.json.bak-{int(time.time())}").write_text(
                OUT.read_text(encoding="utf-8"), encoding="utf-8")
        OUT.write_text(json.dumps(state), encoding="utf-8")
        print("sesion guardada en", OUT)
        print("verifica con: notebooklm auth check --test --json")
        return 0
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)


if __name__ == "__main__":
    sys.exit(main())
