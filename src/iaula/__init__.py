import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Playwright en apps empaquetadas usa "<app>/_internal/.../.local-browsers" y falla.
    # Forzamos la carpeta compartida de navegadores del usuario (o la del instalador).
    _base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path(_base) / "ms-playwright"))

__version__ = "1.2.0"
