"""Relay one site heartbeat to the fleet console (run every 5 minutes by cron or Task Scheduler).

Outbound HTTPS only: the hospital opens no inbound port. Environment:
PREDICTRX_API_URL (site API), PREDICTRX_API_TOKEN (operator token), FLEET_URL (console).
``--every SECONDS`` keeps relaying instead of exiting. PREDICTRX_DEMO_OPERATOR=true
authenticates with demo headers, which only a demo-mode site accepts.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx


def _site_headers() -> dict[str, str]:
    if os.environ.get("PREDICTRX_DEMO_OPERATOR", "").lower() == "true":
        return {"X-Demo-User": "fleet-relay", "X-Demo-Role": "operator"}
    return {"Authorization": f"Bearer {os.environ['PREDICTRX_API_TOKEN']}"}


def push_once() -> int:
    api = os.environ.get("PREDICTRX_API_URL", "http://127.0.0.1:8000").rstrip("/")
    fleet = os.environ["FLEET_URL"].rstrip("/")
    heartbeat = httpx.get(f"{api}/v1/ops/heartbeat", headers=_site_headers(), timeout=30)
    heartbeat.raise_for_status()
    body = heartbeat.json()
    if body.get("signature") is None:
        print("FLEET_SIGNING_KEY is not configured on the site; refusing to send an unsigned heartbeat.", file=sys.stderr)
        return 2
    sent = httpx.post(f"{fleet}/v1/heartbeats", json=body, timeout=30)
    print(sent.status_code, sent.text, flush=True)
    return 0 if sent.status_code == 200 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--every", type=float, default=None, help="Repeat every N seconds instead of exiting")
    args = parser.parse_args(argv)
    if args.every is None:
        return push_once()
    while True:
        try:
            push_once()
        except (httpx.HTTPError, KeyError, ValueError) as error:
            print(f"heartbeat not sent: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
