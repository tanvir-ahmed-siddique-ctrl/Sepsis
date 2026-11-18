# Consultation and CRM workflow

**Implemented:** `POST /v1/public/consultations`, vendor list/patch, opportunities CRUD/stage changes, UI at `/contact` and `/platform/partnership`.  
**Not connected:** live calendar availability API.

## Public consultation

Collects institution, contact, role, location, hospital type, optional size/readiness, purpose, preferred windows, modality, consent. Honeypot + hourly email rate limit. Preferred times create **pending** requests — never shown as booked until vendor confirms.

## Vendor meeting management

Statuses: pending, assigned, confirmed, declined, rescheduled, completed, cancelled. Fields: owner, org/site, opportunity link, agenda, notes, next action, follow-up.

## Opportunity pipeline stages

`new_inquiry` → … → `governed_production` / `renewal_or_expansion`, plus `on_hold`, `not_qualified`, `closed_lost`.

Legacy commercial **leads** remain available in `/platform/commercial`. New hospital-oriented opportunities live in partnership workspace. Do not fabricate counts or forecasts.
