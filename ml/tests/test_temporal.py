import numpy as np
import pytest

torch = pytest.importorskip("torch")

from predict_rx.temporal.data import HORIZONS, VARIABLES, augment, carry_forward, incident_targets  # noqa: E402
from predict_rx.temporal.models import build_model, load_organ_graph  # noqa: E402

N_STATIC = 10


def test_incident_targets_censor_post_onset():
    labels = np.array([0] * 10 + [1] * 10, dtype=np.int8)  # first positive at 10 -> onset 16
    targets = incident_targets(labels, np.array([0, 20]))
    six = targets[:, HORIZONS.index(6)]
    assert np.isnan(targets[16:]).all()
    assert six[9] == 0 and six[10] == 1 and six[15] == 1
    assert targets[15, HORIZONS.index(1)] == 1
    assert targets[14, HORIZONS.index(1)] == 0
    assert targets[4, HORIZONS.index(12)] == 1 and targets[3, HORIZONS.index(12)] == 0


def test_incident_targets_non_septic_all_zero():
    targets = incident_targets(np.zeros(8, dtype=np.int8), np.array([0, 8]))
    assert (targets == 0).all()


def test_carry_forward_values_and_delta():
    x = torch.zeros(1, 4, len(VARIABLES))
    m = torch.zeros(1, 4, len(VARIABLES), dtype=torch.bool)
    x[0, 1, 0], m[0, 1, 0] = 2.0, True
    x_last, ever, log_delta = carry_forward(x, m)
    assert x_last[0, :, 0].tolist() == [0.0, 2.0, 2.0, 2.0]
    assert ever[0, :, 0].tolist() == [0.0, 1.0, 1.0, 1.0]
    assert log_delta[0, 1, 0] == 0 and log_delta[0, 3, 0] > log_delta[0, 2, 0]


@pytest.mark.parametrize("kind,params", [
    ("graph_hazard", {"use_graph": True}),
    ("graph_hazard", {"use_graph": False}),
    ("grud", {}),
    ("tcn", {}),
])
def test_models_are_causal(kind, params):
    torch.manual_seed(0)
    model = build_model(kind, N_STATIC, params).eval()
    x = torch.randn(2, 12, len(VARIABLES))
    m = torch.rand(2, 12, len(VARIABLES)) > 0.5
    x = x * m
    static = torch.randn(2, N_STATIC)
    iculos = torch.arange(1, 13).float().repeat(2, 1)
    base = model(x, m, static, iculos)
    x2, m2 = x.clone(), m.clone()
    x2[:, 8:] = torch.randn(2, 4, len(VARIABLES))
    m2[:, 8:] = True
    changed = model(x2, m2, static, iculos)
    assert torch.allclose(base["challenge_logit"][:, :8], changed["challenge_logit"][:, :8], atol=1e-5)
    assert torch.allclose(base["hazard_prob"][:, :8], changed["hazard_prob"][:, :8], atol=1e-5)
    assert not torch.allclose(base["challenge_logit"][:, 8:], changed["challenge_logit"][:, 8:])


def test_hazard_heads_monotone_in_horizon():
    model = build_model("graph_hazard", N_STATIC, {}).eval()
    x = torch.zeros(1, 6, len(VARIABLES))
    m = torch.zeros(1, 6, len(VARIABLES), dtype=torch.bool)
    out = model(x, m, torch.zeros(1, N_STATIC), torch.arange(1, 7).float().unsqueeze(0))
    assert (out["hazard_prob"].diff(dim=-1) >= 0).all()


def test_augment_only_removes_or_delays_observations():
    generator = torch.Generator().manual_seed(1)
    m = torch.rand(4, 20, len(VARIABLES)) > 0.3
    x = torch.randn(4, 20, len(VARIABLES)) * m
    x_aug, m_aug = augment(x, m, generator, lab_drop=0.3, lab_group_drop=0.1, vital_mask=0.1, delay_fraction=0.0)
    assert not (m_aug & ~m).any()
    assert (x_aug[~m_aug] == 0).all()


def test_organ_graph_covers_every_variable_once():
    nodes, membership, adjacency, graph = load_organ_graph()
    assert membership.sum(0).eq(1).all()
    assert "care_process" in nodes and "context" in nodes
    assert adjacency.diagonal().all()
    assert graph["status"] == "curated-structure-not-causal"
