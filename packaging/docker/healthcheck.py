import urllib.request
import sys

url = "http://127.0.0.1:7800/api/sessions"
try:
    data = urllib.request.urlopen(url, timeout=5).read()
    print(data.decode("utf-8", errors="replace"))
    sys.exit(0)
except Exception as e:
    print(f"healthcheck failed: {e}", file=sys.stderr)
    sys.exit(1)
