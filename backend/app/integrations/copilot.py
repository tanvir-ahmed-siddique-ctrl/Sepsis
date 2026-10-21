"""Mapping copilot: proposes how an unknown local observation maps to the registry.

Retrieval is deterministic and always available: keyword and synonym matching,
character-trigram similarity, unit compatibility and value-range plausibility
over the versioned mapping registry. An optional LLM (on-premises Ollama, or an
OpenAI-compatible API the site approves) receives field metadata only and may
only *choose among* the retrieved candidates and explain the choice; it never
invents codes or conversion factors. Output is a proposal for an interface
analyst. The registry changes only through a reviewed edit and the SHA-bound
sign-off workflow.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import settings
from app.integrations.mapping import MappingRegistry, normalize_unit
from app.ratelimit import LIMITER
from app.services.clinical_contract import SPECS

PROMPT_VERSION = "mapping-copilot/v1"
TOP_K = 5
# Hybrid retrieval: the nearest vector neighbours join the candidate pool and the
# final order is reciprocal-rank fusion of lexical and vector ranks. The lexical
# evidence score alone still gates deterministic recommendations, because
# embedding similarity cannot separate unseen concepts from Bangla matches.
VECTOR_NEIGHBOURS = 3
RRF_K = 10

# Local report vocabulary (Bangladesh lab slips, bedside charts and Bangla
# charting terms) → canonical targets. Ambiguous terms list every target.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "pulse": ("HR",), "pr": ("HR",), "hr": ("HR",), "heart rate": ("HR",), "নাড়ি": ("HR",), "পালস": ("HR",),
    "spo2": ("O2Sat",), "sp02": ("O2Sat",), "pulse ox": ("O2Sat",), "oxygen saturation": ("O2Sat", "SaO2"),
    "sao2": ("SaO2",),
    "temp": ("Temp",), "temperature": ("Temp",), "তাপমাত্রা": ("Temp",), "জ্বর": ("Temp",),
    "sbp": ("SBP",), "systolic": ("SBP",), "dbp": ("DBP",), "diastolic": ("DBP",),
    "map": ("MAP",), "mean arterial": ("MAP",),
    "bp": ("SBP", "DBP"), "blood pressure": ("SBP", "DBP"), "রক্তচাপ": ("SBP", "DBP"),
    "rr": ("Resp",), "resp": ("Resp",), "respiratory rate": ("Resp",), "শ্বাস": ("Resp",),
    "fio2": ("FiO2",), "ph": ("pH",), "pco2": ("PaCO2",), "paco2": ("PaCO2",),
    "hco3": ("HCO3",), "bicarbonate": ("HCO3",), "tco2": ("HCO3",), "be": ("BaseExcess",), "base excess": ("BaseExcess",),
    "lactate": ("Lactate",), "lac": ("Lactate",),
    "creatinine": ("Creatinine",), "s creatinine": ("Creatinine",), "creat": ("Creatinine",), "cr": ("Creatinine",),
    "bun": ("BUN",), "urea": ("BUN",), "blood urea": ("BUN",),
    "glucose": ("Glucose",), "rbs": ("Glucose",), "fbs": ("Glucose",), "cbg": ("Glucose",), "blood sugar": ("Glucose",),
    "k": ("Potassium",), "potassium": ("Potassium",), "cl": ("Chloride",), "chloride": ("Chloride",),
    "ca": ("Calcium",), "calcium": ("Calcium",), "mg": ("Magnesium",), "magnesium": ("Magnesium",),
    "po4": ("Phosphate",), "phosphate": ("Phosphate",), "phos": ("Phosphate",),
    "bilirubin": ("Bilirubin_total", "Bilirubin_direct"), "t bil": ("Bilirubin_total",), "tbil": ("Bilirubin_total",),
    "d bil": ("Bilirubin_direct",), "dbil": ("Bilirubin_direct",), "direct bilirubin": ("Bilirubin_direct",),
    "sgot": ("AST",), "ast": ("AST",), "alp": ("Alkalinephos",), "alk phos": ("Alkalinephos",),
    "wbc": ("WBC",), "tc": ("WBC",), "tlc": ("WBC",), "total count": ("WBC",),
    "plt": ("Platelets",), "platelet": ("Platelets",), "platelets": ("Platelets",),
    "hb": ("Hgb",), "hb%": ("Hgb",), "hgb": ("Hgb",), "haemoglobin": ("Hgb",), "hemoglobin": ("Hgb",),
    "hct": ("Hct",), "pcv": ("Hct",), "haematocrit": ("Hct",), "hematocrit": ("Hct",),
    "aptt": ("PTT",), "ptt": ("PTT",), "fibrinogen": ("Fibrinogen",),
    "trop i": ("TroponinI",), "troponin i": ("TroponinI",), "ctni": ("TroponinI",), "troponin": ("TroponinI",),
}

# Terms whose common local meaning differs from the registry target.
CAUTIONS: dict[str, str] = {
    "urea": "Serum urea is not BUN: BUN = urea × 0.467 (mg/dL). The analyst must confirm which the lab reports.",
    "hb%": "Hb% may be reported as percent of a reference rather than g/dL; confirm the lab's unit before mapping.",
    "tco2": "Total CO2 approximates but is not identical to measured bicarbonate.",
    "bilirubin": "Unqualified bilirubin is ambiguous; confirm total vs direct.",
    "bp": "A combined BP field must be split into systolic and diastolic components before mapping.",
    "blood pressure": "A combined BP field must be split into systolic and diastolic components before mapping.",
    "oxygen saturation": "Confirm pulse oximetry (SpO2) versus arterial blood gas (SaO2).",
    "অক্সিজেন স্যাচুরেশন": "Confirm pulse oximetry (SpO2) versus arterial blood gas (SaO2).",
    "troponin": "Confirm troponin I versus T and the assay unit (ng/mL vs ng/L).",
}

UNIT_ALIASES = {"°f": "degf", "f": "degf", "°c": "degc", "c": "degc", "µmol/l": "umol/l", "μmol/l": "umol/l",
                "mg%": "mg/dl", "bpm": "bpm", "/minute": "/min", "x10^9/l": "10*9/l", "x10^3/ul": "10*3/ul"}

PHI_PATTERN = re.compile(r"\d{6,}|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|@")
# Split on whitespace and ASCII punctuation only: Bengali vowel signs and nukta
# are combining marks that ``\w`` does not match.
SEPARATORS = re.compile(r"[\s.,;:()\[\]{}+\-/\\|_*#'\"]+")


def _normalize_text(text: str) -> str:
    return SEPARATORS.sub(" ", text.lower()).strip()


@dataclass(frozen=True)
class Candidate:
    code: str
    display: str
    target: str
    canonical_unit: str | None
    score: float
    matched_terms: tuple[str, ...]
    unit_status: str
    conversion: tuple[float, float] | None
    range_status: str
    semantic: float | None = None

    def as_dict(self) -> dict[str, Any]:
        spec = SPECS[self.target]
        return {
            "code": self.code,
            "system": "http://loinc.org",
            "display": self.display,
            "target": self.target,
            "canonical_unit": self.canonical_unit,
            "score": round(self.score, 3),
            "semantic_similarity": None if self.semantic is None else round(self.semantic, 3),
            "matched_terms": list(self.matched_terms),
            "unit_status": self.unit_status,
            "conversion": {"factor": self.conversion[0], "offset": self.conversion[1]} if self.conversion else None,
            "range_status": self.range_status,
            "plausible_range": [spec.minimum, spec.maximum],
        }


def _tokens(text: str) -> set[str]:
    return set(_normalize_text(text).split())


def _trigrams(text: str) -> set[str]:
    padded = f"  {_normalize_text(text)} "
    return {padded[i : i + 3] for i in range(len(padded) - 2)}


def _jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left and right else 0.0


def _unit_key(unit: str | None) -> str:
    key = normalize_unit(unit)
    return UNIT_ALIASES.get(key, key)


def _synonym_hits(display: str) -> dict[str, list[str]]:
    lowered = f" {_normalize_text(display)} "
    compact = lowered.replace(" ", "")
    hits: dict[str, list[str]] = {}
    for term, targets in SYNONYMS.items():
        if f" {term} " in lowered or compact == term.replace(" ", ""):
            for target in targets:
                hits.setdefault(target, []).append(term)
    return hits


def looks_like_phi(*values: str | None) -> bool:
    return any(value and PHI_PATTERN.search(value) for value in values)


EMBED_QUERY_INSTRUCTION = (
    "Instruct: Given a local laboratory or vital-sign field name, possibly abbreviated or in Bangla, "
    "retrieve the matching standard ICU observation\nQuery: "
)


def _headers() -> dict[str, str]:
    key = settings.copilot_llm_api_key.get_secret_value() if settings.copilot_llm_api_key else ""
    return {"Authorization": f"Bearer {key}"} if key else {}


def endpoint_is_external(url: str) -> bool:
    """True when the LLM endpoint is outside the hospital network (public DNS name or public IP)."""
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "." in host and not host.endswith((".local", ".internal", ".lan", ".localhost"))
    return not (address.is_private or address.is_loopback or address.is_link_local)


def llm_endpoint() -> dict[str, Any]:
    url = settings.copilot_llm_url
    return {
        "provider": "openai-compatible" if settings.copilot_llm_provider == "openai" else "ollama",
        "host": urlsplit(url).hostname if url else None,
        "external": bool(url) and endpoint_is_external(url),
    }


def _external_blocked() -> bool:
    url = settings.copilot_llm_url
    return bool(url) and endpoint_is_external(url) and not settings.demo_mode and not settings.copilot_external_llm_approved


@lru_cache(maxsize=512)
def _embed_cached(provider: str, url: str, model: str, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
    if provider == "openai":
        response = httpx.post(
            f"{url.rstrip('/')}/embeddings",
            json={"model": model, "input": list(texts)},
            headers=_headers(),
            timeout=settings.copilot_llm_timeout_seconds,
        )
        response.raise_for_status()
        rows = sorted(response.json()["data"], key=lambda row: row["index"])
        return tuple(tuple(row["embedding"]) for row in rows)
    response = httpx.post(
        f"{url.rstrip('/')}/api/embed",
        json={"model": model, "input": list(texts)},
        timeout=settings.copilot_llm_timeout_seconds,
    )
    response.raise_for_status()
    return tuple(tuple(vector) for vector in response.json()["embeddings"])


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = (sum(a * a for a in left) ** 0.5) * (sum(b * b for b in right) ** 0.5)
    return dot / norm if norm else 0.0


def _registry_documents(registry: MappingRegistry) -> list[tuple[str, str]]:
    return [(mapping.code, mapping.display) for mapping in sorted(registry.entries.values(), key=lambda item: item.code)]


def semantic_scores(registry: MappingRegistry, local_display: str) -> tuple[dict[str, float] | None, dict[str, Any]]:
    """Vector half of hybrid retrieval: cosine similarity from the configured embedding model."""
    if not (settings.copilot_llm_url and settings.copilot_embed_model):
        return None, {"mode": "lexical", "detail": "No embedding model configured."}
    if _external_blocked():
        return None, {"mode": "lexical", "detail": "External embedding endpoint is not approved for this site."}
    documents = _registry_documents(registry)
    provider, url, model = settings.copilot_llm_provider, settings.copilot_llm_url, settings.copilot_embed_model
    try:
        vectors = _embed_cached(provider, url, model, tuple(text for _, text in documents))
        (query,) = _embed_cached(provider, url, model, (EMBED_QUERY_INSTRUCTION + local_display,))
    except (httpx.HTTPError, KeyError, ValueError) as error:
        return None, {"mode": "lexical", "detail": f"Embedding model unavailable ({type(error).__name__})."}
    scores = {code: _cosine(query, vector) for (code, _), vector in zip(documents, vectors)}
    return scores, {"mode": "hybrid", "embedding_model": settings.copilot_embed_model, "documents": len(documents)}


def retrieve(
    registry: MappingRegistry,
    local_display: str,
    local_unit: str | None,
    sample_min: float | None = None,
    sample_max: float | None = None,
    k: int = TOP_K,
    semantic: dict[str, float] | None = None,
) -> list[Candidate]:
    query_tokens = _tokens(local_display)
    query_grams = _trigrams(local_display)
    synonyms = _synonym_hits(local_display)
    unit_key = _unit_key(local_unit)
    vector_rank = {code: rank for rank, code in enumerate(sorted(semantic or {}, key=lambda c: (-semantic[c], c)))}
    vector_pool = {code for code, rank in vector_rank.items() if rank < VECTOR_NEIGHBOURS}
    lexical_evidence: set[str] = set()
    ranked: list[Candidate] = []
    for mapping in registry.entries.values():
        document = f"{mapping.display} {mapping.target}"
        lexical = _jaccard(query_tokens, _tokens(document))
        fuzzy = max(_jaccard(query_grams, _trigrams(mapping.display)), _jaccard(query_grams, _trigrams(mapping.target)))
        synonym = 1.0 if mapping.target in synonyms else 0.0
        conversions = {UNIT_ALIASES.get(key, key): value for key, value in mapping.conversions.items()}
        if local_unit is None:
            unit_status, conversion, unit_score = "unit_missing", None, 0.3
        elif unit_key in conversions:
            unit_status, conversion, unit_score = "convertible", conversions[unit_key], 1.0
        else:
            unit_status, conversion, unit_score = "unit_needs_analyst", None, 0.0
        range_status, range_score = "not_checked", 0.5
        if conversion and (sample_min is not None or sample_max is not None):
            spec = SPECS[mapping.target]
            converted = [v * conversion[0] + conversion[1] for v in (sample_min, sample_max) if v is not None]
            inside = all(spec.minimum <= value <= spec.maximum for value in converted)
            range_status, range_score = ("plausible", 1.0) if inside else ("outside_plausible_range", 0.0)
        similarity = semantic.get(mapping.code) if semantic else None
        score = 0.45 * max(lexical, synonym) + 0.25 * fuzzy + 0.2 * unit_score + 0.1 * range_score
        if lexical == 0 and synonym == 0 and fuzzy < 0.2:
            if mapping.code not in vector_pool:
                continue
        else:
            lexical_evidence.add(mapping.code)
        ranked.append(
            Candidate(
                code=mapping.code,
                display=mapping.display,
                target=mapping.target,
                canonical_unit=mapping.canonical_unit,
                score=score,
                matched_terms=tuple(synonyms.get(mapping.target, [])),
                unit_status=unit_status,
                conversion=conversion,
                range_status=range_status,
                semantic=similarity,
            )
        )
    ranked.sort(key=lambda item: (-item.score, item.code))
    if vector_rank:
        evidence = [item.code for item in ranked if item.code in lexical_evidence]
        lexical_rrf = {code: 1 / (RRF_K + rank) for rank, code in enumerate(evidence)}
        ranked.sort(key=lambda item: (
            -(lexical_rrf.get(item.code, 0.0) + 1 / (RRF_K + vector_rank[item.code])), item.code
        ))
    return ranked[:k]


def deterministic_choice(candidates: list[Candidate]) -> str | None:
    """Without a model decision, recommend only on lexical evidence (score ≥ 0.5)."""
    best = max(candidates, key=lambda item: (item.score, item.code), default=None)
    return best.code if best is not None and best.score >= 0.5 else None


def cautions_for(local_display: str) -> list[str]:
    lowered = f" {_normalize_text(local_display)} "
    compact = lowered.replace(" ", "")
    return [text for term, text in CAUTIONS.items() if f" {term} " in lowered or compact == term.replace(" ", "")]


SYSTEM_PROMPT = (
    "You are an interface-analyst assistant for an ICU data-integration product. "
    "You map ONE local laboratory or vital-sign field to ONE candidate from a supplied list. "
    "Rules: choose only a code from the candidate list or 'none'; never invent codes, units or conversion factors; "
    "prefer 'none' when the local field is ambiguous; mention any specimen, method or unit ambiguity in cautions. "
    "You do not give clinical advice."
)

FEW_SHOT = [
    {
        "role": "user",
        "content": json.dumps({
            "local_field": {"code": "LAB-77", "display": "S. Creatinine", "unit": "mg/dL"},
            "candidates": [{"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma", "target": "Creatinine", "unit_status": "convertible"}],
        }),
    },
    {
        "role": "assistant",
        "content": json.dumps({"choice_code": "2160-0", "confidence": "high", "rationale": "'S.' denotes serum; unit mg/dL is accepted.", "cautions": []}),
    },
]


def _response_schema(codes: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "choice_code": {"type": "string", "enum": [*codes, "none"]},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "rationale": {"type": "string", "maxLength": 300},
            "cautions": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 4},
        },
        "required": ["choice_code", "confidence", "rationale", "cautions"],
    }


JSON_INSTRUCTION = (
    'Reply with only a JSON object: {"choice_code": "<candidate code or none>", '
    '"confidence": "low|medium|high", "rationale": "<one sentence>", "cautions": ["<text>"]}.'
)


def prompt_sha256() -> str:
    return hashlib.sha256(json.dumps([PROMPT_VERSION, SYSTEM_PROMPT, FEW_SHOT, JSON_INSTRUCTION]).encode()).hexdigest()


def _openai_bodies(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Most constrained request first, then progressively plainer ones for providers that reject a parameter.

    ``reasoning_effort: none`` keeps reasoning models from spending minutes thinking on a pick-one task;
    models without the parameter answer 400 and the next body omits it.
    """
    base = {"model": request["model"], "messages": request["messages"]}
    schema = {"type": "json_schema", "json_schema": {"name": "mapping_choice", "schema": request["format"]}}
    json_mode = {"type": "json_object"}
    return [
        {**base, "temperature": 0, "reasoning_effort": "none", "response_format": schema},
        {**base, "temperature": 0, "reasoning_effort": "none", "response_format": json_mode},
        {**base, "temperature": 0, "response_format": json_mode},
        base,
    ]


def _json_object(content: str) -> str:
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in model reply")
    return content[start : end + 1]


@lru_cache(maxsize=256)
def _ask_llm_cached(provider: str, url: str, model: str, payload: str) -> str:
    timeout = settings.copilot_llm_timeout_seconds
    if provider != "openai":
        response = httpx.post(f"{url.rstrip('/')}/api/chat", content=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["message"]["content"]
    bodies = _openai_bodies(json.loads(payload))
    for index, body in enumerate(bodies):
        response = httpx.post(f"{url.rstrip('/')}/chat/completions", json=body, headers=_headers(), timeout=timeout)
        if response.status_code in (400, 422) and index < len(bodies) - 1:
            continue
        response.raise_for_status()
        return _json_object(response.json()["choices"][0]["message"]["content"] or "")
    raise ValueError("unreachable")


def ask_llm(local_code: str, local_display: str, local_unit: str | None, candidates: list[Candidate]) -> dict[str, Any]:
    if not settings.copilot_llm_url:
        return {"status": "disabled", "detail": "COPILOT_LLM_URL is not configured; deterministic retrieval only."}
    endpoint = llm_endpoint()
    if _external_blocked():
        return {"status": "blocked", **endpoint,
                "detail": "The LLM endpoint is outside the hospital network and the site has not approved it "
                          "(COPILOT_EXTERNAL_LLM_APPROVED)."}
    if not candidates:
        return {"status": "skipped", "detail": "No retrieved candidates to choose from."}
    codes = [item.code for item in candidates]
    context = [
        {"code": c.code, "display": c.display, "target": c.target, "canonical_unit": c.canonical_unit,
         "unit_status": c.unit_status, "range_status": c.range_status}
        for c in candidates
    ]
    user = json.dumps({"local_field": {"code": local_code, "display": local_display, "unit": local_unit}, "candidates": context})
    system = SYSTEM_PROMPT if settings.copilot_llm_provider == "ollama" else f"{SYSTEM_PROMPT} {JSON_INSTRUCTION}"
    payload = json.dumps(
        {
            "model": settings.copilot_llm_model,
            "messages": [{"role": "system", "content": system}, *FEW_SHOT, {"role": "user", "content": user}],
            "format": _response_schema(codes),
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 2048},
        },
        sort_keys=True,
    )
    if LIMITER.hit("copilot-llm", "site", settings.copilot_llm_per_minute) is not None:
        return {"status": "rate_limited", **endpoint,
                "detail": "Model call budget for this minute is used up; deterministic retrieval shown."}
    try:
        content = _ask_llm_cached(settings.copilot_llm_provider, settings.copilot_llm_url, settings.copilot_llm_model, payload)
        answer = json.loads(content)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
        return {"status": "unavailable", **endpoint,
                "detail": f"Model did not return a usable answer ({type(error).__name__})."}
    if not isinstance(answer, dict):
        return {"status": "unavailable", **endpoint, "detail": "Model did not return a JSON object."}
    choice = answer.get("choice_code")
    if choice not in {*codes, "none"}:
        return {"status": "rejected", **endpoint,
                "detail": "Model answer was outside the retrieved candidates and was discarded."}
    return {
        "status": "ok",
        **endpoint,
        "model": settings.copilot_llm_model,
        "choice_code": choice,
        "confidence": answer.get("confidence"),
        "rationale": str(answer.get("rationale", ""))[:300],
        "cautions": [str(item)[:200] for item in answer.get("cautions", [])][:4],
    }


def suggest(
    registry: MappingRegistry,
    *,
    local_code: str,
    local_display: str,
    local_unit: str | None,
    sample_min: float | None,
    sample_max: float | None,
    use_llm: bool,
) -> dict[str, Any]:
    if looks_like_phi(local_code, local_display, local_unit):
        raise ValueError("Input looks like it contains identifiers or dates; submit field metadata only.")
    semantic, retrieval = semantic_scores(registry, local_display)
    candidates = retrieve(registry, local_display, local_unit, sample_min, sample_max, semantic=semantic)
    llm = ask_llm(local_code, local_display, local_unit, candidates) if use_llm else {"status": "not_requested"}
    recommended = None
    if llm.get("status") == "ok":
        recommended = None if llm["choice_code"] == "none" else llm["choice_code"]
    else:
        recommended = deterministic_choice(candidates)
    chosen = next((item for item in candidates if item.code == recommended), None)
    cautions = cautions_for(local_display)
    needs_confirmation = (
        chosen is None
        or bool(cautions)
        or chosen.unit_status != "convertible"
        or chosen.range_status == "outside_plausible_range"
        or llm.get("confidence") == "low"
    )
    patch = None
    if chosen and chosen.unit_status == "convertible" and local_unit is not None:
        patch = {"code": chosen.code, "add_unit_alias": local_unit, "conversion": [chosen.conversion[0], chosen.conversion[1]],
                 "local_source_code": local_code}
    return {
        "local_field": {"code": local_code, "display": local_display, "unit": local_unit,
                        "sample_range": [sample_min, sample_max]},
        "candidates": [item.as_dict() for item in candidates],
        "retrieval": retrieval,
        "recommended_code": recommended,
        "needs_analyst_confirmation": needs_confirmation,
        "cautions": cautions,
        "llm": llm,
        "proposed_registry_patch": patch,
        "registry": {"version": registry.version, "sha256": registry.sha256},
        "prompt": {"version": PROMPT_VERSION, "sha256": prompt_sha256()},
        "policy": "Proposal only. An interface analyst edits the registry; the new registry SHA must be re-verified "
                  "and signed off before any mapped data reaches scoring.",
    }
