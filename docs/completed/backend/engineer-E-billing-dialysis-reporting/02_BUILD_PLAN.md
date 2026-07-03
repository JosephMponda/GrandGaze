# Engineer E - Build Plan

You have the broadest scope and the least blocking dependency on other engineers (only `patients.Patient`), which is exactly why the ordering below matters - `reporting` unblocks three other engineers' patient-safety features, so it jumps the queue ahead of your own module's "main" feature (Billing).

## Days 0–1 (Wed–Thu 1–2 Jul) - `reporting` first, unblock the team
- Scaffold `apps/reporting`. `AlertEvent` model needs only `patients.Patient`, which is close to frozen by Engineer A already - don't wait for the full freeze, build against a stub if needed and swap it in.
- Implement and publish `raise_alert()` / `unacknowledged_alerts()` / `acknowledge()` by **end of Day 2** - this is the hardest deadline in the whole project because three other engineers (B, C, D) are blocked on it for graded patient-safety features. Treat slipping this as a same-day escalation, not a "catch up tomorrow" item.
- Also own the local Docker Compose fallback bundle mentioned in root `AGENTS.md` §2 - start it in parallel since it's infrastructure, not app logic, and doesn't block on anyone.

## Day 2 (Fri 3 Jul) - Local fallback + Docker bundle
- Finish `docker-compose.local.yml`: Django + gunicorn + Postgres + Redis + Nginx, fully offline-capable, documented `README-local-deploy.md` with exact commands ("this is what you run if venue Wi-Fi dies").
- Confirm `raise_alert()` published and acknowledged by B/C/D in standup.

## Days 3–4 (Mon–Tue 6–7 Jul) - Billing (the MVP item)
- `ServiceCatalogItem`, `Invoice`, `InvoiceLineItem`, `Payment` models + migrations, seed catalog.
- Invoice creation + line-item + payment recording views.
- Outstanding balance calculation, unpaid-bills view.

## Day 5 (Wed 8 Jul) - Analytics dashboard
- `/dashboard/analytics/` aggregating every module's `services.py` - this requires the other four engineers' `services.py` interfaces to at least exist with correct signatures, even if implementations are still being polished. Coordinate a specific time this day to pull in whatever's ready; don't block the whole dashboard on the single slowest module, degrade gracefully (show "data unavailable" for a module not yet ready rather than crashing the page).

## Days 6–7 (Thu–Fri 9–10 Jul) - `syncapi` (offline sync)
- `SyncSubmission`/`SyncConflict` models, `POST /api/sync/submit/` idempotent dispatch endpoint, `GET /api/sync/status/`.
- Coordinate directly with the frontend team here - this is the backend half of the offline-first feature described in `frontend/02_FRONTEND_ARCHITECTURE.md`, and it needs to be built and tested together, not in isolation. Schedule a joint session Day 7.

## Days 8–9 (Mon–Tue 13–14 Jul) - MVP hardening, then bonus scope if ahead of schedule
- Confirm all MVP acceptance criteria (billing, reporting, sync) pass before touching `interop` or `dialysis`.
- If ahead: `interop` FHIR-Bundle read-only endpoint (½ day, high bonus-point value for the effort).
- If further ahead: `dialysis` module - this is genuinely valuable (few competing teams will have chronic-care longitudinal tracking) but only after everything above is solid.

## Days 10–13 (Tue 14 – Fri 17 Jul) - Bug bash + docs
- Full integration bug bash - you're well placed to run this since your dashboard touches every module, use it as your integration test surface.
- Write the Billing, Reporting/Governance, Interoperability, and (if built) Dialysis sections of the System Design Document.
- Tests: idempotent sync replay, conflict detection, invoice balance correctness, alert dashboard correctness.

## Days 14+ - Demo prep
- Own the "offline fallback" demo beat: kill the internet connection live, show the app still working against the local Docker bundle, then reconnect and show queued submissions syncing. This is your single highest-value demo moment for Malawi Context Fit (15%) and Innovation (15%) - rehearse it enough times that it's boring to you by demo day.

## Dependencies you owe other engineers
- **End of Day 2 - hard deadline:** `raise_alert()` live. This blocks Engineers B, C, D's patient-safety features.
- **End of Day 5:** analytics dashboard degrades gracefully per-module rather than hard-failing if one module's `services.py` isn't ready yet.
