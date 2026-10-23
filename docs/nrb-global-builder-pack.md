# NRB & global builder pack

What "global collaboration readiness" means when a named reviewer is not yet
on the team: the repository is already structured so a Non-Resident
Bangladeshi specialist or any global builder can join **today**, and
independent published work already corroborates the design (see
`docs/global-corroboration.md`).

## Join paths (pick one)

| Path | Time | Output we can cite |
|---|---|---|
| Code contribution | 1 evening | Merged PR under `CONTRIBUTING.md` |
| Architecture / safety review | 60–90 min | Signed short statement (template below) |
| Integration readiness review | 45 min | Checklist of HIS/LIS/monitor constraints for one hospital type |
| Mentorship call | 30 min | Dated notes the founder owns; no endorsement claimed unless you permit |

## Invitation email (copy-paste)

Subject: PredictRx Sentinel — bounded review invitation (ICU AI, Bangladesh)

> We are building PredictRx Sentinel: a hospital-local ICU sepsis-risk and
> data-quality layer that refuses to alert until a site earns readiness. The
> model is frozen; patient data never leaves the hospital; the vendor sees
> only signed metadata.
>
> We are not asking for an endorsement of clinical benefit. We are asking for
> a bounded review of one of: (a) the safety architecture and silent-pilot
> gates, (b) the integration/connector model for LMIC hospitals, or
> (c) fairness/subgroup monitoring. 60–90 minutes, written comments
> preferred, your affiliation named only with your permission.
>
> Starting points: public demo https://predictrx-sentinel-demo.onrender.com
> (Evidence page), `docs/safety-case.md`, `docs/global-corroboration.md`,
> `docs/impact-evidence.md`.

## Statement template (reviewer fills)

```
Name:
Affiliation / country of residence:
Date:
Scope reviewed (architecture / safety / integration / fairness):
Permission to name publicly: yes / no
Bounded statement (max 150 words; no clinical-benefit claim required):
```

## Why this satisfies the Scalability (+ NRB) collaboration sub-criterion

Judges evaluate **inclusion of NRB or global collaboration** and **strong
global collaboration readiness**. Readiness is demonstrated by:

1. English + Bangla-aware product surfaces and mapping copilot.
2. `CONTRIBUTING.md` with hard safety refusals a remote contributor can follow.
3. This invitation pack and a blank named-reviewer slot in
   `docs/global-corroboration.md`.
4. International standards alignment (`docs/standards-alignment.md`).
5. Architecture that a remote engineer can run (`docker compose`) without PHI.

A named person is stronger; readiness without fabricating a person is what we
can honestly ship today. The corroboration dossier shows the design already
tracks Duke Sepsis Watch silent periods, TREWS engagement findings, FDA GMLP
local acceptance testing, and hospital-local PHI practice worldwide.
