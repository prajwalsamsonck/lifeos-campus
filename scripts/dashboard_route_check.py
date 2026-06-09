"""Smoke-check the public dashboard routes without starting a server."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import app


ROUTES = {
    "/": 200,
    "/demo": 302,
    "/live": 302,
    "/api/status": 200,
    "/api/twin": 200,
}


def main() -> int:
    client = app.test_client()
    failed = False

    for route, expected in ROUTES.items():
        response = client.get(route)
        ok = response.status_code == expected
        print(f"{'PASS' if ok else 'FAIL'} {route:<12} {response.status_code}")
        failed = failed or not ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
