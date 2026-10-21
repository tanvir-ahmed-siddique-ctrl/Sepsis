"""In-process operational metrics and audit-chain verification.

Metrics are exposed in Prometheus text format at ``/metrics``. They are process-local,
which matches the single-active-writer deployment.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict
from typing import Any

LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
AUDIT_ENVELOPE_KEYS = {"audit_id", "at", "event_hash"}


class Metrics:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.requests: dict[tuple[str, str, int], int] = defaultdict(int)
        self.request_buckets: dict[str, list[int]] = defaultdict(lambda: [0] * (len(LATENCY_BUCKETS) + 1))
        self.request_sum: dict[str, float] = defaultdict(float)
        self.inference_count = 0
        self.inference_seconds = 0.0
        self.inference_failures = 0
        self.ingest_events: dict[tuple[str, str], int] = defaultdict(int)
        self.rejected: dict[tuple[str, str], int] = defaultdict(int)
        self.started_at = time.time()

    def observe_request(self, method: str, route: str, status: int, seconds: float) -> None:
        with self.lock:
            self.requests[(method, route, status)] += 1
            buckets = self.request_buckets[route]
            for index, bound in enumerate(LATENCY_BUCKETS):
                if seconds <= bound:
                    buckets[index] += 1
            buckets[-1] += 1
            self.request_sum[route] += seconds

    def observe_inference(self, seconds: float) -> None:
        with self.lock:
            self.inference_count += 1
            self.inference_seconds += seconds

    def inference_failed(self) -> None:
        with self.lock:
            self.inference_failures += 1

    def observe_ingest(self, connector: str, status: str) -> None:
        with self.lock:
            self.ingest_events[(connector, status)] += 1

    def request_rejected(self, bucket: str, reason: str) -> None:
        with self.lock:
            self.rejected[(bucket, reason)] += 1


METRICS = Metrics()


def _canonical_hash(event: dict[str, Any]) -> str:
    canonical = {key: value for key, value in event.items() if key not in AUDIT_ENVELOPE_KEYS}
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class AuditVerifier:
    """Incrementally verifies linkage and content hashes of the append-only audit log."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self.verified = 0
        self.last_hash = "0" * 64
        self.linkage_breaks: list[int] = []
        self.content_mismatches: list[int] = []

    def verify(self, audit: list[dict[str, Any]]) -> dict[str, Any]:
        with self.lock:
            if len(audit) < self.verified:
                self._reset()
            for index in range(self.verified, len(audit)):
                event = audit[index]
                if event.get("previous_hash") != self.last_hash:
                    self.linkage_breaks.append(index)
                if _canonical_hash(event) != event.get("event_hash"):
                    self.content_mismatches.append(index)
                self.last_hash = event.get("event_hash", "")
            self.verified = len(audit)
            return {
                "events_verified": self.verified,
                "linkage_valid": not self.linkage_breaks,
                "linkage_breaks": self.linkage_breaks[:20],
                "content_hash_mismatches": len(self.content_mismatches),
                "first_content_mismatches": self.content_mismatches[:20],
                "head_hash": self.last_hash,
            }


def verify_audit_chain(audit: list[dict[str, Any]]) -> dict[str, Any]:
    return AuditVerifier().verify(audit)


def _labels(**labels: Any) -> str:
    inner = ",".join(f'{key}="{str(value).replace(chr(34), "")}"' for key, value in labels.items())
    return "{" + inner + "}"


def render_prometheus(gauges: dict[str, list[tuple[dict[str, Any], float]]]) -> str:
    lines: list[str] = []
    with METRICS.lock:
        lines.append("# TYPE predictrx_http_requests_total counter")
        for (method, route, status), count in sorted(METRICS.requests.items()):
            lines.append(f"predictrx_http_requests_total{_labels(method=method, route=route, status=status)} {count}")
        lines.append("# TYPE predictrx_http_request_seconds histogram")
        for route, buckets in sorted(METRICS.request_buckets.items()):
            for bound, count in zip(LATENCY_BUCKETS, buckets):
                lines.append(f"predictrx_http_request_seconds_bucket{_labels(route=route, le=bound)} {count}")
            lines.append(f"predictrx_http_request_seconds_bucket{_labels(route=route, le='+Inf')} {buckets[-1]}")
            lines.append(f"predictrx_http_request_seconds_sum{_labels(route=route)} {METRICS.request_sum[route]:.6f}")
            lines.append(f"predictrx_http_request_seconds_count{_labels(route=route)} {buckets[-1]}")
        lines.append("# TYPE predictrx_inference_total counter")
        lines.append(f"predictrx_inference_total {METRICS.inference_count}")
        lines.append("# TYPE predictrx_inference_seconds_sum counter")
        lines.append(f"predictrx_inference_seconds_sum {METRICS.inference_seconds:.6f}")
        lines.append("# TYPE predictrx_inference_failures_total counter")
        lines.append(f"predictrx_inference_failures_total {METRICS.inference_failures}")
        lines.append("# TYPE predictrx_ingest_requests_total counter")
        for (connector, status), count in sorted(METRICS.ingest_events.items()):
            lines.append(f"predictrx_ingest_requests_total{_labels(connector=connector, status=status)} {count}")
        lines.append("# TYPE predictrx_requests_rejected_total counter")
        for (bucket, reason), count in sorted(METRICS.rejected.items()):
            lines.append(f"predictrx_requests_rejected_total{_labels(bucket=bucket, reason=reason)} {count}")
        lines.append("# TYPE predictrx_uptime_seconds gauge")
        lines.append(f"predictrx_uptime_seconds {time.time() - METRICS.started_at:.0f}")
    for name, samples in sorted(gauges.items()):
        lines.append(f"# TYPE {name} gauge")
        for labels, value in samples:
            rendered = _labels(**labels) if labels else ""
            lines.append(f"{name}{rendered} {value}")
    return "\n".join(lines) + "\n"
