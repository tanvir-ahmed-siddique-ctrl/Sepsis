# Congress submission portal — ready-to-paste answers

Phase: **Idea to Unicorn — Preliminary Submission** (due 31 Oct 2026, 23:59 GMT+6).
Team: **theMergers**.

Rules used for every answer below:

- **TICK** = true in the current repository; a judge can verify it in code.
- **TICK ONLY IF YOU DID** = depends on what the team actually used during
  development; the repository cannot prove it.
- **DO NOT TICK** = not used. Ticking it would be a false claim that judges or
  investors can discover.

## Quick click sheet (AI Depth and Data Lifecycle)

| Portal section | Tick | Do not tick |
|---|---|---|
| Token optimization tools | Structured outputs / JSON mode; Sliding-window / context trimming | Provider caching, LLMLingua, Graphify, KV-cache, speculative decoding, batching |
| LLMs | Qwen; plus each assistant you really used (Claude, ChatGPT, Gemini…) | Anything not used |
| Retrieval & RAG | Naive RAG; Hybrid Search (Keyword + Vector); Knowledge Graph / Other Graph Methods | Vector DB, rerankers, Graph RAG, agentic/self/corrective RAG, HyDE |
| MCP | "We built and/or used MCP servers" | — |
| Frontend AI builders | Cursor Composer / Agent (+ others only if used) | — |
| Workflow automation | none | all |
| Local LLMs | Runtime: Ollama. Models: add "Qwen 3.5 4B" and "Qwen3-Embedding 0.6B" | Qwen 2/2.5 (wrong version) |
| Agentic frameworks | none | all |
| AI-DLC | AGENTS.md spec | Others unless adopted |
| /docs module | Yes | — |
| Data sources | Internal; Open Datasets; User Uploads / Bulk Import; IoT / Sensor / Streaming; Synthetic | Scraping, external APIs, partner data (until a real feed exists) |
| Acquisition | MCP servers; Bulk Upload; Automated Flows; API Pull / SDK integrations | Scrapers, AI extraction, RSS, email, OCR, speech |
| Formats | JSON, CSV, Parquet, YAML, JSONL, Markdown | PDF, XLSX, images, audio, video unless added |
| Storage | Relational | Vector DB (index is in-memory), NoSQL, object storage, warehouse |
| Visualization | Apache ECharts | Others unless used |
| Insights | Classical ML; Deep Learning; LLM Inference / RAG; Anomaly Detection; Rule Engine; Statistical Analysis | Forecasting, clustering |
| Tunneling | None (the live link is hosted on Render, not tunnelled); write "Render (Docker image)" if there is an Other field | Cloudflare/ngrok unless you really use them |

---

## Project info (required)

**Project Name**
PredictRx Sentinel

**Domain / Challenge**
HealthSphere AI → pick the challenge closest to ICU early warning, clinical
decision support or health-data interoperability.

**Elevator Pitch**
PredictRx Sentinel is a hospital-local ICU intelligence layer that connects
fragmented monitor, lab and chart data, shows what is missing, and makes
sepsis-risk AI earn the right to alert through local evidence and safety gates.

**Public Summary**
ICU teams in Bangladesh work across paper charts, monitors, lab systems and HIS
screens, and AI trained abroad can fail silently on that data. PredictRx
Sentinel runs inside the hospital: it ingests FHIR, HL7, lab CSV and bedside
charting; validates codes and units; scores six-hour sepsis risk with a frozen,
explainable model; and lets a TrustGate show, hold, or abstain. A local LLM
copilot helps map Bangla and Bangladeshi lab terms to international standards,
with human sign-off. Hospitals start with workflow and data-quality value; live
alerts stay off until nine readiness gates pass. Research prototype, not
approved for clinical use.

**Problem Statement — what problem does it solve?**
Sepsis is a leading cause of ICU death. Published Bangladesh ICU cohorts have
reported sepsis mortality near 47–49%, and public ICU capacity is scarce and
concentrated (DGHS listed 778 ICU beds across reporting public hospitals in
January 2024; reporting citing DGHS puts 55% of public ICU beds in Dhaka).
Deterioration is hard to see early because ICU data is fragmented across
paper, monitors, labs and hospital software, uses inconsistent local names and
units, and arrives late or incomplete. Imported early-warning AI makes this
worse when it silently scores on bad data or floods staff with false alerts.
Hospitals need trustworthy, connected ICU data first—and a safe way to test
whether AI works on their own patients before anyone relies on it.

**Solution Description — how does your solution work?**
1. Connect: FHIR R4, HL7 v2 ORU/ADT, lab CSV, native API, an edge relay for
   monitor HL7 over MLLP, and an offline bedside chart.
2. Validate: a versioned LOINC/unit registry converts units, rejects impossible
   values and quarantines unknown codes with full provenance and audit.
3. Map with AI help: a mapping copilot fuses keyword, trigram and synonym
   retrieval with on-premises Qwen3 embeddings, then an on-premises Qwen 3.5
   model (Ollama) proposes how local terms such as "S. Creatinine", "RBS" or
   "নাড়ি" map to LOINC; the model may only choose among retrieved candidates
   or answer "none", and an analyst signs off the registry SHA.
4. Predict and explain: a frozen LightGBM model scores six-hour sepsis risk
   from past-only temporal features; TreeSHAP shows the drivers in plain
   language; cited guideline context refuses treatment or dosing questions.
5. Govern: TrustGate turns a score into Alert, Watch, Verify data or Abstain.
   Sites run silently first; interruptive alerts are blocked until nine
   readiness gates pass.
6. Personalise safely: doctors document what the model cannot see (chronic
   kidney/liver/lung disease, immunosuppression, pregnancy, comfort care, rare
   conditions). A versioned policy labels chronic-baseline drivers, warns when a
   low score may be falsely reassuring, and keeps alerts shadow-only for comfort
   care or out-of-scope populations, without ever editing the probability.
   Entries expire, and context codes are logged for subgroup evaluation.
7. Operate: separate doctor, nurse, hospital-admin and metadata-only platform
   operator roles; hash-chained audit; backup/restore and certified
   offboarding; rate limits; Prometheus metrics; a
   read-only MCP server; and a vendor fleet console that receives only
   allowlisted, HMAC-signed, patient-free heartbeats from each hospital.

**Data & AI Provenance**
Model data: PhysioNet/CinC 2019 "Early Prediction of Sepsis from Clinical
Data" (CC BY 4.0), about 40,000 adult ICU stays from US hospitals. Dataset A was
split by patient (70/15/15, seed 42) for training, calibration and internal
test; geographically distinct Dataset B (19,978 patients) was scored once after
the model was frozen on 28 Sep 2026 (AUROC 0.808). The frozen model is verified
by SHA-256 at start-up. No Bangladeshi or identifiable patient data was used;
the model is not validated for Bangladesh. Integration tests use synthetic
messages. The mapping copilot runs Qwen 3.5 4B and Qwen3-Embedding 0.6B locally
through Ollama on field metadata only. It can instead use any OpenAI-compatible
API, which a hospital site must explicitly approve; even then only field names
and units are sent, never patient data. Its 37-case retrieval benchmark was written by the team and
is not an external validation. AI coding assistants were
used during development (see Tooling & IDE).

**Tooling & IDE**
Cursor IDE with Cursor Agent/Composer for AI-assisted development, code review
and browser verification through MCP; Python 3.11 (FastAPI, LightGBM,
scikit-learn, SHAP, PyTorch for rejected challengers); Next.js/React/TypeScript
with Tailwind and Apache ECharts; PostgreSQL; Docker Compose; Ollama for the
local LLM; pytest and Vitest for 220 automated tests.
(Add any other assistants the team really used, e.g. ChatGPT or Claude chat.)

**YouTube Video** — founder action
The live link shows the product; the video also shows the two things a free
public host cannot: the local LLM and a hospital-style installation. The portal
limits the video to 181 seconds, so record a **180-second** version on the
laptop with Ollama running (`COPILOT_LLM_URL` set):
1. Problem and claim boundary (0:00–0:18): fragmented ICU data and a research
   prototype that does not diagnose or prescribe.
2. `/presentation` replay (0:18–1:03): one held-out case, rising score,
   TreeSHAP drivers and TrustGate Watch/Verify/Abstain behaviour.
3. Integration plus AI (1:03–1:28): `/integration`, a FHIR/HL7 mapping and
   copilot suggestion for `S. Urea`; state that the hospital-local Qwen model
   sees field metadata only and a human signs every mapping.
4. Roles and scale (1:28–1:52): Nurse/Doctor workflow; Hospital-admin
   onboarding; then `/fleet` as the founder's patient-free multi-site view.
   State clearly that the public role picker is a simulator and real hospitals
   create named admin accounts locally.
5. Evidence, business and ask (1:52–3:00): `/readiness` or `/docs`, nine gates
   before alerts, paid readiness → one-ICU SafeLaunch → recurring operations,
   then ask for a Bangladesh design-partner hospital. Show the local
   installation commands only as a fast cut or terminal overlay; say no
   hospital is deployed yet.

**Demo / Live Links** — founder action
Submit the Render URL (see "Publishing the demo"). Suggested note for judges:

> Public demo of PredictRx Sentinel running in demo mode on 9 de-identified
> PhysioNet 2019 records and synthetic HL7/FHIR samples; no hospital data.
> `/` is one simulated hospital installation; use Session → Demo sign-in to
> switch between Nurse, Doctor, Hospital admin and Platform operator.
> `/judge-guide` explains the public-demo boundary, the real hospital account
> model and the founder control-plane view. The shared replay mode is locked
> on the public host, so a visitor cannot interrupt the case flow.
> `/fleet` is the vendor console, which sees every hospital only through
> signed, patient-free heartbeats. The free host sleeps when idle; the first
> load can take up to 3 minutes. In hospitals the mapping copilot uses a
> local LLM (Qwen 3.5 4B via Ollama) on the hospital's own server.
> [Pick one:] On this public host it uses <provider/model> through an
> OpenAI-compatible API, receiving field names and units only. / This free
> public host has no LLM, so the copilot runs in its deterministic mode.
> The video shows the local LLM and a simulated on-site installation.

Useful paths: `/judge-guide`, `/presentation`, `/`, `/integration`, `/pilot`,
`/fleet`, `/docs`, `/model`. Add the source repository link if the portal accepts one.
If you set a cloud key on Render, tick that model (for example Gemini) under
LLMs as well, since the product then really uses it.

---

## AI Detail Usage

**Prompt Usage**
The mapping copilot uses a versioned prompt (`mapping-copilot/v1`, SHA-256
recorded in every response and audit event): role prompting (interface-analyst
assistant, explicitly non-clinical), rule constraints (choose only from
retrieved candidates, prefer "none" when ambiguous, never invent codes or
conversion factors), and a one-shot example. Output is constrained by a JSON
schema whose `choice_code` enum is generated from the retrieved candidates.
Temperature 0. Prompt changes are versioned in code and covered by tests.

**Token Optimization**
Deterministic retrieval runs first, so the LLM is called only when requested
and receives only the top 5 candidates (a few hundred tokens) instead of the
registry. Context window capped at 2,048 tokens; thinking disabled; a 4B local
model instead of a large hosted model; JSON-schema structured output removes
parsing retries; identical requests and registry embeddings are served from an
in-process cache, so the registry is embedded once per registry version.

Tools / methods: **TICK** Structured outputs / JSON mode · **TICK**
Sliding-window / context trimming (top-k candidate pruning). Add custom:
"Local small model (Qwen 3.5 4B) + deterministic-first routing" and
"In-process response cache". **DO NOT TICK** provider prompt caching, LLMLingua,
Graphify, KV-cache reuse, speculative decoding or batching.

**LLMs / Models Used**
- **Qwen**: TICK (Qwen 3.5 4B chooses mappings and Qwen3-Embedding 0.6B powers
  vector retrieval; both run in the product via Ollama).
- Claude / ChatGPT / Gemini / others: **TICK ONLY IF YOU DID** use them during
  development, e.g. through Cursor or chat. Do not tick models you did not use.

How and why: Qwen 3.5 4B runs on hospital hardware, so no data leaves the
network and the copilot works offline; it handles Bangla and abbreviations well
enough to disambiguate retrieved candidates. The copilot is provider-agnostic:
the same constrained prompt runs on any OpenAI-compatible API (with automatic
fallback from JSON-schema to JSON mode), which hospitals must explicitly
approve and which the public demo can use when no local GPU/CPU is available. Coding assistants accelerated
development; every change was verified by tests.

**Retrieval & RAG**
- **TICK** Naive RAG (registry entries are embedded, retrieved and passed to
  the LLM, which generates a constrained choice and rationale).
- **TICK** Hybrid Search (Keyword + Vector): lexical ranking fused with
  Qwen3-Embedding cosine ranking by reciprocal-rank fusion.
- **TICK** Knowledge Graph / Other Graph Methods (versioned organ-system and
  evidence graphs map model drivers to organ context).
- **DO NOT TICK** Vector Database (the index is in memory), rerankers, Graph
  RAG, agentic/self/corrective RAG or HyDE.

RAG architecture details: sources are the versioned LOINC/unit mapping registry
(38 entries; one document per code, so no chunking is needed), a curated
Bangladesh and Bangla synonym dictionary, pitfall cautions (urea vs BUN, Hb%,
TCO2, SpO2 vs SaO2), and the clinical variable contract with plausible ranges.
Lexical retrieval scores keyword overlap, character trigrams, synonym hits,
unit convertibility and value-range plausibility. Vector retrieval embeds the
query with a task instruction and adds the three nearest registry entries.
Reciprocal-rank fusion orders the pool; the top 5 become the LLM context. On a
37-case internal benchmark (Bangla, abbreviations, misspellings, 6 unknown
concepts), hybrid retrieval raised recall@5 from 67.7% to 90.3%. A separate
versioned guideline registry provides cited context with treatment-query
refusal.

**MCP Usage — TICK "We built and/or used MCP servers"**
Built: `predictrx-sentinel` MCP server (`mcp-server/predictrx_mcp.py`, official
MCP Python SDK 2.3, stdio transport): 8 read-only tools (`site_health`,
`integration_status`, `readiness_gates`, `readiness_passport`, `model_card`,
`unmapped_source_codes`, `fleet_heartbeat`, `mapping_registry`) and 3 document
resources. It
authenticates as the metadata-only operator role, so patient data is refused
by the API. It is tested in the backend suite.
Used: Cursor's browser MCP server for automated UI verification during
development. Add others only if the team really used them.

**Open Source Tools & Libraries**
LightGBM (frozen risk model), scikit-learn (baselines, calibration, metrics),
SHAP (TreeSHAP explanations), PyTorch (GRU-D/TCN challengers, rejected),
CatBoost (tabular challenger), pandas/Polars/PyArrow/NumPy (feature pipeline),
FastAPI + Pydantic (API and validation), SQLAlchemy + Alembic + PostgreSQL
(storage and migrations), PyJWT/cryptography (auth), Next.js/React/TypeScript,
Tailwind CSS, Apache ECharts, Ollama + Qwen (local LLM), MCP Python SDK,
pytest and Vitest (tests), Docker.

**Agent Frameworks & Orchestration**
No autonomous agent is used in the product by design. The copilot is a fixed
pipeline: retrieval → constrained LLM call → schema and candidate validator →
human sign-off gate. The MCP server exposes tool calling to external
assistants. Development used Cursor Agent with sub-agents for parallel
exploration and verification. Do not tick LangGraph, CrewAI or similar.

**Fine-tuning / Adaptation**
Not applicable. No LLM is fine-tuned. Patient data is not used to adapt any
LLM. Skip.

**Evaluation & Quality Measurement**
Preregistered patient-level splits; frozen model scored once on held-out
Dataset B; AUROC, AUPRC, Brier, calibration error, Challenge utility,
alert-burden and warning-time metrics; subgroup and failure-case reports
including missed detections; negative-result experiment ledger. Copilot:
versioned 37-case benchmark (`copilot-retrieval-bench/v1`, results in
`docs/evaluation/`) measuring recall@5, top-1 and negative-control abstention
for lexical, hybrid, and hybrid + Qwen modes. Hybrid + Qwen reached 67.7%
top-1 against 54.8% for lexical + Qwen; all 6 unknown concepts abstained; the
only wrong pick was the ambiguous SpO2/SaO2 term, which now carries a caution.
A lexical regression floor runs in CI. Patient-context policy has its own unit
and API tests. Total: see Tooling & IDE.

**Guardrails, Safety & Privacy**
Copilot refuses identifier-like input; LLM answers outside retrieved candidates
are discarded; abstention ("none") is respected; conversion factors come only
from the curated registry; every suggestion is audit-logged with prompt and
registry hashes. Clinical side: TrustGate abstention, silent mode, nine
readiness gates before alerts, hash-chained audit, role separation, frozen
model, pseudonymised exports and treatment-query refusal. Patient-context
policy: chronic-baseline drivers are labelled rather than suppressed; comfort
care and out-of-scope populations get shadow-only alerts; entries expire so
suppression cannot persist silently. Privacy: the vendor fleet console accepts
only allowlisted, HMAC-signed, patient-free heartbeats. Abuse: per-client and
per-integration-key rate limits (429), login throttling plus account lockout,
oversized bodies rejected (413), and start-up refusal if the model file's
SHA-256 differs from the registry. Exit: a decommission command erases a site
only after proving the hospital holds a verified backup identical to the live
database, and issues a closeout certificate.

**Frontend AI / Visual App Builders**
**TICK** Cursor Composer / Agent. Others only if the team really used them.

**Workflow Automation**
**DO NOT TICK** any; none are used.

**Local / On-device LLMs**
Runtime: **TICK** Ollama. Models: add "Qwen 3.5 (4B)" and "Qwen3-Embedding
(0.6B)". The list shows Qwen 2/2.5; add the exact versions instead of ticking
the wrong one.

**Agentic Frameworks Used**
**DO NOT TICK** any.

**AI Development Lifecycle**
**TICK** AGENTS.md spec (repository `AGENTS.md` records invariants and checks
for AI agents). Process notes: locked decisions (`docs/DECISIONS.md`),
preregistered experiment ledger with review gates, frozen-artifact hashes,
test/build/preflight gates before release, and evidence-plan documents. Tick
"Cursor Rules + PRD workflow" only if you add Cursor rules.

**Live /docs module**
**TICK** "Yes". The app ships `/docs`: whitepaper, live API readiness, AI
component boundaries, safeguards, roles, business model and roadmap.

---

## Data Lifecycle & Engineering

**1. Data sources**: TICK Open Datasets (PhysioNet), Internal (own DB/app data:
bedside charting, handoff), User Uploads / Bulk Import (lab CSV), IoT / Sensor
/ Streaming (monitor HL7 through the MLLP edge relay), Synthetic data
(Synthea-style integration test payloads). Third-party/partner data: tick only
when a real hospital feed exists.

**2. Acquisition**: TICK Bulk Upload (CSV), Automated Flows (inbound FHIR and
HL7 webhook-style endpoints with idempotency keys), API Pull / SDK integrations
(FHIR R4 Bundle/NDJSON and HL7 v2 ADT/ORU through interface engines), MCP
servers for data access (read-only metadata). Do not tick scrapers, OCR,
speech-to-text or RSS.

**3. Formats**: JSON, JSONL (FHIR Bulk NDJSON), CSV, Parquet, YAML, Markdown;
add "HL7 v2 (pipe-delimited)". Parsers: custom HL7 v2 ORU/ADT parser, FHIR R4
Bundle/NDJSON mapper, CSV header-alias mapper. Cleaning: unit conversion,
range validation, timezone enforcement, deduplication, late-data revision,
quarantine. Schema validation: Pydantic models and the clinical variable
contract.

**4. Storage**: TICK Relational (PostgreSQL in deployment, SQLite for tests).

**5. Visualization**: TICK Apache ECharts; add Matplotlib/Seaborn (ML
reports). Dashboards: ICU overview, bedside chart, ward NEWS2, alerts,
handoff, silent-pilot metrics, integration hub, operations console, model
transparency, readiness passport.

**6. Insights**: TICK Classical ML (LightGBM, scikit-learn, CatBoost), Deep
Learning (PyTorch challengers, rejected), LLM inference (mapping copilot),
Anomaly detection (range/unit quarantine and input-shift detection), Rule
engine (NEWS2, TrustGate gates), Statistical analysis (calibration,
bootstrap, subgroup). Delivery: in-app risk timeline with explanations,
TrustGate state, handoff, alerts only when gates allow.

**7. Pipelines**: custom Python feature pipeline shared by training and
serving; replay scheduler; streaming via the edge MLLP relay with durable
queue, retry spool, circuit breaker and replay.

**8. Outbound**: REST API (FastAPI/OpenAPI), pseudonymised research exports,
Prometheus `/metrics`, MCP server, outbound HMAC-signed fleet heartbeat to the
vendor console; risk model served in-process on CPU; LLM and embeddings served
on-premises by Ollama.

**9. Open source stack**: same list as above.

**10. Quality and governance**: data quality—quarantine, provenance, feed lag
and coverage; privacy—on-premises data plane, role separation, pseudonymised
exports, retention, allowlisted patient-free fleet heartbeat; equity—context
subgroups logged with every prediction for subgroup evaluation; lineage—hash-chained audit, registry and model SHA-256;
cost/performance—CPU inference, small local LLM, deterministic-first copilot.

**Publish local environment to internet**: tick nothing unless you really use
a tunnel; the live link is a hosted container on Render. State that the public
demo runs in demo mode on public PhysioNet replay data and synthetic samples.

---

## Publishing the demo (needed for the required live link)

Demo mode contains no hospital data, but anyone can sign in with any demo
role, so the public instance must stay in demo mode on a separate host.

**Free, laptop off:** one container on Render's free plan, built from
`infra/Dockerfile.demo` and pushed to a private Docker Hub repository.
Step-by-step: `docs/operator-guide.md` section 4, Option A. Tested locally at
the free limits (0.1 CPU, 512 MB): about 190 MB RAM, ready in about 2 minutes,
Congress preflight passed. Keep it awake during judging with a free
UptimeRobot monitor on `/api/health`.

Before submitting:

```bash
python infra/congress_demo.py check --api https://<name>.onrender.com/api --web https://<name>.onrender.com
```

A paid VM (Option B) is only needed to put the LLM online; it is optional.
