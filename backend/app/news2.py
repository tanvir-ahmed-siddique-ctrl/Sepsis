"""NEWS2 (Royal College of Physicians, 2017) — published rule, not a trained model.

Ward patients are scored here and are never sent through the frozen ICU sepsis model.
Scores are withheld when a required parameter is missing; nothing is imputed.

Scale 2 (SpO2 88–92% on oxygen) is used only when the encounter is flagged as
confirmed or suspected hypercapnic respiratory failure. That flag is an explicit
clinician choice, not inferred from the data.
"""

from __future__ import annotations

from typing import Any

PARAMETERS = ("respiration_rate", "spo2", "on_oxygen", "systolic_bp", "heart_rate", "consciousness", "temperature")
AVPU = {"A": 0, "V": 3, "P": 3, "U": 3}


def _band(value: float | None, cuts: list[tuple[float | None, float | None, int]]) -> int | None:
    if value is None:
        return None
    for low, high, points in cuts:
        if (low is None or value >= low) and (high is None or value < high):
            return points
    return None


def respiration_score(rate: float | None) -> int | None:
    return _band(rate, [(None, 9, 3), (9, 12, 1), (12, 21, 0), (21, 25, 2), (25, None, 3)])


def spo2_scale1(spo2: float | None) -> int | None:
    return _band(spo2, [(None, 92, 3), (92, 94, 2), (94, 96, 1), (96, None, 0)])


def spo2_scale2(spo2: float | None, on_oxygen: bool | None) -> int | None:
    if spo2 is None or on_oxygen is None:
        return None
    if on_oxygen:
        return _band(spo2, [(None, 84, 3), (84, 86, 2), (86, 88, 1), (88, 93, 0), (93, 95, 1), (95, 97, 2), (97, None, 3)])
    return _band(spo2, [(None, 84, 3), (84, 86, 2), (86, 88, 1), (88, None, 0)])


def oxygen_score(on_oxygen: bool | None) -> int | None:
    if on_oxygen is None:
        return None
    return 2 if on_oxygen else 0


def sbp_score(sbp: float | None) -> int | None:
    return _band(sbp, [(None, 91, 3), (91, 101, 2), (101, 111, 1), (111, 220, 0), (220, None, 3)])


def heart_rate_score(rate: float | None) -> int | None:
    return _band(rate, [(None, 41, 3), (41, 51, 1), (51, 91, 0), (91, 111, 1), (111, 131, 2), (131, None, 3)])


def consciousness_score(avpu: str | None) -> int | None:
    if avpu is None:
        return None
    return AVPU.get(avpu.strip().upper()[:1])


def temperature_score(temp_c: float | None) -> int | None:
    return _band(temp_c, [(None, 35.1, 3), (35.1, 36.1, 1), (36.1, 38.1, 0), (38.1, 39.1, 1), (39.1, None, 2)])


def clinical_response(total: int, any_3: bool) -> dict[str, Any]:
    if total >= 7:
        return {
            "urgency": "emergency",
            "frequency_minutes": 15,
            "response": "Emergency assessment by a clinical team with critical-care competencies; consider transfer to a higher-care area.",
        }
    if total >= 5 or any_3:
        return {
            "urgency": "urgent",
            "frequency_minutes": 60,
            "response": "Urgent review by a clinician with acute-care competencies; minimum hourly observations.",
        }
    if total >= 1:
        return {
            "urgency": "low",
            "frequency_minutes": 240,
            "response": "Assessment by a registered nurse; increase frequency of observations to at least 4–6 hourly.",
        }
    return {
        "urgency": "routine",
        "frequency_minutes": 720,
        "response": "Continue routine monitoring at least 12-hourly.",
    }


def score(
    *,
    respiration_rate: float | None,
    spo2: float | None,
    on_oxygen: bool | None,
    systolic_bp: float | None,
    heart_rate: float | None,
    consciousness: str | None,
    temperature: float | None,
    scale: int = 1,
) -> dict[str, Any]:
    if scale not in {1, 2}:
        raise ValueError("NEWS2 scale must be 1 or 2")
    components = {
        "respiration_rate": respiration_score(respiration_rate),
        "spo2": spo2_scale2(spo2, on_oxygen) if scale == 2 else spo2_scale1(spo2),
        "air_or_oxygen": oxygen_score(on_oxygen),
        "systolic_bp": sbp_score(systolic_bp),
        "heart_rate": heart_rate_score(heart_rate),
        "consciousness": consciousness_score(consciousness),
        "temperature": temperature_score(temperature),
    }
    missing = [name for name, points in components.items() if points is None]
    complete = not missing
    total = sum(points or 0 for points in components.values()) if complete else None
    any_3 = any((points or 0) >= 3 for points in components.values()) if complete else False
    response = clinical_response(total, any_3) if complete else None
    return {
        "score": total,
        "complete": complete,
        "missing": missing,
        "scale": scale,
        "any_parameter_score_3": any_3,
        "components": components,
        "inputs": {
            "respiration_rate": respiration_rate,
            "spo2": spo2,
            "on_oxygen": on_oxygen,
            "systolic_bp": systolic_bp,
            "heart_rate": heart_rate,
            "consciousness": consciousness,
            "temperature": temperature,
        },
        "urgency": None if response is None else response["urgency"],
        "frequency_minutes": None if response is None else response["frequency_minutes"],
        "response": None if response is None else response["response"],
        "source": "RCP NEWS2 2017 — published clinical rule, not a trained model",
        "disclaimer": "NEWS2 is a published early-warning score. It is not a sepsis diagnosis and does not replace clinical judgment.",
    }
