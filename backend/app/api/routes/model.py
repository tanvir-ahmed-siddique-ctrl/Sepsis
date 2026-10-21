import json
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends

from app.auth import CLINICAL_ROLES, Actor, require_roles
from app.core.config import settings
from app.services.engine import get_engine
from predict_rx.readiness.passport import generate_passport

router = APIRouter(tags=["model"])
MODEL_EVIDENCE = require_roles(*CLINICAL_ROLES, "operator")


@router.get("/model")
def model_card(_: Actor = Depends(MODEL_EVIDENCE)):
    engine = get_engine()
    metrics_dir = Path(settings.metrics_dir)
    metrics = json.loads((metrics_dir / "metrics.json").read_text()) if (metrics_dir / "metrics.json").exists() else {}
    holdout_path = metrics_dir / "eval_holdout.json"
    holdout = json.loads(holdout_path.read_text()) if holdout_path.exists() else None
    reports = metrics.get("reports", {})
    return {
        "model_version": engine.model_version,
        "frozen": engine.frozen,
        "model_hash": engine.model_hash,
        "thresholds": engine.thresholds,
        "internal_test": {name: r["test"] for name, r in reports.items()},
        "validation": {name: r["val"] for name, r in reports.items()},
        "holdout_dataset_b": holdout,
        "subgroups_internal_test": metrics.get("subgroups_test"),
        "subgroups_holdout": None if holdout is None else holdout.get("subgroups"),
        "release_criteria_internal_test": metrics.get("release_criteria_internal_test"),
        "global_shap_top25": metrics.get("global_shap_top25"),
        "cpu_latency_ms_per_prediction": metrics.get("cpu_latency_ms_per_prediction"),
        "label_definition": (
            "Official Challenge-compatible SepsisLabel: positive from six hours before "
            "defined onset onward. Not an exact incident six-hour hazard probability."
        ),
        "validation_wording": (
            "Site-held-out retrospective validation on a geographically distinct public hospital cohort."
        ),
        "disclaimer": settings.disclaimer,
    }


@router.get("/model/passport")
def hospital_readiness_passport(_: Actor = Depends(MODEL_EVIDENCE)):
    evidence = yaml.safe_load(Path(settings.passport_evidence_path).read_text())
    passport = generate_passport(evidence)
    passport["source"] = settings.passport_evidence_path
    passport["local_site_evidence"] = bool(evidence.get("local_site_evidence", False))
    return passport
