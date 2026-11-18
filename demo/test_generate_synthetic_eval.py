import csv
import importlib.util
import json
from pathlib import Path


def test_synthetic_evaluation_fixture_has_no_patient_source(tmp_path):
    source = Path(__file__).with_name("generate_synthetic_eval.py")
    spec = importlib.util.spec_from_file_location("generate_synthetic_eval", source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = json.loads(module.generate(tmp_path).read_text())
    assert len(manifest["cases"]) == 24
    assert "synthetic" in manifest["source_split"].lower()
    assert all("source_patient" not in case and case["labelled_onset_hour"] is None for case in manifest["cases"])
    with (tmp_path / "EVAL-BED-01.psv").open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="|"))
    assert len(rows) == 18
    assert all(row["SepsisLabel"] == "0" for row in rows)
