"""Site operating mode.

* ``demo`` — held-out replay beds and synthetic data; alerts are interruptive inside the demo.
* ``silent`` — real feeds are scored and recorded; bedside staff are blinded and alerts are
  recorded as shadow alerts only.
* ``live`` — interruptive alerts for real encounters. Requested live mode stays
  ``live-disabled`` (behaving like silent) until every readiness gate passes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.config import settings
from app.records import RecordStore, utc_now

REQUESTABLE_MODES = ("demo", "silent", "live")
CONFIG_KEY = "site"


@dataclass
class SiteState:
    site_id: str
    requested_mode: str
    live_authorized: bool = False
    soft_landing: bool = False
    gates_at_request: list[dict[str, Any]] = field(default_factory=list)
    governance_signoff: dict[str, Any] | None = None
    guideline_approval: dict[str, Any] | None = None
    mapping_signoff: dict[str, Any] | None = None
    updated_at: str | None = None
    updated_by: str | None = None

    @property
    def effective_mode(self) -> str:
        if self.requested_mode == "live":
            return "live" if self.live_authorized else "live-disabled"
        return self.requested_mode

    @property
    def interruptive_alerts_enabled(self) -> bool:
        return self.effective_mode in {"demo", "live"}

    @property
    def blinded(self) -> bool:
        return self.effective_mode in {"silent", "live-disabled"}

    def as_dict(self) -> dict[str, Any]:
        body = asdict(self)
        body.update(
            effective_mode=self.effective_mode,
            interruptive_alerts_enabled=self.interruptive_alerts_enabled,
            bedside_blinded=self.blinded,
            demo_auth_enabled=settings.demo_mode,
        )
        return body


class SiteManager:
    def __init__(self, records: RecordStore) -> None:
        self.records = records
        stored = records.load_config(CONFIG_KEY)
        if stored:
            known = {key: value for key, value in stored.items() if key in SiteState.__dataclass_fields__}
            self.state = SiteState(**known)
        else:
            self.state = SiteState(site_id=settings.site_id, requested_mode=settings.site_mode)
        if self.state.requested_mode == "demo" and not settings.demo_mode:
            self.state.requested_mode = "silent"
        if self.state.requested_mode not in REQUESTABLE_MODES:
            self.state.requested_mode = "silent"

    def save(self, actor_id: str) -> None:
        self.state.updated_at = utc_now()
        self.state.updated_by = actor_id
        payload = asdict(self.state)
        self.records.save_config(CONFIG_KEY, payload, actor_id)

    def set_mode(self, mode: str, actor_id: str, gates: list[dict[str, Any]]) -> SiteState:
        if mode not in REQUESTABLE_MODES:
            raise ValueError(f"Mode must be one of {REQUESTABLE_MODES}")
        if mode == "demo" and not settings.demo_mode:
            raise ValueError("Demo mode requires DEMO_MODE=true.")
        self.state.requested_mode = mode
        self.state.gates_at_request = gates if mode == "live" else []
        self.state.live_authorized = mode == "live" and bool(gates) and all(g["passed"] for g in gates)
        self.save(actor_id)
        return self.state
