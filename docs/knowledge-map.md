# Clinical evidence graph

The versioned graph is stored at `knowledge/evidence_graph.v1.json` and is
queryable through `GET /v1/evidence/features/{feature}`. It separates:

1. patient-specific model influence (grouped TreeSHAP),
2. curated clinical context,
3. model/data provenance, and
4. safeguard or review actions.

Every edge explicitly carries `causal: false`. This is **not** a diagnosis,
causal graph, or treatment engine. Unmapped model features fail open to a
curation request rather than receiving invented clinical context.

| Feature / derived | Organ / concept | Plain language |
|---|---|---|
| HR, shock_index | Cardiovascular | Heart rate relative to blood pressure |
| SBP, DBP, MAP, pulse_pressure | Cardiovascular | Blood pressure adequacy |
| Resp, O2Sat, FiO2, PaCO2 | Respiratory | Breathing effort / oxygenation |
| Temp | Systemic inflammation | Fever or hypothermia |
| WBC, Lactate | Infection / perfusion | White cells and tissue perfusion marker |
| Creatinine, BUN, bun_creatinine_ratio | Renal | Kidney function stress |
| Bilirubin_total, AST, Alkalinephos | Hepatic | Liver injury markers |
| Platelets, PTT, Fibrinogen | Coagulation | Clotting system stress |
| GCS-related (if present later) | Neurologic | Mental status |

Current provenance nodes cite the PhysioNet/CinC 2019 source and Sepsis-3
consensus context. Graph context never changes the ML score. The API validates
node references and rejects any edge that does not explicitly declare
`causal: false`.
