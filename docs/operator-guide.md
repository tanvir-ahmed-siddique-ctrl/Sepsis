# Founder operator guide — PredictRx Sentinel

One document for the person who runs the company: what exists, how to run it,
how to put it online, how to install it at a hospital, how to keep it safe and
how to leave a hospital cleanly. Detailed runbooks are linked, not repeated.

## 1. Status in one paragraph

The software is a working, tested product foundation: ICU board, bedside
chart, alerts with ownership, handoff, NEWS2 ward board, integration hub (FHIR,
HL7 v2, CSV, edge relay), mapping copilot, silent-pilot evidence tools, site
setup, user management, audit chain, backups, metrics, fleet heartbeat and an
MCP server. The model is frozen Run 4, validated only retrospectively on public
data. **Not done and not claimable:** any hospital installation, Bangladesh
data, local validation, clinical approval, customers or revenue. The next
milestone is evidence, not features.

## 2. Project map

| Folder | What lives there |
|---|---|
| `backend/` | FastAPI API: engine, TrustGate, clinical-context policy, connectors, auth, audit, ops CLI |
| `frontend/` | Next.js app (all pages below) |
| `ml/` | Training, evaluation, frozen model registry (`ml/artifacts/models`) |
| `edge/` | On-site HL7 MLLP relay for monitor/LIS feeds |
| `control-plane/` | Vendor fleet console: receives signed, patient-free heartbeats |
| `mcp-server/` | Read-only MCP tools for operators and AI assistants |
| `infra/` | Dockerfiles, backup/restore scripts, Congress preflight, public-demo Caddyfile |
| `knowledge/` | Evidence graph, guideline registry, FHIR mapping registry |
| `demo/cases/` | 9 de-identified public PhysioNet 2019 Challenge records (CC BY 4.0) used for replay |
| `docs/` | Runbooks, model card, safety, business, submission answers |

| Page | Who uses it | What it gives |
|---|---|---|
| `/` | Nurse, doctor | ICU board: every bed, risk band, data trust state, freshness |
| `/patient/[id]` | Nurse, doctor | Trend, top drivers, data quality, clinical context the model cannot see |
| `/alerts` | Nurse, doctor | Alert queue: own, acknowledge, review, escalate |
| `/handoff` | Nurse, doctor | Structured shift handoff |
| `/chart` | Nurse | Admit/transfer/discharge, vitals and labs entry, offline queue, QR bed labels |
| `/ward` | Nurse | NEWS2 board for ward patients (not the sepsis model) |
| `/integration` | Admin, IT | Feed health, quarantine, mappings, Bangla/English mapping copilot, CSV upload |
| `/pilot` | Admin, governance | Adjudication, outcomes, shadow-alert burden, readiness gates, pseudonymised export |
| `/readiness` | Admin, buyer | Hospital readiness passport |
| `/model` | Everyone | Model card, frozen hash, evidence |
| `/operations` | Admin, operator | Writer lease, audit chain, metrics, fleet heartbeat payload |
| `/admin/setup` | Admin | Site setup checklist and silent-pilot gates |
| `/admin/users` | Admin | Users, roles, units, PIN/TOTP reset |
| `/docs` | Judges, buyers | Live module documentation and AI stack |
| `/presentation` | Founder | Pitch view |

Roles: `nurse`, `clinician`, `admin`, `operator` (vendor; metadata only, never
patient data) and `integration` (machine keys).

## 3. Run it on your laptop

```bash
docker compose up -d --build
python infra/congress_demo.py check      # must print CONGRESS PREFLIGHT PASSED
```

Open <http://localhost:3000>. Demo mode lets you switch role from the login
page. API docs: <http://localhost:8000/docs>. Optional LLM for the mapping
copilot, either on-premises (Ollama with `qwen3.5:4b` and
`qwen3-embedding:0.6b`) or any OpenAI-compatible API with a key (Gemini, Groq,
OpenRouter, OpenAI); see `.env.example`. Hospital sites default to
on-premises; an external API is refused outside demo mode until the hospital
sets `COPILOT_EXTERNAL_LLM_APPROVED=true`.

## 4. Get a live link (demo only, public de-identified data)

Never put hospital patient data on a public link. The public demo runs
`DEMO_MODE` with 9 de-identified PhysioNet 2019 Challenge records (CC BY 4.0)
and synthetic HL7/FHIR samples.

### Option A — free: one container on Render (recommended for the competition)

`infra/Dockerfile.demo` packs both sides of the product into one image:

- `/` — one simulated hospital installation (web app, API, frozen model,
  replay records). In real life every hospital runs this on its own server.
- `/fleet` — the vendor fleet console (`control-plane/`), read-only in the
  demo. The demo hospital pushes a signed, patient-free heartbeat to it every
  minute with a signing key generated at container start, exactly as a real
  site pushes outbound over the internet.

SQLite lives in `/tmp` and resets on every restart. Tested under the Render
free limits (0.1 CPU, 512 MB): about 255 MB RAM, ready about 2 minutes after
start, pages under 0.2 s once warm.

1. Create a free [Docker Hub](https://hub.docker.com) account and a **private**
   repository `predictrx-demo` (the free plan includes one private repository).
2. Build and push from the project folder:

   ```bash
   docker login
   docker build --platform linux/amd64 -f infra/Dockerfile.demo -t <dockerhub-user>/predictrx-demo:latest .
   docker push <dockerhub-user>/predictrx-demo:latest
   ```

3. In Docker Hub → Account settings → Personal access tokens, create a
   read-only token.
4. In [Render](https://dashboard.render.com): New → Web Service → Existing
   image → `docker.io/<dockerhub-user>/predictrx-demo:latest` → add registry
   credentials (Docker Hub user + token) → Instance type **Free** → Advanced:
   health check path `/api/health`. Render may ask for card verification; the
   free plan is not charged.
5. Render gives `https://<name>.onrender.com`. Open it, wait for the board,
   then use **Session → Demo sign-in** to switch role.
6. Free services sleep after 15 minutes idle; the first visit then takes
   about 3 minutes. During the judging window, add a free
   [UptimeRobot](https://uptimerobot.com) HTTP monitor on
   `https://<name>.onrender.com/api/health` every 5 minutes. One always-on
   service uses about 744 of the 750 free hours per month.
7. To update: rebuild, push, then Render → Manual deploy → Deploy latest
   reference.

8. Optional, to make the mapping copilot's LLM work on the public link: in
   Render → Environment add `COPILOT_LLM_PROVIDER=openai`,
   `COPILOT_LLM_URL=https://generativelanguage.googleapis.com/v1beta/openai`
   (or another OpenAI-compatible API), `COPILOT_LLM_MODEL=<model name from
   the provider>` and `COPILOT_LLM_API_KEY=<key>`, then redeploy. Only field
   names and units are sent; calls are capped at 30 per minute
   (`COPILOT_LLM_PER_MINUTE`), after which the copilot falls back to
   deterministic mode. Never put the key in the image or the repository.

Limits to say out loud: anyone with the link shares one demo state (rate
limits apply); a restart resets it; without step 8 the mapping copilot runs in
deterministic mode. The public image locks the operating mode to replay, so a
visitor cannot stop the shared case flow or request live mode. This lock is
only for the public demo; hospital sites keep audited administrator-controlled
mode changes.

### Option B — small cloud VM with your own domain

**What to copy to the server:** the repository, `ml/artifacts/models/` (about
10 MB, contains the frozen model) and `demo/cases/` (under 100 KB). Do not
copy `ml/artifacts/challengers/` (136 MB of experiments) or any dataset.

1. Rent a Linux VM with 2–4 vCPU and 4–8 GB RAM; install Docker.
2. Point a DNS `A` record (for example `demo.yourdomain.com`) to the VM.
3. Create `.env.demo`:

   ```bash
   POSTGRES_PASSWORD=<random>
   JWT_SECRET=<32+ random bytes>
   SITE_ADDRESS=demo.yourdomain.com
   DEMO_USER=judges
   DEMO_PASSWORD_HASH='<output of: docker run --rm caddy:2 caddy hash-password --plaintext "your-password">'
   ```

4. Start:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.public-demo.yml --env-file .env.demo up -d --build
   ```

Caddy obtains the HTTPS certificate automatically. Only ports 80/443 are open;
API and database are not reachable from the internet. Share the URL and the
password only with judges or investors. Reset the replay before each session.

### Option C — Cloudflare Tunnel from the laptop (no server, no domain)

Set `SITE_ADDRESS=:80` in `.env.demo`, start the same command, then run
`cloudflared tunnel --url http://localhost:80`. It prints a temporary
`https://…trycloudflare.com` URL. The link dies when the laptop sleeps, so use
it for a scheduled call, not for the judging window.

Why not Vercel/Netlify alone: the API is a stateful Python service with a
single-writer database lease; it needs a container host.

## 5. Your own setup as founder

1. **Company identity:** one founder email per role (support, security,
   billing). Turn on 2FA everywhere, use a password manager.
2. **Fleet console (your server):** run `control-plane/fleet_console.py` on
   your VM behind HTTPS. Per hospital add an entry in `sites.json` with its own
   `FLEET_SIGNING_KEY`. You see only versions, model hash, gate status, feed
   health and counts — never patient data. See `control-plane/README.md`.
3. **Your account at each hospital:** the hospital admin creates an `operator`
   account for you. It can read metadata pages only. Patient pages return 403.
4. **Release discipline:** tag every release; record the image digest and the
   model SHA-256 in the site deployment record.

### Who is who — how the system knows you

| Where | Who you are | How the identity is created |
|---|---|---|
| Public demo link | Anyone who opens it | No identity: **Demo sign-in** lets any visitor pick a role. It is a sandbox. |
| Your fleet console | Founder / vendor | `FLEET_CONSOLE_TOKEN` you set on your server; nobody else has it. |
| A hospital installation | Not you by default | At install, someone with server access runs `bootstrap-admin` once (it refuses when users exist). That account belongs to the **hospital's** IT or ICU admin. |
| Inside a hospital, as vendor | `operator` | The hospital admin creates your operator account in `/admin/users`; metadata only. |
| Doctors and nurses | `clinician`, `nurse` | The hospital admin creates them in `/admin/users`, or they sign in through the hospital's identity provider (OIDC). |

On a real site `DEMO_MODE=false`, so the demo role picker disappears and
every request needs a password, PIN or identity-provider token. The hospital
admin can remove your operator account at any time; that is deliberate.

To show the real sign-in flow in a video, run the site stack on the laptop
(section 6), run `bootstrap-admin` with a demo hospital-admin ID, sign in at
`/login` with it, change the temporary password, then create a nurse in
`/admin/users` and sign in as that nurse.

## 6. Installing at a hospital

The full checklist is in [hospital onboarding](hospital-onboarding.md) and the
[FDE playbook](business/fde-deployment-playbook.md). The short version:

**Before the visit (1–2 weeks):** signed pilot/readiness agreement and
data-processing agreement; named clinical, IT, privacy and governance owners;
ethics/IRB route; source inventory (HIS, LIS, monitors, paper); a server
ordered by the hospital.

**Server the hospital provides:** 4 vCPU, 16 GB RAM, 250 GB encrypted SSD,
UPS, Ubuntu LTS with Docker, inside the hospital LAN behind its reverse proxy.
Add 8 GB RAM if they want the on-premises mapping copilot LLM.

**Day 1 — install:**

```bash
cp .env.example .env.site   # fill every secret; never reuse demo values
docker compose -f docker-compose.yml -f docker-compose.site.yml --env-file .env.site up -d --build
docker compose ... exec api python -m app.ops_cli check-config
docker compose ... run --rm --no-deps api python -m app.ops_cli bootstrap-admin \
  --user-id site.admin --display-name "Site Administrator" --password '<temporary>'
```

The hospital admin then creates units, users (nurse, clinician, admin, and
your operator account) and one integration key per feed
(`ops_cli new-integration-key`).

**Days 2–5 — connect data:** HL7/FHIR from the interface engine, edge relay for
monitors, CSV for labs if nothing else exists, bedside chart for paper wards.
Map codes with the copilot; a human signs every mapping. Watch quarantine
until it is near zero for real reasons.

**Weeks 2–6+ — silent pilot:** scores are stored, not shown. Clinicians
adjudicate. The `/pilot` page tracks every readiness gate.

**What the hospital receives:** the installed system, admin training, nurse
quick-reference card (Bangla/English), the operations and onboarding runbooks,
signed mapping sheet, backup/restore drill record, incident contact sheet, and
at closeout the silent-pilot report.

## 7. Proof that the model runs on real data

| Question | Where to look |
|---|---|
| Is the model the frozen one? | `/model` and `/v1/ops/status` show SHA-256 `a7dcf5f4…532d`; the API refuses to start if `ACTIVE.json` and the file disagree |
| Is data arriving? | `/integration` feed health; metric `predictrx_feed_minutes_since_success` |
| Is the model scoring? | `predictrx_predictions_24h`, `predictrx_inference_total`; heartbeat `activity` counts in your fleet console |
| Is the data trustworthy? | TrustGate state per bed, quarantine rate, missing-vital drift metrics |
| Is it right? | Only the silent-pilot adjudication and local validation report can answer this |

## 8. Security model

**Not centralized.** Each hospital runs its own database, API and web app on
its own server. Patient data never leaves the hospital. Your fleet console
receives a signed, allowlisted heartbeat with counts only. If your console is
hacked, no patient data is exposed; if one hospital is hacked, other hospitals
are unaffected.

| Threat | Protection in the product | Hospital/company responsibility |
|---|---|---|
| Request flood / scripted client | Per-client budget (600/min), integration key budget (1,200/min), 429 with `Retry-After`, metric `predictrx_requests_rejected_total` | Reverse proxy connection limits, LAN-only exposure |
| Password guessing | 20 login attempts/min per address, 5-attempt account lockout for 15 min, TOTP, ward PIN sessions of 15 min | SSO where available |
| Huge uploads | Body over 12 MB rejected (413) before parsing; integration payloads capped at 10 MB | Proxy `client_max_body_size` |
| Model swap or tampering | Registry SHA-256 check at startup, artifacts mounted read-only, no training code path in production | Restrict server admin access |
| Audit log editing | Hash-chained audit; `verify-audit` and metric `predictrx_audit_chain_valid` | Alert on `0` |
| Stolen integration key | Keys are scoped to units and formats, stored as SHA-256 only, rotated per feed | Rotate after staff/vendor change |
| Insider misuse | Role and unit scopes; every action audited | Access reviews |
| Ransomware / server loss | Logical backups with checksum and audit-head hash; tested restore | Encrypted off-server backup copy |

**Backups (3-2-1):** `infra/backup.sh` writes to the `predictrx-backups`
volume nightly (cron). The hospital copies it to a second encrypted disk and
one offline/off-site medium it controls. Test a restore monthly. You, the
vendor, do not hold copies.

### If a hospital is attacked

1. Use the paper downtime process; PredictRx is decision support, care continues without it.
2. Isolate the server from the network; do not wipe it (evidence).
3. Hospital IT/security leads; you support. Check `verify-audit` and access logs.
4. Rotate every secret: JWT, integration keys, metrics token, fleet key, admin passwords.
5. Rebuild from clean images; restore the last backup whose audit chain verifies.
6. Breach notification is the hospital's duty as data controller under the
   Personal Data Protection Ordinance 2025; you provide facts within agreed hours.
7. Written post-incident review before scores are re-enabled.

### Founder safety

- Hold no patient data: smaller breach surface and less liability.
- Contracts state research/silent use, no clinical claims, hospital as data
  controller, limitation of liability, and incident cooperation.
- Professional/product liability and cyber insurance before the first paid site.
- Support access only when the hospital opens a session and logs it; no
  standing remote access or shared passwords.

## 9. Leaving a hospital, or closing the company

**Hospital offboarding** (data stays theirs, nothing left behind):

```bash
# 1. stop the API so nothing changes
docker compose ... stop api web
# 2. final backup -> hand to the hospital data controller
docker compose ... run --rm --no-deps api python -m app.ops_cli backup --out /app/backups/final.json.gz
# 3. erase and certify (refuses unless the backup matches the live database exactly)
docker compose ... run --rm --no-deps api python -m app.ops_cli decommission \
  --final-backup /app/backups/final.json.gz --confirm-site-id <SITE_ID> --certificate /app/backups/closeout.json
```

The certificate records the backup hashes, row counts erased, audit head at
closure and model hash. Then the hospital destroys the volumes and other
backup copies, revokes keys and removes proxy rules (the certificate lists
these steps). Remove the site from your fleet console.

**If the company stops:** give every customer at least 90 days' notice, a final
backup, the decommission procedure and the source code of their installed
release under the escrow/licence terms in the contract, so the hospital can keep
running or shut down safely without you.

## 10. Sizes

| Item | Size | Ships to a hospital? |
|---|---|---|
| Frozen model (`model.joblib`) | 1.9 MB | Yes (inside `ml/artifacts/models`, ~10 MB total) |
| Replay cases | < 100 KB | Demo only |
| Challenger experiments | 136 MB | No |
| Training datasets | large | Never |
| Optional copilot LLM (Qwen 3.5 4B + embedding) | a few GB | Only if the hospital wants it |

The model is small because it is a LightGBM tree model (7 leaves per tree,
isotonic calibration) over engineered features; there is nothing large to deploy.
