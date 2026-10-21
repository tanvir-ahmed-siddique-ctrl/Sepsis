# PredictRx Sentinel — Full plan (evaluated)

See also: [docs/DECISIONS.md](docs/DECISIONS.md) and [docs/adoption-plan.md](docs/adoption-plan.md).

Locked V1:

1. Frozen LightGBM remains primary until a preregistered challenger beats it.
2. Graph-Hazard / GRU-D / TCN remain gated behind Dataset B baselines, data/target audit, and A-only tabular evidence.
3. Normalized JSON observations now; FHIR later.
4. Grouped TreeSHAP + versioned non-causal evidence graph; no RAG treatment assistant.
5. PhysioNet 2019 only for V1; MIMIC-IV does not block shipping.
6. SQLite local/offline persistence with PostgreSQL via `DATABASE_URL`.
7. TrustGate, failure simulator, and Hospital Readiness Passport are the product differentiators.
8. Direct public deploy, video, and slides are owned outside this implementation pass.
