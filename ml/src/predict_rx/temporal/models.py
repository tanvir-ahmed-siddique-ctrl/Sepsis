"""Sentinel Graph-Hazard and temporal baselines.

All models are strictly causal: the output at hour t depends only on hours
<= t (carry-forward via cumulative max, per-hour graph layers, unidirectional
GRU, left-padded convolutions).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

from predict_rx.temporal.data import HORIZONS, MAX_HOURS, VARIABLES, carry_forward

ORGAN_GRAPH = Path(__file__).resolve().parents[4] / "knowledge" / "organ_graph.v1.json"


def load_organ_graph(path: Path = ORGAN_GRAPH) -> tuple[list[str], torch.Tensor, torch.Tensor, dict]:
    """Return node names, organ-variable membership [organs, V], and adjacency [N, N]."""
    graph = json.loads(path.read_text())
    organs = list(graph["organs"])
    nodes = organs + ["care_process", "context"]
    membership = torch.zeros(len(organs), len(VARIABLES), dtype=torch.bool)
    for o, organ in enumerate(organs):
        for variable in graph["organs"][organ]["variables"]:
            membership[o, VARIABLES.index(variable)] = True
    if (membership.sum(0) != 1).any():
        raise ValueError("Every variable must belong to exactly one organ node.")
    index = {name: i for i, name in enumerate(nodes)}
    adjacency = torch.eye(len(nodes), dtype=torch.bool)
    for edge in graph["edges"]:
        targets = nodes if edge["target"] == "*" else [edge["target"]]
        for target in targets:
            adjacency[index[target], index[edge["source"]]] = True
            if edge["target"] != "*":
                adjacency[index[edge["source"]], index[target]] = True
    return nodes, membership, adjacency, graph


class PerVariableProjection(nn.Module):
    """Separate small linear map per variable plus a variable identity embedding."""

    def __init__(self, n_var: int, n_in: int, d: int):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(n_var, n_in, d) / math.sqrt(n_in))
        self.bias = nn.Parameter(torch.zeros(n_var, d))
        self.identity = nn.Parameter(torch.randn(n_var, d) * 0.02)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return F.gelu(torch.einsum("btvi,vid->btvd", inputs, self.weight) + self.bias + self.identity)


class Heads(nn.Module):
    def __init__(self, d_hidden: int, n_var: int):
        super().__init__()
        self.challenge = nn.Linear(d_hidden, 1)
        self.hazard = nn.Linear(d_hidden, len(HORIZONS))
        self.reconstruct = nn.Linear(d_hidden, n_var)
        widths = torch.tensor([HORIZONS[0]] + [b - a for a, b in zip(HORIZONS[:-1], HORIZONS[1:])], dtype=torch.float32)
        self.register_buffer("widths", widths)

    def forward(self, h: torch.Tensor) -> dict[str, torch.Tensor]:
        rate = F.softplus(self.hazard(h)) * self.widths
        cumulative = torch.cumsum(rate, dim=-1)
        return {
            "challenge_logit": self.challenge(h).squeeze(-1),
            "hazard_prob": (1 - torch.exp(-cumulative)).clamp(1e-6, 1 - 1e-6),
            "reconstruction": self.reconstruct(h),
        }


def _context(static: torch.Tensor, iculos: torch.Tensor) -> torch.Tensor:
    horizon = iculos.shape[1]
    stay = (torch.log1p(iculos.clamp(min=0)) / math.log1p(MAX_HOURS)).unsqueeze(-1)
    return torch.cat([static.unsqueeze(1).expand(-1, horizon, -1), stay], dim=-1)


class GraphHazard(nn.Module):
    """Organ-graph, multi-horizon temporal model on sparse hourly events."""

    def __init__(self, n_static: int, *, d_token: int = 32, d_node: int = 64, d_hidden: int = 128,
                 graph_layers: int = 2, dropout: float = 0.2, use_graph: bool = True,
                 graph_path: Path = ORGAN_GRAPH):
        super().__init__()
        n_var = len(VARIABLES)
        self.use_graph = use_graph
        self.value_tokens = PerVariableProjection(n_var, 2, d_token)
        self.process_tokens = PerVariableProjection(n_var, 2, d_token)
        self.context = nn.Sequential(nn.Linear(n_static + 1, d_node), nn.GELU(), nn.Linear(d_node, d_node))
        self.care_query = nn.Parameter(torch.randn(2, d_token) * 0.1)
        self.care_out = nn.Linear(2 * d_token, d_node)
        if use_graph:
            nodes, membership, adjacency, _ = load_organ_graph(graph_path)
            self.node_names = nodes
            self.register_buffer("membership", membership)
            self.register_buffer("adjacency", adjacency)
            n_organs = membership.shape[0]
            self.organ_query = nn.Parameter(torch.randn(n_organs, d_token) * 0.1)
            self.organ_out = nn.Linear(d_token, d_node)
            self.layers = nn.ModuleList(GraphLayer(d_node, dropout) for _ in range(graph_layers))
            n_nodes = len(nodes)
        else:
            self.global_query = nn.Parameter(torch.randn(7, d_token) * 0.1)
            self.global_out = nn.Linear(d_token, d_node)
            n_nodes = 9
        self.readout = nn.Sequential(nn.Linear(n_nodes * d_node, d_hidden), nn.GELU(), nn.Dropout(dropout))
        self.gru = nn.GRU(d_hidden, d_hidden, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.heads = Heads(d_hidden, n_var)
        self.last_attention: torch.Tensor | None = None

    def encode(self, x, m, static, iculos) -> torch.Tensor:
        x_last, ever, log_delta = carry_forward(x, m)
        values = self.value_tokens(torch.stack([x_last, ever], dim=-1))
        process = self.process_tokens(torch.stack([m.float(), log_delta], dim=-1))
        care_scores = torch.softmax(torch.einsum("btvd,qd->btqv", process, self.care_query), dim=-1)
        care = self.care_out(torch.einsum("btqv,btvd->btqd", care_scores, process).flatten(-2))
        context = self.context(_context(static, iculos))
        if self.use_graph:
            scores = torch.einsum("btvd,od->btov", values, self.organ_query)
            scores = scores.masked_fill(~self.membership, float("-inf"))
            organs = self.organ_out(torch.einsum("btov,btvd->btod", torch.softmax(scores, dim=-1), values))
            nodes = torch.cat([organs, care.unsqueeze(2), context.unsqueeze(2)], dim=2)
            for layer in self.layers:
                nodes, attention = layer(nodes, self.adjacency)
            self.last_attention = attention.detach()
        else:
            scores = torch.softmax(torch.einsum("btvd,qd->btqv", values, self.global_query), dim=-1)
            pooled = self.global_out(torch.einsum("btqv,btvd->btqd", scores, values))
            nodes = torch.cat([pooled, care.unsqueeze(2), context.unsqueeze(2)], dim=2)
        h, _ = self.gru(self.readout(nodes.flatten(-2)))
        return self.dropout(h)

    def forward(self, x, m, static, iculos) -> dict[str, torch.Tensor]:
        return self.heads(self.encode(x, m, static, iculos))


class GraphLayer(nn.Module):
    """Attention restricted to curated organ edges (plus self loops)."""

    def __init__(self, d: int, dropout: float):
        super().__init__()
        self.q, self.k, self.v = nn.Linear(d, d), nn.Linear(d, d), nn.Linear(d, d)
        self.norm1, self.norm2 = nn.LayerNorm(d), nn.LayerNorm(d)
        self.ffn = nn.Sequential(nn.Linear(d, 2 * d), nn.GELU(), nn.Linear(2 * d, d))
        self.dropout = nn.Dropout(dropout)
        self.scale = 1 / math.sqrt(d)

    def forward(self, nodes: torch.Tensor, adjacency: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        scores = torch.einsum("btid,btjd->btij", self.q(nodes), self.k(nodes)) * self.scale
        attention = torch.softmax(scores.masked_fill(~adjacency, float("-inf")), dim=-1)
        nodes = self.norm1(nodes + self.dropout(torch.einsum("btij,btjd->btid", attention, self.v(nodes))))
        nodes = self.norm2(nodes + self.dropout(self.ffn(nodes)))
        return nodes, attention


class GRUDInput(nn.Module):
    """GRU-D-style baseline: learned per-variable input decay toward the training mean (0).

    Hidden-state decay is omitted because PhysioNet 2019 is already hourly; this
    is documented as the input-decay variant of GRU-D.
    """

    def __init__(self, n_static: int, *, d_hidden: int = 128, dropout: float = 0.2):
        super().__init__()
        n_var = len(VARIABLES)
        self.decay = nn.Parameter(torch.zeros(n_var))
        self.decay_bias = nn.Parameter(torch.zeros(n_var))
        self.gru = nn.GRU(3 * n_var + n_static + 1, d_hidden, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.heads = Heads(d_hidden, n_var)

    def forward(self, x, m, static, iculos):
        x_last, ever, log_delta = carry_forward(x, m)
        delta = torch.expm1(log_delta * math.log1p(MAX_HOURS))
        gamma = torch.exp(-F.relu(self.decay * delta + self.decay_bias))
        mf = m.float()
        x_hat = mf * x + (1 - mf) * gamma * x_last
        inputs = torch.cat([x_hat, mf, log_delta, _context(static, iculos)], dim=-1)
        h, _ = self.gru(inputs)
        return self.heads(self.dropout(h))


class CausalTCN(nn.Module):
    def __init__(self, n_static: int, *, channels: int = 96, levels: int = 5, dropout: float = 0.2):
        super().__init__()
        n_var = len(VARIABLES)
        self.input = nn.Linear(4 * n_var + n_static + 1, channels)
        self.convs = nn.ModuleList(
            nn.Conv1d(channels, channels, kernel_size=3, dilation=2**level) for level in range(levels)
        )
        self.dilations = [2**level for level in range(levels)]
        self.dropout = nn.Dropout(dropout)
        self.heads = Heads(channels, n_var)

    def forward(self, x, m, static, iculos):
        x_last, ever, log_delta = carry_forward(x, m)
        inputs = torch.cat([x_last, ever, m.float(), log_delta, _context(static, iculos)], dim=-1)
        h = self.input(inputs).transpose(1, 2)
        for conv, dilation in zip(self.convs, self.dilations):
            h = h + self.dropout(F.gelu(conv(F.pad(h, (2 * dilation, 0)))))
        return self.heads(h.transpose(1, 2))


def build_model(kind: str, n_static: int, params: dict) -> nn.Module:
    if kind == "graph_hazard":
        return GraphHazard(n_static, **params)
    if kind == "grud":
        return GRUDInput(n_static, **params)
    if kind == "tcn":
        return CausalTCN(n_static, **params)
    raise ValueError(f"Unknown temporal model: {kind}")
