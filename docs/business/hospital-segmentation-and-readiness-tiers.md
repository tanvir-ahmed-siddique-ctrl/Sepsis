# Hospital segmentation and digital-readiness tiers

**Status:** Implemented in code as configurable attributes (`organization_size`, `readiness_tier`) on organisation profiles, opportunities and consultation self-reports.  
**Not:** A numerical maturity score. Checklist evidence lives on FDE readiness items.

## Separate attributes

| Attribute | Examples |
|---|---|
| Organisation size | clinic, small, medium, large, tertiary, academic, specialist, group |
| Site size / bed scope | per-site `bed_scope` on site profiles |
| Clinical units | free-text `units_summary` |
| Digital maturity / readiness tier | foundation, connected, advanced, unspecified |
| Infrastructure / device / IT workforce | readiness checklist items |
| Commercial capacity / support needs | relationship status + service plan fields |

Size ≠ readiness.

## Tiers

### Foundation
Limited IT, fragmented records, networking/server gaps, limited staffing. Services: assessment, planning, equipment compatibility review, foundational training. **No automatic clinical AI deployment.**

### Connected
Some digital systems, partial connectivity, identifiable gaps. Services: integration assessment, mapping, managed IT, clinical intelligence readiness assessment.

### Advanced
Established infrastructure, owners, governance pathways. Services: advanced integration, eligible local evaluation, managed ops, multi-unit coordination.

## Status progression

Readiness improves only through documented checklist evidence and authorized review (`not_started` → … → `approved` / `rejected`).
