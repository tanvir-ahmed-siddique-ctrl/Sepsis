# Auri AI · local co-pilot + vendor-bundled cloud assist

> Research prototype — **not** approved for clinical use.  
> **Auri AI never writes sepsis probabilities.** Frozen LightGBM Run 4 + TrustGate remain the only score path.

Brand: **Auri AI** (product page `/aurie`, Profile tab, Hospital setup). Same assistant formerly described as mapping copilot / Aurie.

---

## Can we implement this? — Yes (phased)

| Phase | What | Status |
|-------|------|--------|
| **P0** | Local Qwen / Ollama + hybrid RAG mapping; EN⇄বাংলা Language dropdown; medical terms stay English | **Shipped** |
| **P1** | Admin stores optional LLM URL + API key encrypted on **hospital-local** DB; UI never reads key back | **Shipped** (`GET/PUT /v1/site/auri-ai`, Hospital setup panel) |
| **P2** | Handoff draft + “explain TrustGate” chat over allowlisted fields/docs | Roadmap |
| **P3** | Vendor console pushes **licence-bundled** model entitlement (hospital still runs Auri locally; key material delivered offline / FDE) | Roadmap |

---

## Commercial model (how money works without looking like a weird bolt-on)

Hospitals buy **Auralis enablement** (Discover → Bridge → Silent eval → Licence → Managed Edge).

**Auri AI cloud assist** is not sold as “buy ChatGPT from us separately.” It is:

1. **Included in the site deal** when the quotation says so (professional services / annual licence line: “Auri AI cloud assist entitlement”).  
2. Auralis (vendor) provisions the **approved OpenAI-compatible credential** during FDE / admin setup — or the hospital brings its own key.  
3. The key lives **only on that hospital’s local server** (encrypted config). Browser / demo screenshots never hold it.  
4. Usage stays inside **that site’s Auri jobs** (mapping, explain, drafts). No free-range access to other hospitals’ data, no sepsis re-scoring, no auto-orders.

So the taka is **bundled into the deal** (implementation + licence), not a confusing consumer API marketplace. Internally you still track cloud COGS; publicly it reads as “assistant included in the clinical system.”

---

## What Auri AI does (now + next)

### Does now

| Job | Notes |
|-----|--------|
| Mapping propose | Bangla/local → LOINC from retrieved candidates only |
| Hybrid RAG | Lexical + embeddings + RRF |
| Local LLM | Ollama `qwen3.5:4b` default |
| Cloud LLM (optional) | OpenAI-compatible URL + key on local server |
| Language chrome | Header **Language** dropdown · English / বাংলা |

### Add next (same security envelope)

| Job | Notes |
|-----|--------|
| Handoff draft | From fields already on the board |
| Protocol / TrustGate explain | Local docs + allowlisted glossary |
| Unmapped triage helper | Why quarantine fired |

### Never

Diagnosis · prescribe · change Run 4 · dump full identifiable charts to public cloud by default · store keys in `localStorage`.

---

## Security architecture

```
Clinician browser  --session-->  Hospital API
                                    |
                                    +--> encrypted auri_ai_llm config (local DB)
                                    +--> Ollama on LAN  OR  approved cloud API
                                    |
                                    X--> no path into Run 4 scorer
```

- **Admin / clinical IT** configure via Hospital setup (`AuriAiAdminPanel`).  
- **GET `/v1/site/auri-ai`** returns status only (`has_api_key`, model, host) — never the secret.  
- **Public demo** refuses ingesting customer cloud keys (`public_demo_lockdown`).  
- External hosts need `external_approved` (same spirit as `COPILOT_EXTERNAL_LLM_APPROVED`).

Local DB storage is **fine** (same trust boundary as the clinical DB). Frontend storage is **not**.

---

## Language policy

| Surface | Language |
|---------|----------|
| Menus, buttons, help | English or বাংলা (dropdown) |
| Disease names, LOINC, drug classes | **English** |
| Local slang input | Bangla/English aliases → English codes |

---

## Why not n8n?

Deterministic hospital connectors + quarantine + audit already live in-repo. n8n adds PHI egress risk and another ops plane. RAG **is** used — for mapping only.

---

## Operator pointers

- Profile → **Auri AI** (clinician view)  
- `/app/admin/setup` → **Auri AI · site assistant runtime** (admin)  
- Marketing → `/aurie`  
- Code → `backend/app/auri.py`, `backend/app/integrations/copilot.py`
