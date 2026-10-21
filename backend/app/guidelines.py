"""Versioned guideline and local-protocol retrieval with citations.

Retrieval is deterministic (concept tags from the evidence graph plus keyword
overlap). Nothing is generated, no patient data enters a query, and treatment
questions are refused by policy.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.evidence import get_evidence_graph
from app.records import local_protocols, utc_now

ALLOWED_TOPICS = {"screening", "recognition", "assessment", "monitoring", "escalation", "governance"}
TREATMENT_TERMS = {
    "antibiotic", "antibiotics", "antimicrobial", "antimicrobials", "dose", "dosing", "fluid", "fluids",
    "bolus", "crystalloid", "vasopressor", "vasopressors", "noradrenaline", "norepinephrine", "steroid",
    "steroids", "hydrocortisone", "administer", "give", "prescribe", "treat", "treatment", "therapy", "ml/kg",
}
DISCLAIMER = (
    "Curated guideline context for review — not patient-specific advice. Treatment recommendations "
    "are excluded by policy; follow the hospital's approved protocols and the clinical team."
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9/\-]*", text.lower()))


class GuidelineRegistry:
    def __init__(self, path: str | Path) -> None:
        raw = Path(path).read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.document = json.loads(raw)
        self.version = self.document["version"]
        self.sources = {source["source_id"]: source for source in self.document["sources"]}
        self.passages = self.document["passages"]
        for passage in self.passages:
            if passage["source_id"] not in self.sources:
                raise ValueError(f"Passage {passage['passage_id']} cites an unknown source")
            if passage["topic"] not in ALLOWED_TOPICS:
                raise ValueError(f"Passage {passage['passage_id']} has a disallowed topic {passage['topic']}")

    def cite(self, passage: dict[str, Any]) -> dict[str, Any]:
        source = self.sources[passage["source_id"]]
        return {
            **passage,
            "source_type": "guideline",
            "citation": {
                "title": source["title"],
                "publisher": source["publisher"],
                "version": source["version"],
                "published": source["published"],
                "url": source["url"],
                "doi": source["doi"],
                "section": passage["section"],
                "recommendation": passage["recommendation"],
                "review_due": source["review_due"],
            },
        }


_registry: GuidelineRegistry | None = None


def get_guideline_registry() -> GuidelineRegistry:
    global _registry
    if _registry is None:
        _registry = GuidelineRegistry(settings.guidelines_path)
    return _registry


def approved_local_protocols(engine: Any) -> list[dict[str, Any]]:
    rows = engine.records.select(local_protocols, local_protocols.c.status == "approved")
    protocols = []
    for row in rows:
        payload = json.loads(row["payload"])
        protocols.append({
            "passage_id": row["entry_id"],
            "source_type": "local_protocol",
            "section": payload["section"],
            "topic": payload["topic"],
            "text": payload["text"],
            "concepts": payload["concepts"],
            "keywords": sorted(_tokens(payload["title"] + " " + payload["section"])),
            "citation": {
                "title": payload["title"],
                "publisher": "Local hospital protocol",
                "version": payload["version"],
                "document_ref": payload["document_ref"],
                "review_due": payload["review_due"],
                "approved_by": row["approved_by"],
                "approved_at": row["approved_at"],
            },
        })
    return protocols


def _site_approved(engine: Any) -> bool:
    approval = engine.site.state.guideline_approval or {}
    return approval.get("registry_version") == get_guideline_registry().version


def _visible_guidelines(engine: Any) -> tuple[bool, str | None]:
    approved = _site_approved(engine)
    if approved or engine.site.state.effective_mode == "demo":
        return approved, None
    return approved, "guideline_registry_version_not_approved_by_site"


def guidance_for_features(engine: Any, features: list[str]) -> dict[str, Any]:
    registry = get_guideline_registry()
    graph = get_evidence_graph()
    feature_concepts = []
    concepts: set[str] = set()
    for feature in features[:12]:
        result = graph.query_feature(feature)
        ids = [concept["id"] for concept in result["curated_clinical_context"]["dysfunction_concepts"]]
        feature_concepts.append({"feature": feature, "mapped": result["mapped"], "concepts": ids})
        concepts.update(ids)
    approved, withheld = _visible_guidelines(engine)
    candidates = [] if withheld else [registry.cite(p) for p in registry.passages]
    candidates += approved_local_protocols(engine)
    ranked = []
    for order, passage in enumerate(candidates):
        matched = sorted(set(passage["concepts"]) & concepts)
        general = "*" in passage["concepts"]
        if not matched and not general:
            continue
        local_first = 0 if passage["source_type"] == "local_protocol" else 1
        ranked.append((local_first, -len(matched), order, {**passage, "matched_concepts": matched}))
    ranked.sort(key=lambda item: item[:3])
    return {
        "registry_version": registry.version,
        "registry_sha256": registry.sha256,
        "site_approved": approved,
        "withheld_reason": withheld,
        "features": feature_concepts,
        "passages": [item[3] for item in ranked],
        "patient_specific": False,
        "policy": registry.document["policy"],
        "disclaimer": DISCLAIMER,
    }


def search_guidance(engine: Any, query: str, limit: int = 5) -> dict[str, Any]:
    registry = get_guideline_registry()
    tokens = _tokens(query)
    refused = sorted(tokens & TREATMENT_TERMS)
    base = {
        "query": query,
        "registry_version": registry.version,
        "patient_specific": False,
        "disclaimer": DISCLAIMER,
    }
    if refused:
        return {
            **base,
            "refused": True,
            "refusal_reason": "Treatment and dosing questions are out of scope for PredictRx. "
                              "Use the hospital's approved protocol and the clinical team.",
            "matched_terms": refused,
            "results": [],
        }
    approved, withheld = _visible_guidelines(engine)
    candidates = [] if withheld else [registry.cite(p) for p in registry.passages]
    candidates += approved_local_protocols(engine)
    scored = []
    for order, passage in enumerate(candidates):
        haystack = _tokens(passage["text"]) | set(passage.get("keywords", [])) | _tokens(passage["section"])
        score = len(tokens & haystack)
        if score:
            local_first = 0 if passage["source_type"] == "local_protocol" else 1
            scored.append((-score, local_first, order, {**passage, "score": score}))
    scored.sort(key=lambda item: item[:3])
    return {
        **base,
        "refused": False,
        "site_approved": approved,
        "withheld_reason": withheld,
        "results": [item[3] for item in scored[:limit]],
    }


def submit_local_protocol(engine: Any, actor: Any, payload: dict[str, Any]) -> dict[str, Any]:
    if set(_tokens(payload["text"])) & {"dose", "dosing", "ml/kg", "mg/kg"}:
        raise ValueError("Local protocol excerpts shown by PredictRx may not contain doses.")
    submitted_at = utc_now()
    entry_id = "local-" + hashlib.sha256(f"{payload['title']}|{payload['version']}|{submitted_at}".encode()).hexdigest()[:16]
    row = {
        "entry_id": entry_id,
        "payload": json.dumps(payload),
        "status": "pending_approval",
        "submitted_by": actor.user_id,
        "submitted_at": submitted_at,
        "approved_by": None,
        "approved_at": None,
    }
    with engine.lock:
        engine._require_writable()
        engine.records.insert(local_protocols, row)
        engine._log("local_protocol_submitted", {"entry_id": entry_id, "actor": actor.user_id,
                                                 "actor_role": actor.role, "title": payload["title"],
                                                 "version": payload["version"]})
    return {**row, "payload": payload}


def decide_local_protocol(engine: Any, actor: Any, entry_id: str, decision: str) -> dict[str, Any]:
    rows = engine.records.select(local_protocols, local_protocols.c.entry_id == entry_id)
    if not rows:
        raise KeyError(entry_id)
    row = rows[0]
    if decision == "approve":
        if row["status"] != "pending_approval":
            raise ValueError("Only pending protocols can be approved.")
        if row["submitted_by"] == actor.user_id:
            raise PermissionError("Two-person rule: the submitter cannot approve their own protocol.")
        row.update(status="approved", approved_by=actor.user_id, approved_at=utc_now())
    elif decision == "retire":
        row.update(status="retired")
    else:
        raise ValueError("Decision must be approve or retire.")
    with engine.lock:
        engine._require_writable()
        engine.records.upsert(local_protocols, "entry_id", row)
        engine._log(f"local_protocol_{row['status']}", {"entry_id": entry_id, "actor": actor.user_id,
                                                         "actor_role": actor.role})
    return {**row, "payload": json.loads(row["payload"])}


def list_local_protocols(engine: Any) -> list[dict[str, Any]]:
    rows = engine.records.select(local_protocols, order_by=local_protocols.c.submitted_at.desc())
    return [{**row, "payload": json.loads(row["payload"])} for row in rows]
