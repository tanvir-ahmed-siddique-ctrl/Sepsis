# International standards alignment

"Principles-aligned with evidence" — never "certified" or "compliant" without
an independent certification body. Each row states what we implement and where
a judge can verify it.

| Standard / guidance | How PredictRx aligns | Verify |
|---|---|---|
| HL7 FHIR R4 | Bundle + Bulk NDJSON ingest; LOINC-coded observations; mapping registry with human sign-off | `/integration`, `POST /v1/integrations/fhir/bundle`, conformance run |
| HL7 v2.x | ORU observation ingest; ADT admit/transfer/discharge path; edge MLLP relay | `/integration`, `POST /v1/integrations/hl7v2/oru`, edge package |
| OpenAPI 3 | Live machine-readable API at `/api/openapi.json` | `/api-reference` |
| FDA/HC/MHRA GMLP (2021) | Independent train/test; Human–AI team focus (acknowledgement required); clear user information (model card, TrustGate reasons); local silent acceptance before live alerts; deployed monitoring hooks | `docs/model-card.md`, `/pilot`, `/readiness` |
| FDA ML transparency guidance | Local site acceptance path, performance monitoring plan, disclosed limitations and subgroup gaps | `docs/impact-evidence.md`, `docs/evidence/fairness-audit.md` |
| WHO AI for health ethics (2021) | Six principles mapped control-by-control | `docs/impact-evidence.md` §5 |
| IMDRF SBOM cybersecurity practice | CycloneDX SBOM for Python + web; vuln disposition with rescan | `docs/evidence/sbom-*.cdx.json`, `vulnerability-disposition.md` |
| Bangladesh PDPO 2025 framing | Hospital as controller; vendor holds no PHI; DPIA template for site install | `docs/data-protection-impact-assessment.md` |
| Software supply integrity | Release manifest: commit + model SHA + key-file hashes; rollback procedure | `docs/evidence/release-manifest.md` |

## Explicit non-claims

- Not FDA/CE/DGDA cleared or approved for clinical use.
- Not ISO 13485 / ISO 27001 / GDPR certified.
- Not a claim that alignment equals regulatory authorisation in any jurisdiction.
