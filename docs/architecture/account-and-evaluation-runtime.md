# Auralis account and evaluation boundaries

The hospital FastAPI service remains the sole authority for clinical identities,
patient data and local workflows. Its local password authentication works without
the account service or an internet connection. The separate account service
(`control-plane/account_service.py`) owns vendor/customer identities, organizations,
sites, coded support tickets, registered deployment equipment and regulatory
coordination tasks. It has its own SQLite database and no clinical route or patient
table. The Next server keeps each service's opaque token in a separate HttpOnly,
SameSite=Strict cookie; every API still checks its own authorization and tenant.

## Local account service

The optional `docker-compose.accounts.yml` overlay starts the account authority
for local development. Set `ACCOUNT_API_INTERNAL_URL=http://accounts:8101` on the
web service. In a real installation, host vendor/customer accounts on separately
approved infrastructure and point the web server there; never copy the hospital
database into it. Bootstrap the first vendor user interactively:

```powershell
$env:ACCOUNT_DB = 'C:\approved\accounts.db'
python control-plane/account_service.py bootstrap-vendor --email operator@example.org --name 'Vendor operator'
```

The password prompt does not echo. Customer accounts are provisioned against an
existing organization and must rotate their initial password. There are no seeded
production customers, sites, assets, tickets or approvals. Account records use
database table creation on startup; schema migration and HA/backup procedures for
this new service still require commissioning before production.

## Isolated synthetic evaluation

Use `docker-compose.yml` plus `docker-compose.evaluation.yml` as a **separate
Compose project and host**. The overlay supplies distinct database, account,
case, backup and Caddy volumes. A seed job generates synthetic observations only;
the original de-identified research replay directory is not mounted. The frozen
model still scores each synthetic case, and the UI labels the source accurately.

Provide `EVAL_DB_PASSWORD`, `EVAL_JWT_SECRET`, `EVAL_HOSPITAL_PASSWORD`,
`EVAL_ACCOUNT_PASSWORD`, `EVAL_SITE_ADDRESS`, `EVAL_GATE_USER` and a Caddy
`EVAL_GATE_PASSWORD_HASH` through deployment secrets. Never commit their values.
The account service seeds only `evaluator@auralis.invalid`; its password comes
from `EVAL_ACCOUNT_PASSWORD`. Distribute access out of band. The HTTP basic gate
is an additional boundary, not a substitute for separate infrastructure.

`EVALUATION_RUNTIME=true` requires hospital `DEMO_MODE=true`,
`PUBLIC_DEMO_LOCKDOWN=true` and a dedicated hospital password. The legacy
demo-token endpoint stays disabled. The evaluator's account session can request
a hospital-local synthetic clinical session through the Next server. A different
customer account in the evaluation database does not get evaluator privilege.
Normal customer/vendor accounts cannot access the hospital clinical API through
their account token. Evaluation billing, notifications and release actions are
not present in this foundation, so no real-world side effect can be triggered.

Set `EVALUATION_SYSTEM_CHECK_URL` on the public site only after an isolated
HTTPS evaluation endpoint exists. The public sign-in exposes a small System Check
link; an unconfigured installation does not issue an evaluation role token.

## Verification and deployment limits

Unit/API tests verify account tenant isolation, vendor-only mutations, session
revocation, evaluator-only switching, synthetic seed generation, frozen-model
scoring of generated cases, and the locked-down demo-token boundary. Docker
Compose configuration and frontend build checks pass. A full container runtime
smoke test requires a running Docker daemon and a real HTTPS host. Local hospital
connector mapping, hospital SSO, clinical validation, regulatory approval and
offline failover drills require a commissioned hospital environment.
