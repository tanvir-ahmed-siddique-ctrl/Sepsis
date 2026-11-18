# Role → navigation matrix (account surfaces)

| Role | Primary nav |
|---|---|
| root_admin / platform_admin | `/platform/accounts`, commercial, partnership, service, documents |
| deployment_engineer | partnership (FDE/readiness/equipment), service, documents |
| finance_legal | commercial, partnership proposals/pricing assumptions, documents |
| support_engineer | service tickets, limited org/site read |
| security_compliance | compliance, audit, offboarding |
| customer_owner | `/portal/*` org/commercial/service/documents |
| Hospital admin/clinician/nurse/clinical_it/clinical_viewer | `/app/*` per hospital role guards |

Vendor commercial users do not receive clinical patient-data access via account APIs.
