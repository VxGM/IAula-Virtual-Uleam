import sys

if "--ensure-deps" in sys.argv:
    from iaula import actions

    actions.ensure_chromium()
    print("Dependencias listas")
    sys.exit(0)

from iaula.config import load_config
from iaula.desktop import run

if __name__ == "__main__":
    raise SystemExit(run(load_config()))
