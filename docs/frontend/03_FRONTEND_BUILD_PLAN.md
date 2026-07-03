# Frontend 03 - Build Plan

3 frontend engineers (F1, F2, F3) + 2 designers (D1, D2). Calendar dates match the backend plans - see root `README.md`. Frontend work is inherently dependent on backend views existing to style, so the first two days are design-system and infrastructure work that doesn't block on backend, and pairing with specific backend engineers ramps up from Day 3 onward.

## Days 0–1 (Wed–Thu 1–2 Jul) - Design system + tooling, no backend dependency yet
- **D1 + D2**: finalize the color palette, type scale, and component inventory (frontend `01_DESIGN_SYSTEM.md`) as actual Figma (or equivalent) mockups for: nav shell, patient profile page, a data table, the alert banner (3 severity states), the status badge, the login page. This is the visual reference everyone builds against - get it locked by end of Day 1, not iterated on for a week.
- **F1**: set up Tailwind CLI build pipeline, vendor HTMX/Alpine/idb/Chart.js per `02_FRONTEND_ARCHITECTURE.md` §2, wire the base `templates/base.html` shell + nav partial.
- **F2**: build the shared component partials (`_field.html`, `_status_badge.html`, `_alert_banner.html`, `_empty_state.html`) against D1/D2's mockups, as soon as those are available (even in-progress mockups - start with the button/badge/field components since those get locked first).
- **F3**: scaffold the service worker + IndexedDB outbox skeleton (`sw.js`, `app.js`) - this can be built and tested against dummy endpoints before real backend `syncapi` endpoints exist, per `02_FRONTEND_ARCHITECTURE.md` §4.

## Day 2 (Fri 3 Jul) - Pair up with backend as contracts freeze
- Engineer A's login/dashboard shell and Patient model freeze today - **F1 pairs with Engineer A** starting now on the login page and dashboard shell styling.
- **F2** continues component library, starts the patient registration form + search UI styling in tandem with Engineer A.
- **F3** continues offline infrastructure; reviews `syncapi` module spec (Engineer E) to align on the exact `client_uuid`/payload shape before Engineer E starts building it Day 6–7.

## Days 3–6 (Mon–Thu 6–9 Jul) - Pairing ramps up across all backend modules
Assign one frontend engineer as the primary pairing partner per backend engineer, rotating as needed based on where the critical path is that day - this isn't a rigid 1:1 for the whole sprint, it's a starting allocation:

- **F1 ↔ Engineer A** (patient profile shell, tabs, dashboard widget layout) and **Engineer B** (encounter form, vitals entry + trend chart) once A's shell is stable.
- **F2 ↔ Engineer C** (lab order/result UI, barcode display, imaging request safety-checklist UI) and **Engineer D** (prescribing form + safety-warning HTMX flow - this is a genuinely tricky interaction, budget real time for it).
- **F3 ↔ Engineer E** (billing UI, analytics dashboard layout, and critically the joint offline-sync session scheduled Day 7 per Engineer E's build plan).
- **D1 + D2**: continue producing mockups slightly ahead of the pairing schedule above (roughly 1–2 days ahead) so frontend engineers are never waiting on a design; also do a full accessibility/contrast pass on whatever's been built by Day 5.

## Days 7–9 (Fri 10 – Mon 13 Jul) - Integration, offline sync live, cross-page consistency
- **F3 + Engineer E**: wire the real offline outbox against live `/api/sync/submit/` and `/api/sync/status/` endpoints, test the full offline→reconnect→sync flow manually and with automated tests where feasible.
- **F1 + F2**: full visual consistency pass across every page built so far - this is where component drift gets caught and fixed (a button that got restyled ad-hoc in one backend engineer's PR, a table that doesn't match the design system table pattern, etc.).
- **D1 + D2**: usability pass - actually use the app end-to-end as if registering and treating a patient, note friction points, file them as small polish tickets rather than large redesign asks (there's no time budget for a redesign at this point).

## Days 10–13 (Tue 14 – Fri 17 Jul) - Bug bash, performance, docs
- Full-team bug bash (joins the backend bug bash from the root README timeline).
- Performance pass against the 150KB/page budget (design system §6) - measure real page weights, not estimates, on the "Slow 3G" DevTools throttle preset.
- Accessibility final check (contrast, keyboard nav, status badges never color-only).
- **D1 + D2**: prepare the visual materials for the final presentation/demo (§19.7 of brief) - this is a real deliverable, budget dedicated time for it, don't treat it as an afterthought after code freezes.

## Days 14+ - Demo prep and rehearsal
- Full team: rehearse the demo script end-to-end at least twice, including the offline-fallback moment (Engineer E's demo beat) and the patient-safety alert moments (Engineers B/C/D's demo beats) - the frontend team's job here is making sure every one of those moments is visually unambiguous to a judge watching from a few feet away, not just functionally correct.

## Standing rule for the whole sprint
No frontend engineer builds a new visual pattern without checking the component inventory first (design system §5). If it's genuinely missing, it gets added to the design system document and then built once, reused everywhere - never built inline in a single page's template "just for now." "Just for now" is exactly how visual inconsistency creeps in under time pressure, and Malawi Context Fit / professional tone is a scored criterion, not just aesthetic preference.
