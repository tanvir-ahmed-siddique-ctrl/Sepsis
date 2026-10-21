from app.core.config import settings
from app.evidence import EvidenceGraph


def test_evidence_graph_is_referentially_valid_and_noncausal():
    graph = EvidenceGraph(settings.evidence_graph_path)
    assert graph.graph["version"] == "1.0.0"
    assert all(edge["causal"] is False for edge in graph.edges)


def test_feature_query_separates_model_influence_from_clinical_context():
    result = EvidenceGraph(settings.evidence_graph_path).query_feature("Lactate_hours_since")
    assert result["mapped"]
    assert result["base_observation"]["id"] == "obs:Lactate"
    assert result["temporal_change"]["id"] == "change:trend"
    assert result["model_influence"]["provenance"]
    assert result["curated_clinical_context"]["evidence_sources"]
    assert "not a causal" in result["model_influence"]["meaning"]


def test_unmapped_features_fail_open_to_review_not_invented_context():
    result = EvidenceGraph(settings.evidence_graph_path).query_feature("unknown_feature")
    assert not result["mapped"]
    assert result["curated_clinical_context"]["organ_systems"] == []
    assert result["unmapped_action"]
