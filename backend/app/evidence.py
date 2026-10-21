"""Versioned, queryable evidence graph with explicit epistemic boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from predict_rx.explain import base_variable

from app.core.config import settings


class EvidenceGraph:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.graph = json.loads(self.path.read_text())
        self.nodes = {node["id"]: node for node in self.graph["nodes"]}
        self.edges = self.graph["edges"]
        unknown = {
            endpoint
            for edge in self.edges
            for endpoint in (edge["from"], edge["to"])
            if endpoint not in self.nodes
        }
        if unknown:
            raise ValueError(f"Evidence graph has unknown node references: {sorted(unknown)}")
        if any(edge.get("causal") is not False for edge in self.edges):
            raise ValueError("Every evidence edge must explicitly declare causal=false.")

    def _targets(self, node_id: str, relation: str | None = None) -> list[dict[str, Any]]:
        return [
            self.nodes[edge["to"]]
            for edge in self.edges
            if edge["from"] == node_id and (relation is None or edge["relation"] == relation)
        ]

    def query_feature(self, feature: str) -> dict[str, Any]:
        variable = base_variable(feature)
        observation = self.nodes.get(f"obs:{variable}")
        temporal_id = "change:trend" if feature != variable else "change:current"
        temporal = self.nodes[temporal_id]
        organs = self._targets(observation["id"], "curated_context") if observation else []
        concepts = [target for organ in organs for target in self._targets(organ["id"])]
        sources = {
            source["id"]: source
            for concept in concepts
            for source in self._targets(concept["id"], "evidence_context")
        }
        model_sources = self._targets("influence:treeshap", "model_provenance")
        safeguards = self._targets("influence:treeshap", "safeguard")
        for concept in concepts:
            safeguards.extend(self._targets(concept["id"], "safeguard"))
        return {
            "graph_id": self.graph["graph_id"],
            "graph_version": self.graph["version"],
            "feature": feature,
            "base_observation": observation,
            "mapped": observation is not None,
            "temporal_change": temporal,
            "model_influence": {
                "method": self.nodes["influence:treeshap"],
                "provenance": model_sources,
                "meaning": "Association with this model output; not a causal effect.",
            },
            "curated_clinical_context": {
                "organ_systems": organs,
                "dysfunction_concepts": concepts,
                "evidence_sources": list(sources.values()),
                "meaning": "Context for review; not diagnosis or treatment advice.",
            },
            "safeguards": safeguards,
            "unmapped_action": None if observation else "Show model influence only and request graph curation.",
            "disclaimer": "No path in this graph is a causal treatment recommendation.",
        }


_graph: EvidenceGraph | None = None


def get_evidence_graph() -> EvidenceGraph:
    global _graph
    if _graph is None:
        _graph = EvidenceGraph(settings.evidence_graph_path)
    return _graph
