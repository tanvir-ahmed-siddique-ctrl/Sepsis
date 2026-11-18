# Hospital organisation & site profile specification

**Surface:** Vendor Control Plane (`/platform/partnership` + APIs). Not public. No fictitious customers.

## Hierarchy

Hospital Organisation → Site/Campus → Units (summary) → Members (existing memberships) → Integrations/deployments (existing) → Equipment records → FDE projects → Commercial records.

## Organisation profile fields (implemented)

display_name, organization_type, organization_size, readiness_tier, relationship_status, country, primary/clinical/IT/procurement owners, notes (vendor-only), sites list.

Relationship statuses: prospect → discovery → assessment → technical_feasibility → proposal → contracted → implementing → evaluating → governed_production → managed_services → suspended → closed.

## Site profile fields (implemented)

address, country, timezone, units_summary, bed_scope, site_owner, deployment_lead, environment_status, governance_state, service_plan, notes.

## Linked records (existing + new)

Commercial quotes/contracts/licences/invoices; tickets/SLA; documents; equipment_records; fde_projects + readiness checklist; education_events; partnership_plans (internal); proposals.

Full 28-section editorial layout is represented by these linked modules rather than one monolithic page. Empty states are valid.
