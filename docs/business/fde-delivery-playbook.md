# FDE delivery playbook

**Implements / supersedes detail for:** earlier `docs/business/fde-deployment-playbook.md` operational narrative. Code: `fde_projects`, `readiness_checklist_items`, equipment, proposals.

## Project categories

site_readiness, infrastructure_improvement, equipment_connectivity, hospital_it_implementation, clinical_platform_integration, clinical_intelligence_evaluation, managed_technology_services.

## Statuses

planned, active, blocked, awaiting_hospital, completed, cancelled.

## Readiness passport

Default checklist keys (network, compute, storage, data sources, HIS/LIS, devices, interfaces, timestamp/units, sandbox, security, identity, privacy, clinical owners, procurement, staffing). States only — no score.

## Rules

- Do not enable interruptive clinical alerts solely because install succeeded.
- Do not expose connector secrets.
- Equipment is not operational until delivery/install/acceptance evidence.
- Planning timeline assumptions (1–2 weeks discovery, etc.) are templates, not SLAs.
