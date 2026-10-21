from app.trustgate import TrustState, assess_prediction, data_availability_shift


FRESH = {"HR": 0, "SBP": 0, "MAP": 60, "O2Sat": 0}


def test_reliable_high_risk_prediction_can_alert():
    result = assess_prediction(
        probability=0.2,
        risk_band="high_risk",
        data_quality="ok",
        data_freshness_minutes=60,
        signal_freshness=FRESH,
        high_risk_threshold=0.08,
        perturbed_probabilities=[0.18, 0.12, 0.09],
    )
    assert result.state == TrustState.alert
    assert result.alert_stability == 1.0
    assert result.prediction_covered


def test_unstable_high_risk_prediction_routes_to_verification():
    result = assess_prediction(
        probability=0.09,
        risk_band="high_risk",
        data_quality="ok",
        data_freshness_minutes=60,
        signal_freshness=FRESH,
        high_risk_threshold=0.08,
        perturbed_probabilities=[0.07, 0.06, 0.09],
    )
    assert result.state == TrustState.verify_data
    assert result.alert_stability == 1 / 3
    assert "alert_unstable_under_perturbation" in result.reasons


def test_missing_history_and_severe_shift_abstain():
    no_history = assess_prediction(
        probability=None,
        risk_band="insufficient_data",
        data_quality="insufficient",
        data_freshness_minutes=None,
        signal_freshness={},
        high_risk_threshold=0.08,
    )
    assert no_history.state == TrustState.abstain
    assert not no_history.prediction_covered
    assert data_availability_shift({}) == 0.7

    stale = assess_prediction(
        probability=0.03,
        risk_band="watch",
        data_quality="stale_required_vitals",
        data_freshness_minutes=721,
        signal_freshness={name: 721 for name in FRESH},
        high_risk_threshold=0.08,
    )
    assert stale.state == TrustState.abstain


def test_single_model_disagreement_is_not_treated_as_validated_confidence():
    result = assess_prediction(
        probability=0.03,
        risk_band="watch",
        data_quality="ok",
        data_freshness_minutes=0,
        signal_freshness=FRESH,
        high_risk_threshold=0.08,
        disagreement=0.0,
        disagreement_validated=False,
    )
    assert result.state == TrustState.watch
    assert not result.disagreement_validated
