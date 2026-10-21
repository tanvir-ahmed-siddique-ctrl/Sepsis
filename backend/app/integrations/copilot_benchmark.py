"""Labelled benchmark for mapping-copilot retrieval: lexical vs hybrid (keyword + vector).

Cases cover dictionary terms, Bangla script, misspellings, phrasings absent from
the synonym dictionary, and negative controls whose concept is not in the
registry (the correct behaviour is to recommend nothing).

Run: python -m app.integrations.copilot_benchmark            (lexical)
     COPILOT_LLM_URL=http://127.0.0.1:11434 COPILOT_EMBED_MODEL=qwen3-embedding:0.6b \
     python -m app.integrations.copilot_benchmark              (lexical and hybrid)
"""

from __future__ import annotations

import json

from app.core.config import settings
from app.integrations import copilot
from app.integrations.mapping import MappingRegistry

BENCHMARK_VERSION = "copilot-retrieval-bench/v1"

# (local display, local unit, expected registry target or None)
CASES: list[tuple[str, str | None, str | None]] = [
    ("S. Creatinine", "mg/dL", "Creatinine"),
    ("RBS", "mmol/L", "Glucose"),
    ("নাড়ি", "/min", "HR"),
    ("Hb%", "g/dL", "Hgb"),
    ("SGOT", "U/L", "AST"),
    ("TC (WBC)", None, "WBC"),
    ("Platelet count", None, "Platelets"),
    ("Serum Potassium", "mmol/L", "Potassium"),
    ("SpO2", "%", "O2Sat"),
    ("শরীরের তাপমাত্রা", "°F", "Temp"),
    ("হৃদস্পন্দন", "/min", "HR"),
    ("রক্তে শর্করা", "mmol/L", "Glucose"),
    ("শ্বাসের হার", "/min", "Resp"),
    ("অক্সিজেন স্যাচুরেশন", "%", "O2Sat"),
    ("রক্তের হিমোগ্লোবিন", "g/dL", "Hgb"),
    ("ক্রিয়েটিনিন", "mg/dL", "Creatinine"),
    ("পটাশিয়াম", "mmol/L", "Potassium"),
    ("ল্যাকটেট", "mmol/L", "Lactate"),
    ("প্লাটিলেট", None, "Platelets"),
    ("Thrombocyte count", None, "Platelets"),
    ("Leucocyte count", None, "WBC"),
    ("Lactic acid", "mmol/L", "Lactate"),
    ("Serum Kreatinin", "mg/dL", "Creatinine"),
    ("Pulse rate per minute", "/min", "HR"),
    ("Breathing rate", "/min", "Resp"),
    ("Sugar (random)", "mmol/L", "Glucose"),
    ("Arterial CO2 tension", "mmHg", "PaCO2"),
    ("Mean arterial pressure (invasive)", "mmHg", "MAP"),
    ("Body temp axillary", "°C", "Temp"),
    ("Cardiac troponin", "ng/mL", "TroponinI"),
    ("Systolic pressure", "mmHg", "SBP"),
    ("ESR", "mm/h", None),
    ("Blood group", None, None),
    ("Urine colour", None, None),
    ("Serum Sodium", "mmol/L", None),
    ("ALT (SGPT)", "U/L", None),
    ("HbA1c", "%", None),
]


def run(registry: MappingRegistry, hybrid: bool, llm: bool = False) -> dict:
    """Recall@5 measures retrieval; top-1 and abstention measure the final recommendation."""
    positives = top1 = recall5 = 0
    negatives = abstained = 0
    misses: list[dict] = []
    targets_by_code = {mapping.code: mapping.target for mapping in registry.entries.values()}
    for display, unit, expected in CASES:
        semantic = copilot.semantic_scores(registry, display)[0] if hybrid else None
        candidates = copilot.retrieve(registry, display, unit, semantic=semantic)
        if llm:
            answer = copilot.ask_llm("BENCH", display, unit, candidates)
            code = None if answer.get("status") != "ok" or answer["choice_code"] == "none" else answer["choice_code"]
        else:
            code = copilot.deterministic_choice(candidates)
        recommended = targets_by_code.get(code) if code else None
        if expected is None:
            negatives += 1
            abstained += recommended is None
            if recommended is not None:
                misses.append({"display": display, "expected": None, "got": recommended})
            continue
        positives += 1
        top1 += recommended == expected
        recall5 += expected in [item.target for item in candidates[:5]]
        if recommended != expected:
            misses.append({"display": display, "expected": expected, "got": recommended})
    return {
        "mode": ("hybrid" if hybrid else "lexical") + (" + LLM" if llm else " deterministic"),
        "recall_at_5": round(recall5 / positives, 3),
        "top1_accuracy": round(top1 / positives, 3),
        "negative_abstention": round(abstained / negatives, 3),
        "positives": positives,
        "negatives": negatives,
        "misses": misses,
    }


def main() -> None:
    settings.copilot_llm_per_minute = 10_000
    registry = MappingRegistry(settings.fhir_mapping_path)
    results = [run(registry, hybrid=False)]
    if settings.copilot_llm_url and settings.copilot_embed_model:
        results.append(run(registry, hybrid=True))
    if settings.copilot_llm_url:
        results.append(run(registry, hybrid=False, llm=True))
    if settings.copilot_llm_url and settings.copilot_embed_model:
        results.append(run(registry, hybrid=True, llm=True))
    print(json.dumps({"benchmark": BENCHMARK_VERSION, "registry_sha256": registry.sha256, "results": results},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
