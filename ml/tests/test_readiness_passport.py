from predict_rx.readiness.passport import RecommendedMode, decide_mode, generate_passport


READY_SCHEMA = {
    "required_field_coverage": 0.99,
    "units_validated": True,
    "encounter_identity_validated": True,
}
METRICS = {
    "auroc": 0.8,
    "auprc": 0.1,
    "brier": 0.02,
    "calibration_slope": 0.95,
    "false_alerts_per_100h": 0.2,
}


def test_integrity_or_schema_failure_blocks_deployment():
    decision = decide_mode(
        {
            "integrity": {"critical_failures": ["invalid timestamps"]},
            "schema": READY_SCHEMA,
        }
    )
    assert decision.mode == RecommendedMode.do_not_deploy
    assert "critical_data_integrity_failures" in decision.blockers


def test_nonlocal_evidence_requires_local_retrospective_validation():
    passport = generate_passport(
        {
            "site_id": "public-site-held-out",
            "model_version": "frozen",
            "local_site_evidence": False,
            "integrity": {"critical_failures": []},
            "schema": READY_SCHEMA,
            "metrics": METRICS,
        }
    )
    assert passport["recommended_mode"] == "Retrospective validation"
    assert len(passport["evidence_sha256"]) == 64


def test_local_evidence_progresses_through_silent_then_controlled_gate():
    evidence = {
        "local_site_evidence": True,
        "integrity": {"critical_failures": []},
        "schema": READY_SCHEMA,
        "metrics": METRICS,
        "subgroup_evidence_complete": True,
        "failure_simulation_complete": True,
        "local_threshold_reviewed": True,
    }
    assert decide_mode(evidence).mode == RecommendedMode.silent_pilot

    evidence.update(
        {
            "silent_pilot_completed": True,
            "approvals": {"ethics_data_use": True, "clinical_owner": True},
            "prospective_protocol_defined": True,
        }
    )
    assert decide_mode(evidence).mode == RecommendedMode.controlled_pilot_candidate
