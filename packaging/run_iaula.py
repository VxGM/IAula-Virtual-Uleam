import os
import sys

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _check() -> int:
    from iaula import actions
    from iaula.config import load_config
    from iaula.report import notify

    cfg = load_config()
    try:
        rep = actions.run_check(cfg, days=30, log=lambda _line: None)
    except Exception as exc:
        notify("IAula", f"No pude revisar el aula: {exc}")
        return 1
    if rep["new_materials"] or rep["new_tasks"] or rep["upcoming_tasks"]:
        notify("IAula", f"{len(rep['new_materials'])} material(es) nuevo(s), "
                        f"{len(rep['upcoming_tasks'])} entrega(s) pendiente(s)")
    return 0


def _install_task() -> int:
    import subprocess
    from pathlib import Path

    exe = Path(sys.executable)
    if getattr(sys, "frozen", False):
        command = f'"{exe}" --check --notify'
    else:
        pythonw = exe.with_name("pythonw.exe")
        runner = pythonw if pythonw.exists() else exe
        command = f'"{runner}" -m iaula check --notify'
    result = subprocess.run(
        ["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", "07:30",
         "/TN", "IAula-Check", "/TR", command],
        capture_output=True, text=True, timeout=30,
    )
    return 0 if result.returncode == 0 else 1


def _remove_task() -> int:
    import subprocess

    result = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", "IAula-Check"],
        capture_output=True, text=True, timeout=30,
    )
    return 0 if result.returncode == 0 else 1


if "--ensure-deps" in sys.argv:
    from iaula import actions

    actions.ensure_chromium()
    print("Dependencias listas")
    sys.exit(0)

if "--check" in sys.argv:
    raise SystemExit(_check())

if "--migrate-legacy" in sys.argv:
    from iaula.config import load_config, migrate_local_secrets

    migrate_local_secrets(load_config().root)
    sys.exit(0)

if "--install-task" in sys.argv:
    raise SystemExit(_install_task())

if "--remove-task" in sys.argv:
    raise SystemExit(_remove_task())

from iaula.config import load_config
from iaula.desktop import run

if __name__ == "__main__":
    raise SystemExit(run(load_config()))
