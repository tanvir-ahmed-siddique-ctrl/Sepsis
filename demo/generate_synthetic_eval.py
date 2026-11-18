"""Create deterministic synthetic ICU replay records for an isolated evaluator site.

These records are constructed from formulas, not copied from a patient dataset.
They exercise product workflows and are never evidence of model performance.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

VITALS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp", "EtCO2"]
LABS = ["BaseExcess", "HCO3", "FiO2", "pH", "PaCO2", "SaO2", "AST", "BUN", "Alkalinephos", "Calcium", "Chloride", "Creatinine", "Bilirubin_direct", "Glucose", "Lactate", "Magnesium", "Phosphate", "Potassium", "Bilirubin_total", "TroponinI", "Hct", "Hgb", "PTT", "WBC", "Fibrinogen", "Platelets"]
DEMOGRAPHICS = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime", "ICULOS"]
FIELDS = VITALS + LABS + DEMOGRAPHICS + ["SepsisLabel"]


def generate(output: Path, count: int = 24) -> Path:
    if not 1 <= count <= 32:
        raise ValueError("Synthetic bed count must be 1–32")
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    for index in range(count):
        bed = f"EVAL-BED-{index + 1:02d}"
        scenario = index % 4
        hours = 18
        cases.append({"bed_id": bed, "kind": "synthetic_scenario", "hours": hours,
                      "labelled_onset_hour": None, "first_high_risk_hour": None, "replay_start_hour": 8})
        with (output / f"{bed}.psv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="|")
            writer.writeheader()
            for hour in range(1, hours + 1):
                phase = max(0, hour - 6) / 12
                wave = math.sin((hour + index) / 3)
                stress = phase * (0 if scenario == 0 else 1 if scenario == 1 else 2 if scenario == 2 else 3)
                row = {key: "NaN" for key in FIELDS}
                row.update({
                    "HR": round(76 + index % 8 + 12 * stress + 2 * wave, 1),
                    "O2Sat": round(max(87, 98 - 2.4 * stress - 0.4 * wave), 1),
                    "Temp": round(36.7 + 0.45 * stress + 0.1 * wave, 1),
                    "SBP": round(126 - 10 * stress + index % 4, 1),
                    "MAP": round(88 - 8 * stress + index % 3, 1),
                    "DBP": round(68 - 5 * stress, 1),
                    "Resp": round(16 + 3 * stress + wave, 1),
                    "Age": 39 + index % 28,
                    "Gender": index % 2,
                    "Unit1": 1,
                    "Unit2": 0,
                    "HospAdmTime": -0.5,
                    "ICULOS": hour,
                    "SepsisLabel": 0,
                })
                if hour in (1, 7, 13):
                    row.update({"Lactate": round(1.1 + 0.7 * stress, 2),
                                "WBC": round(7.4 + 2.0 * stress, 1),
                                "Creatinine": round(0.9 + 0.2 * stress, 2),
                                "Platelets": round(245 - 18 * stress),
                                "Bilirubin_total": round(0.8 + 0.12 * stress, 2)})
                writer.writerow(row)
    manifest = {"model_version": "synthetic-workflow-only",
                "source_split": "Deterministic synthetic records; no patient dataset or validation cohort",
                "selection_rule": "Fixed formula scenarios for interface and workflow review. No outcomes or performance claims.",
                "cases": cases}
    path = output / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=24)
    arguments = parser.parse_args()
    print(generate(arguments.output, arguments.count))
