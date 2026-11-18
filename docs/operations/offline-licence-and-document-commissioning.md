# Offline licence and document commissioning

The Auralis vendor account service and hospital clinical API have separate data stores and keys. The vendor signs a contractual site licence with Ed25519. A hospital administrator imports the JSON package at `/app/admin/licence`; the clinical API verifies it against the local public key and `SITE_ID`. No vendor callback or patient data transfer is required.

## Key and deployment boundary

- Generate an Ed25519 signing key in approved vendor secret storage. Configure its raw 32-byte private key as base64 in `ACCOUNT_LICENCE_PRIVATE_KEY` and a non-secret identifier in `ACCOUNT_LICENCE_KEY_ID`. Never put this key in the hospital deployment, evaluation stack, source, or logs.
- Configure `LICENCE_PUBLIC_KEYS_JSON` on the hospital site as a JSON map of key ID to base64 raw 32-byte Ed25519 public key. `docker-compose.site.yml` requires this value and sets `LICENCE_REQUIRED=true`.
- The vendor issues a package only from a signed contract and a recorded licence. The customer downloads it from the Customer Portal; a hospital administrator imports it locally. The API stores the verified package and audits the import. The licence key ID supports planned key rotation by adding a new public key while retaining the old key for still-valid packages.
- The licence check applies to **new** live-mode requests. Expiry or loss of vendor connectivity does not erase records or automatically interrupt an already running bedside workflow. Clinical approval, local validation, data readiness, and live-mode gates remain separate. A licence is not a clinical authorization.
- Revocation while fully air-gapped cannot be instantaneous; an offline revocation/update procedure and contractual safety policy need institutional approval before production use.

## Commercial document scanning

`docker-compose.accounts.yml` runs the account service with a private ClamAV scanner service. Configure `ACCOUNT_DOCUMENT_KEY` as a Fernet key and `ACCOUNT_MFA_KEY` separately. The service sends each PDF to the scanner via INSTREAM before encrypting it in the account database. The scanner has no host-published port. Upload fails closed if the scanner is absent, errors, returns an indeterminate response, or detects malware. Only approved customer-visible documents can be downloaded by that organization's account.

The evaluation runtime has its own document key and accepts only synthetic evaluation documents. It does not issue real licences. Before production commissioning, the operator must verify signature updates, scanner availability, encrypted database backup/restore, key custody/rotation, PDF rendering, audit export, and access revocation on the actual infrastructure.

## Environment validation performed in repository

- Compose configuration parsing passes for site, account, and evaluation overlays with test-only values. This does not prove container startup.
- Unit/integration tests cover signed package tampering, cross-site rejection, local import, new-live gating, customer/vendor tenant scope, scanner INSTREAM clean/infected responses, and evaluation credential separation.
- A local engine startup test blocks outbound sockets while loading the frozen model in silent mode. This does not replace a hospital network-disconnection drill.

Actual hospital feeds, clinical validation, legal/regulatory review, and offline hardware/network drills remain external commissioning tasks. Do not mark these complete from a synthetic evaluation deployment.
