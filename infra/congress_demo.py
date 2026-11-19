"""Preflight and reset helper for the offline AI Congress demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

EXPECTED_MODEL_SHA256 = "a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d"
ROOT = Path(__file__).resolve().parents[1]


def get_json(url: str) -> dict:
    with urlopen(url, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        return json.load(response)


def check_url(url: str) -> None:
    with urlopen(url, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")


def preflight(api: str, web: str) -> int:
    failures: list[str] = []
    model = ROOT / "ml" / "artifacts" / "models" / "run4_frozen" / "model.joblib"
    actual = hashlib.sha256(model.read_bytes()).hexdigest() if model.exists() else "missing"
    if actual != EXPECTED_MODEL_SHA256:
        failures.append(f"frozen model hash: expected {EXPECTED_MODEL_SHA256}, got {actual}")

    ready: dict = {}
    try:
        ready = get_json(f"{api}/ready")
        if ready.get("status") != "ready":
            failures.append(f"API readiness status is {ready.get('status')!r}")
        if ready.get("model_hash") != EXPECTED_MODEL_SHA256:
            failures.append("API loaded an unexpected model hash")
    except (OSError, URLError, ValueError, RuntimeError) as error:
        failures.append(f"API readiness: {error}")

    for path in (
        "/",
        "/judge",
        "/presentation",
        "/evidence",
        "/connection",
        "/integration",
        "/model",
        "/docs",
        "/chart",
        "/ward",
        "/readiness",
        "/signin",
    ):
        try:
            check_url(f"{web}{path}")
        except (OSError, URLError, RuntimeError) as error:
            failures.append(f"web {path}: {error}")

    if failures:
        print("CONGRESS PREFLIGHT FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("CONGRESS PREFLIGHT PASSED")
    print(f"- frozen model: {EXPECTED_MODEL_SHA256}")
    print(f"- API: {ready.get('status')} ({ready.get('site_mode')})")
    print(f"- judge tour: {web}/judge")
    print(f"- open presentation: {web}/presentation")
    print("- internet connection is not required for the running demo")
    return 0


def reset(api: str) -> int:
    request = Request(
        f"{api}/v1/demo/replay/reset",
        data=b"",
        method="POST",
        headers={"X-Demo-User": "congress-presenter", "X-Demo-Role": "admin"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = json.load(response)
    except (OSError, URLError, ValueError) as error:
        print(f"DEMO RESET FAILED: {error}")
        return 1
    print(f"DEMO RESET: {body}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "reset"))
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--web", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    return preflight(args.api.rstrip("/"), args.web.rstrip("/")) if args.command == "check" else reset(args.api.rstrip("/"))


if __name__ == "__main__":
    sys.exit(main())
