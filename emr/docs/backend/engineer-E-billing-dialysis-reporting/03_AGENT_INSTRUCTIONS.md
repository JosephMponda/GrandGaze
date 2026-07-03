# Engineer E — AI Agent Instructions

Read root `AGENTS.md` first. Scope: `apps/billing`, `apps/dialysis`, `apps/reporting`, `apps/interop`, `apps/syncapi`.

## Scope lock
`reporting.raise_alert()` is a shared utility used by four apps across three engineers — treat its function signature as a public contract from the moment it's published (end of Day 2). Do not change its signature after other engineers have integrated against it without a team-wide heads-up, same as any other frozen contract in this project. Do not build `dialysis` or `interop` before `billing` and `syncapi` acceptance criteria pass — an agent asked to "start on the dialysis module" mid-sprint should check the MVP status first and say so if MVP items are incomplete.

## Do not reinvent
- **Payment gateway integration**: `Payment.reference` is a string field for a mobile-money transaction reference — there is no real payment gateway integration in scope for this competition (no budget, no merchant account, no time). Do not attempt to integrate a live mobile money API; that would also violate the dependency-minimization mandate for an external paid service.
- **FHIR server**: `interop` is one read-only serializer endpoint, not a FHIR server implementation. Do not add a FHIR library (e.g. `fhir.resources`) unless it's genuinely faster than hand-writing the ~40-line serializer — if you do add it, it must go through the allowlist process and the justification must be "faster to build correctly," not "more standards-compliant," since full conformance isn't the goal here.
- **Background job scheduling**: the "missed dialysis session" flag and the analytics dashboard aggregation should run as normal request-time queries against seed/live data for MVP — do not introduce Celery/cron until root `AGENTS.md`'s explicit "week 2, only if scheduled" condition is met, and even then only for genuinely async work (not for something a well-indexed query can compute on page load).

## Non-negotiables specific to this module
- **`raise_alert()` must be genuinely called by every source that needs it** — vitals, labs, imaging, pharmacy. If you're implementing this function and it looks like only one app calls it, that's a signal the other engineers haven't wired their side yet, not that the function is done — chase it down in standup rather than closing the ticket.
- **Sync submissions must be idempotent by `client_uuid`**, full stop — this is what prevents a flaky connection from creating three copies of the same patient registration or vitals reading. Any code path that applies a `SyncSubmission` must check-then-apply inside a transaction, not apply-then-check.
- **Sync conflicts are never silently auto-resolved.** If an agent is asked to "just apply the newer one" for a conflicting submission, push back — clinical data conflicts need a human decision, logged, per root `AGENTS.md` §6. The one exception: a brand-new patient registration with no server-side counterpart yet has no possible conflict and can apply directly.
- **Billing amounts snapshot at time of billing** (`InvoiceLineItem.amount_mwk` stored, not recomputed from `ServiceCatalogItem.price_mwk` later) — a price change next month must not silently alter a historical invoice.
- Any UI copy or documentation describing `interop` or `dialysis` must state clearly what's implemented vs. what's future scope — see root `AGENTS.md` §8 for the interoperability posture. Do not let an agent's default helpfulness lead to overclaiming standards conformance in a README or demo script.

## When generating code, prefer
- One dispatch table (`form_type -> handler function`) in `syncapi/dispatch.py` mapping to each app's `services.py` create function, rather than a large if/elif chain — this makes it trivial to add a new offline-capable form type later without touching the core sync endpoint logic.
- Django `Sum`/`Count`/`F`/`ExpressionWrapper` ORM aggregations for the analytics dashboard rather than pulling all rows into Python and summing manually — this matters for performance once seed data grows, and it's the kind of thing a technical judge might ask about.

## Test expectations for every PR in this module
- `raise_alert()` unit test + at least one cross-app integration test proving another app's save() actually triggers it.
- Idempotent replay test: same `client_uuid` submitted twice → one record created, second call returns the first result.
- Conflict-detection test: a submission referencing a now-closed/signed encounter → `SyncConflict` created, not applied.
- Invoice balance correctness test across multiple line items and partial payments.
- Analytics dashboard test with one module's data intentionally "missing" → page still renders (graceful degradation, not a 500).
