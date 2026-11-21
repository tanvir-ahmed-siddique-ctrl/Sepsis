# Auralis Co-pilot · local AI + optional BYO cloud LLM

> Research prototype — **not** approved for clinical use.  
> The co-pilot **never** writes sepsis probabilities. Frozen LightGBM Run 4 + TrustGate remain the only score path.

## Why this exists

Hospitals want:

1. **Bangla-friendly** charting help and mapping for local lab slang  
2. Optional **stronger cloud models** when the site approves egress  
3. A **medical assistant style** helper for workflow — without turning Auralis into an unregulated diagnostic chatbot  

## What we already ship

| Piece | Status | Path |
|-------|--------|------|
| Hybrid RAG (lexical + embeddings + RRF) | Implemented | `backend/app/integrations/copilot.py` |
| On-prem Ollama default (`qwen3.5:4b`) | Implemented (optional runtime) | `settings.copilot_llm_*` |
| OpenAI-compatible provider switch | Implemented (env / site config) | `copilot_llm_provider=openai` + URL + API key |
| External endpoint refusal unless approved | Implemented | `copilot_external_llm_approved` |
| Field-metadata-only prompts | Implemented | No full chart dump to LLM |
| EN ⇄ বাংলা UI chrome | Implemented | `frontend/lib/copy.ts` |

## Why we did **not** adopt n8n

- ICU edge needs **deterministic** connectors, idempotency, quarantine, and hash-chained audit  
- n8n is a general automation plane — easy to accidentally route PHI to SaaS nodes  
- Our integration passport already covers FHIR / HL7 / CSV / spool in-repo  
- Fewer moving parts on air-gapped or low-bandwidth hospital networks  

RAG **is** used — narrowly — for **terminology mapping**, not for open-ended diagnosis over the patient record.

## Language policy (Bangla + English clinical terms)

| Layer | Policy |
|-------|--------|
| Navigation, buttons, help text | User locale EN or বাংলা |
| Disease names, LOINC display names, drug classes | **English (Latin)** on clinical boards |
| Local aliases (নাড়ি, RBS, Hb%) | Accepted as **input**; mapped to English canonical codes |
| Audit / export | English codes primary; Bangla gloss optional |

This does **not** look unprofessional in Bangladesh ICU software — mixed Bangla UX + English medical tokens is the safe default.

## Co-pilot job list

### Allowed (assistive · proposal / draft only)

| Job | Behaviour | Human gate |
|-----|-----------|------------|
| **Mapping propose** | Bangla/local → LOINC candidates from retrieved set only | Analyst SHA sign-off |
| **Unmapped triage** | Explain why a code is quarantined | Clinical IT |
| **Handoff draft** | Summarize *already displayed* board fields into a draft note | Clinician edits/sends |
| **UI / protocol explain** | “What does TrustGate Verify mean?” from local docs | N/A (non-patient) |
| **Bangla UI paraphrase** | Rephrase chrome strings; not invent disease names | N/A |

### Forbidden

| Job | Reason |
|-----|--------|
| Change Run 4 score / thresholds | Safety + freeze policy |
| Diagnose / prescribe / “what antibiotic?” | Clinical device risk · not approved |
| Send full patient timeline to a public cloud by default | Privacy |
| Store API keys in `localStorage` / frontend bundle | Credential theft |
| Silent auto-apply mapping without sign-off | Governance |

## BYO cloud credentials — security model

```
Browser  --(HTTPS, session cookie)-->  Hospital API
                                         |
                                         +--> encrypted secret / env on local server
                                         |       (never returned in full to UI)
                                         +--> Ollama (default) OR approved OpenAI-compatible URL
```

Rules:

1. **Keys never persist in the frontend.** Profile UI may show `configured: true/false` and model name only.  
2. **Storage** = hospital-local process env or encrypted config table (same trust boundary as DB). Local DB is acceptable; browser storage is not.  
3. **Who can set keys** = clinical IT / admin / operator — not every clinician.  
4. **Egress** = denied unless `copilot_external_llm_approved` (or equivalent site gate).  
5. **Payload allowlist** = field names, units, short aliases, retrieved candidate codes — not free-text full notes with identifiers unless a future DPIA says otherwise.  
6. **Audit** = every external LLM call logs actor, purpose, host, prompt version — no secret key in logs.  
7. **Fallback** = if cloud fails, deterministic retrieval still works.

## Profile → “Auralis AI”

- **Clinician view:** capabilities, language policy, “does not diagnose,” link to mapping hub  
- **Admin / IT view:** points to site LLM settings (env or future encrypted store); never pastes keys into a public demo screenshot  

## Roadmap (not claimed done)

1. Encrypted site-secret CRUD API (admin-only) replacing raw env for BYO keys  
2. Handoff-draft endpoint with the same allowlist discipline as mapping  
3. Richer Bangla chrome strings without translating LOINC  
4. Optional local-only “ask the docs” RAG over `docs/` — still no chart diagnosis  

## Related

- [EXPERIMENT_MATRIX](EXPERIMENT_MATRIX.md) — Qwen is not the sepsis model  
- [trustgate-layers](trustgate-layers.md)  
- [safety-ethics](safety-ethics.md)  
- Mapping UI: `frontend/components/MappingCopilot.tsx`
