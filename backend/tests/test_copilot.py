"""Mapping copilot: deterministic retrieval, LLM constraint, PHI refusal, API access."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.integrations import copilot
from app.integrations.mapping import MappingRegistry

REGISTRY = MappingRegistry(Path(__file__).resolve().parents[2] / "knowledge" / "fhir_mapping.v1.json")


@pytest.mark.parametrize(
    ("display", "unit", "target"),
    [
        ("S. Creatinine", "µmol/L", "Creatinine"),
        ("Pulse", "bpm", "HR"),
        ("নাড়ি", "bpm", "HR"),
        ("তাপমাত্রা", "°F", "Temp"),
        ("RBS", "mmol/L", "Glucose"),
        ("Total Count (TC)", "x10^9/L", "WBC"),
        ("K+", "mmol/L", "Potassium"),
    ],
)
def test_local_terms_retrieve_expected_target(display, unit, target):
    top = copilot.retrieve(REGISTRY, display, unit)[0]
    assert top.target == target
    assert top.unit_status == "convertible"


def test_range_check_flags_wrong_unit_scale():
    plausible = copilot.retrieve(REGISTRY, "Temp", "°F", 97, 104)[0]
    assert plausible.range_status == "plausible"
    implausible = copilot.retrieve(REGISTRY, "Temp", "°C", 97, 104)[0]
    assert implausible.range_status == "outside_plausible_range"


def test_known_local_pitfalls_raise_cautions():
    assert any("not BUN" in text for text in copilot.cautions_for("S. Urea"))
    assert any("SaO2" in text for text in copilot.cautions_for("অক্সিজেন স্যাচুরেশন"))
    assert copilot.cautions_for("Heart rate") == []


def test_identifier_like_input_is_refused():
    with pytest.raises(ValueError):
        copilot.suggest(REGISTRY, local_code="MRN 12345678", local_display="Pulse", local_unit="bpm",
                        sample_min=None, sample_max=None, use_llm=False)


def test_deterministic_mode_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "copilot_llm_url", None)
    result = copilot.suggest(REGISTRY, local_code="LAB-1", local_display="S. Creatinine", local_unit="µmol/L",
                             sample_min=60, sample_max=400, use_llm=True)
    assert result["llm"]["status"] == "disabled"
    assert result["recommended_code"] == "2160-0"
    assert result["proposed_registry_patch"]["conversion"][0] == pytest.approx(1 / 88.4, rel=1e-3)
    assert result["prompt"]["sha256"] == copilot.prompt_sha256()


def _fake_llm(answer: dict):
    def fake(provider, url, model, payload, api_key=""):
        request = json.loads(payload)
        assert request["options"]["temperature"] == 0
        assert request["format"]["properties"]["choice_code"]["enum"][-1] == "none"
        return json.dumps(answer)
    return fake


def test_llm_choice_must_come_from_retrieved_candidates(monkeypatch):
    monkeypatch.setattr(settings, "copilot_llm_url", "http://llm.local")
    monkeypatch.setattr(copilot, "_ask_llm_cached", _fake_llm(
        {"choice_code": "9999-9", "confidence": "high", "rationale": "invented", "cautions": []}))
    result = copilot.suggest(REGISTRY, local_code="LAB-2", local_display="Pulse", local_unit="bpm",
                             sample_min=None, sample_max=None, use_llm=True)
    assert result["llm"]["status"] == "rejected"
    assert result["recommended_code"] == "8867-4"


def test_llm_abstention_is_respected(monkeypatch):
    monkeypatch.setattr(settings, "copilot_llm_url", "http://llm.local")
    monkeypatch.setattr(copilot, "_ask_llm_cached", _fake_llm(
        {"choice_code": "none", "confidence": "low", "rationale": "urea vs BUN unclear", "cautions": []}))
    result = copilot.suggest(REGISTRY, local_code="LAB-3", local_display="S. Urea", local_unit="mg/dL",
                             sample_min=None, sample_max=None, use_llm=True)
    assert result["recommended_code"] is None
    assert result["needs_analyst_confirmation"] is True
    assert result["proposed_registry_patch"] is None


class _Reply:
    def __init__(self, status: int, body: dict):
        self.status_code, self._body = status, body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise copilot.httpx.HTTPStatusError("error", request=None, response=None)


def _openai_settings(monkeypatch, url="https://api.example-llm.com/v1"):
    from pydantic import SecretStr

    monkeypatch.setattr(settings, "copilot_llm_provider", "openai")
    monkeypatch.setattr(settings, "copilot_llm_url", url)
    monkeypatch.setattr(settings, "copilot_llm_model", "any-model")
    monkeypatch.setattr(settings, "copilot_llm_api_key", SecretStr("sk-test"))
    monkeypatch.setattr(settings, "copilot_embed_model", None)
    copilot._ask_llm_cached.cache_clear()


def test_openai_compatible_provider_falls_back_and_parses_reasoning_output(monkeypatch):
    _openai_settings(monkeypatch)
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None, **_):
        calls.append((url, json, headers))
        if "json_schema" in str(json.get("response_format")) or "reasoning_effort" in json:
            return _Reply(400, {"error": "unsupported parameter"})
        content = '<think>serum creatinine</think>{"choice_code": "2160-0", "confidence": "high", ' \
                  '"rationale": "S. means serum", "cautions": []}'
        return _Reply(200, {"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(copilot.httpx, "post", fake_post)
    result = copilot.suggest(REGISTRY, local_code="LAB-5", local_display="S. Creatinine", local_unit="mg/dL",
                             sample_min=None, sample_max=None, use_llm=True)
    assert result["llm"]["status"] == "ok"
    assert result["llm"]["provider"] == "openai-compatible" and result["llm"]["external"] is True
    assert result["recommended_code"] == "2160-0"
    assert [call[0] for call in calls] == ["https://api.example-llm.com/v1/chat/completions"] * 3
    assert calls[0][1]["reasoning_effort"] == "none"
    assert calls[2][1]["response_format"] == {"type": "json_object"} and "reasoning_effort" not in calls[2][1]
    assert calls[0][2] == {"Authorization": "Bearer sk-test"}
    assert "JSON" in calls[0][1]["messages"][0]["content"]
    assert "sample" not in calls[0][1]["messages"][-1]["content"]


def test_external_llm_is_refused_on_hospital_sites_until_approved(monkeypatch):
    _openai_settings(monkeypatch)
    monkeypatch.setattr(settings, "demo_mode", False)
    monkeypatch.setattr(settings, "copilot_external_llm_approved", False)
    monkeypatch.setattr(copilot.httpx, "post", lambda *a, **k: pytest.fail("must not call an unapproved endpoint"))
    result = copilot.suggest(REGISTRY, local_code="LAB-6", local_display="Pulse", local_unit="bpm",
                             sample_min=None, sample_max=None, use_llm=True)
    assert result["llm"]["status"] == "blocked"
    assert result["recommended_code"] == "8867-4"

    monkeypatch.setattr(settings, "copilot_external_llm_approved", True)
    monkeypatch.setattr(copilot, "_ask_llm_cached", _fake_llm(
        {"choice_code": "8867-4", "confidence": "high", "rationale": "pulse is heart rate", "cautions": []}))
    assert copilot.suggest(REGISTRY, local_code="LAB-6", local_display="Pulse", local_unit="bpm",
                           sample_min=None, sample_max=None, use_llm=True)["llm"]["status"] == "ok"


@pytest.mark.parametrize(
    ("url", "external"),
    [
        ("http://localhost:11434", False),
        ("http://127.0.0.1:11434/v1", False),
        ("http://10.20.0.5:8000/v1", False),
        ("http://ollama:11434", False),
        ("http://llm.hospital.local/v1", False),
        ("https://api.openai.com/v1", True),
        ("https://generativelanguage.googleapis.com/v1beta/openai", True),
        ("http://8.8.8.8/v1", True),
    ],
)
def test_endpoint_locality(url, external):
    assert copilot.endpoint_is_external(url) is external


def test_model_call_budget_falls_back_to_deterministic(monkeypatch):
    monkeypatch.setattr(settings, "copilot_llm_provider", "ollama")
    monkeypatch.setattr(settings, "copilot_llm_url", "http://llm.local")
    monkeypatch.setattr(settings, "copilot_llm_per_minute", 0)
    monkeypatch.setattr(copilot, "_ask_llm_cached", lambda *a: pytest.fail("budget exhausted; no call expected"))
    result = copilot.suggest(REGISTRY, local_code="LAB-7", local_display="Pulse", local_unit="bpm",
                             sample_min=None, sample_max=None, use_llm=True)
    assert result["llm"]["status"] == "rate_limited"
    assert result["recommended_code"] == "8867-4"


def test_vector_neighbours_raise_recall_but_not_deterministic_choice():
    lexical = copilot.retrieve(REGISTRY, "প্লাটিলেট", None)
    assert "Platelets" not in [item.target for item in lexical]
    semantic = {code: 0.3 for code in {m.code for m in REGISTRY.entries.values()}}
    semantic["777-3"] = 0.62
    hybrid = copilot.retrieve(REGISTRY, "প্লাটিলেট", None, semantic=semantic)
    assert hybrid[0].target == "Platelets"
    assert hybrid[0].as_dict()["semantic_similarity"] == 0.62
    assert copilot.deterministic_choice(hybrid) is None


def test_lexical_benchmark_regression():
    from app.integrations.copilot_benchmark import run

    result = run(REGISTRY, hybrid=False)
    assert result["negative_abstention"] == 1.0
    assert result["recall_at_5"] >= 0.67
    assert result["top1_accuracy"] >= 0.48
    assert all(miss["got"] is None for miss in result["misses"])


@pytest.mark.skipif(
    not (Path(settings.model_path).exists() and (Path(settings.demo_cases_dir) / "manifest.json").exists()),
    reason="model bundle or demo cases not generated",
)
def test_suggest_endpoint_is_admin_only_and_audited(monkeypatch):
    from fastapi.testclient import TestClient

    settings.database_url = "sqlite:///:memory:"
    settings.demo_mode = True
    monkeypatch.setattr(settings, "copilot_llm_url", None)
    from app.main import app

    admin = {"X-Demo-User": "interface-analyst", "X-Demo-Role": "admin"}
    with TestClient(app, headers=admin) as client:
        body = {"local_code": "LAB-9", "local_display": "SpO2", "local_unit": "%"}
        assert client.post("/v1/integrations/mappings/suggest", json=body,
                           headers={"X-Demo-User": "rn", "X-Demo-Role": "nurse"}).status_code == 403
        response = client.post("/v1/integrations/mappings/suggest", json=body)
        assert response.status_code == 200
        assert response.json()["candidates"][0]["target"] == "O2Sat"
        audit = client.get("/v1/audit?event=mapping_suggestion_generated").json()["events"]
        assert audit and audit[0]["local_code"] == "LAB-9"
        assert client.get("/v1/integrations/mappings/unmapped",
                          headers={"X-Demo-User": "ops", "X-Demo-Role": "operator"}).status_code == 200
