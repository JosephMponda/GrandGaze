# AGENTS.md — MUST–GSL EMR Innovation Challenge

Read this file before writing a single line of code. It applies to every human engineer and every AI coding agent (Claude Code, Codex, or anything else) working on this repository. It is tool-agnostic: nothing here assumes one AI product over another.

## 1. What we are building and why this doc exists

A modular, low-resource EMR prototype for the future MUST Teaching Hospital, judged on: Clinical Relevance (20%), Patient Safety (20%), Innovation (15%), Technical Design (15%), Malawi Context Fit (15%), Sustainability (15%). We have ~16 engineering days. The single biggest risk is **not technology risk, it's scope risk** — five backend engineers and three frontend engineers each independently deciding to "improve" the architecture. This file exists to remove that decision from the table so agents spend tokens on features, not on re-litigating the stack.

## 2. Stack — decided, not up for debate

| Layer | Choice | Why |
|---|---|---|
| Backend framework | **Django 5.x** (LTS) | Team's strongest skill. Batteries: auth, admin, ORM, migrations, forms, sessions, CSRF — all judged requirements (9.3, 9.4) come near-free. |
| API layer | **Django REST Framework**, used *only* for: offline-sync endpoints, FHIR-lite interop export, dashboard JSON/chart data | We are not building a full parallel API for a server-rendered app. Every extra endpoint is extra attack surface and extra time. |
| Database | **PostgreSQL 16** | JSONB for flexible/FHIR-shaped resources, row-level constraints, mature encryption story, free-tier available (Neon), trivially self-hostable for the local-fallback story required in brief §10. |
| Cache / session store / Celery broker | **Redis** | Free tier (Upstash) or local Docker container. |
| Background jobs | **Celery + Redis**, added only in week 2 if capacity allows (report generation, "SMS reminder concept"). Not required for MVP — do not build this on day 1. |
| Frontend rendering | **Django Templates + HTMX + Alpine.js + Tailwind CSS (CLI, not full Node build)** | See §3. This is the single highest-leverage decision in this document — read it. |
| Auth | **Django's built-in `django.contrib.auth`** (sessions, not JWT) + Groups/Permissions for RBAC. `django-axes` for lockout on repeated failed logins. | Section 9.4 requirements (secure login, RBAC, session timeout, failed-login tracking) are satisfied by configuration, not custom code. |
| Audit trail | **`django-simple-history`** on every clinical/PHI model | Satisfies §8.1.19, §9.1, §9.3, §19.4 essentially for free — every create/update/delete is versioned with actor + timestamp automatically. |
| Field-level encryption | **`django-cryptography`** (Fernet-based) on National ID, phone number, and any free-text field flagged sensitive | Satisfies Malawi Data Protection Act 2024 alignment and §9.4 "encryption of sensitive data at rest." |
| API docs | **`drf-spectacular`** (OpenAPI/Swagger) on the DRF surface only | Judges score Technical Design — a live OpenAPI doc is a 2-hour investment with outsized payoff. |
| Hosting (demo/online) | **Render free web service** (Django) + **Neon free Postgres** (0.5GB, scale-to-zero, no expiry) + **Upstash free Redis** | Verified July 2026: Render free web services sleep after 15 min idle (~30–60s cold start — ping it 5 min before your demo slot). Neon free tier does not expire and needs no card, unlike Render's own free Postgres which auto-deletes after 30 days — **do not use Render's bundled Postgres**, use Neon. |
| Hosting (offline/local fallback) | **Docker Compose bundle**: Django + gunicorn + Postgres + Redis + Nginx, running on a single laptop, no internet required | Directly satisfies brief §10 "local server fallback" and doubles as your demo-day insurance policy and your post-competition low-resource clinic deployment story. |
| Frontend build tooling | **Tailwind CLI standalone binary** (no `node_modules`, no bundler) + vendored HTMX/Alpine `<script>` files (not npm) | Zero JS supply-chain surface. This is a direct, deliberate response to the dependency-compromise concern — see §5. |
| Package management | `pip` + `pip-tools` (`requirements.in` → pinned `requirements.txt` with hashes) | Reproducible, auditable builds. |

## 3. Why HTMX + Alpine + Django Templates, not a React/Vue SPA

This is the decision most likely to be second-guessed mid-project by an AI agent defaulting to "modern SPA" patterns. It is deliberate:

- **Speed of build**: no API duplication (one Django view returns both the page and the fragment), no CORS, no separate auth story, no client-side router, no build pipeline to debug at 2am before demo day.
- **Speed of page load**: matches the explicit brief that we're chasing — "loads fast, feels responsive, minimal visual distraction, professional" (their own Laravel-docs comparison). Server-rendered HTML with small HTMX swaps beats a hydrated SPA on first paint every time, especially on the low-bandwidth connections this brief is explicitly designed around.
- **Security surface**: Django's template auto-escaping + CSRF middleware close most of the XSS/CSRF risk automatically. A hand-rolled fetch-based SPA reopens both.
- **Offline story**: a thin service worker caches the app shell and queues HTMX form POSTs in IndexedDB when offline, replaying them on reconnect. This is a well-understood pattern (see §6) and is dramatically simpler to build correctly in two weeks than a full offline-capable SPA with client-side state reconciliation.

**Agents must not introduce React, Vue, Next.js, or any SPA framework into this repo.** If a task seems to need one, stop and raise it — it almost certainly means the task should be re-scoped, not that the stack should change.

## 4. Module boundary map (bounded contexts — respect these)

Each Django app below is owned by exactly one backend engineer. Cross-app access happens **only** through: (a) Django model ForeignKeys to a small set of shared "core" models owned by Engineer A, or (b) explicit internal service functions exposed in each app's `services.py`. No engineer directly queries another app's internal models outside its declared public interface — this is what lets 5 people merge without stepping on each other.

| App(s) | Owner | Domain |
|---|---|---|
| `accounts`, `patients` | Engineer A | Identity, RBAC, audit config, Patient Registration & Master Patient Index — **the foundation everyone else's models FK into** |
| `encounters`, `vitals` | Engineer B | Outpatient clinical documentation, observations, early warning score |
| `laboratory`, `imaging` | Engineer C | Lab orders/results, imaging request/report stub |
| `pharmacy` | Engineer D | E-prescribing, allergy/interaction/dose safety, dispensing |
| `billing`, `dialysis`, `reporting`, `interop`, `syncapi` | Engineer E | Revenue cycle, dialysis (stretch), dashboards, FHIR-lite export, offline sync endpoints |

Engineer A's models (`Patient`, `User`/`Profile`, `AuditEvent`) must be **contract-frozen by end of Day 2** (see root build calendar in `README.md`). Every other engineer builds against that frozen contract, not against a moving target. If Engineer A needs to change a frozen field after Day 2, it goes through a 1-line PR that all four other engineers are tagged on — no silent breaking changes.

## 5. Dependency policy (allowlist + audit) — this is not optional

Context: this year saw real npm/GitHub supply-chain compromises reaching into internal repos. We minimize blast radius by minimizing what we depend on, and we audit what we keep.

**Rules for every engineer and every AI agent:**

1. **No new dependency without it being added to `ALLOWED_PACKAGES.md` in the repo root first**, with a one-line justification. If it's not on the list, don't `pip install` it, don't suggest it, don't let the agent quietly add it to `requirements.in`.
2. **Prefer what's already in Django/DRF over a new package.** Concretely, agents must NOT reach for a third-party library to do: authentication, session handling, form validation, admin CRUD, pagination, filtering (DRF has `django-filter`, that's the one exception — it's allowlisted), CSRF, or password hashing. These exist in the framework.
3. **Every dependency is pinned with hashes** via `pip-compile --generate-hashes`. `requirements.txt` is never hand-edited.
4. **`pip-audit` runs in CI on every PR.** A PR with a new high/critical CVE in its dependency tree does not merge, no exceptions, no "we'll fix it after demo day."
5. **No frontend npm dependency tree at all.** Tailwind CLI binary is downloaded once and checked as a documented, pinned version in setup docs (not committed as a binary — pin the version string). HTMX and Alpine are vendored as single `.js` files with a comment noting exact version and source URL, not pulled from a CDN at request-time (CDN outage during demo = dead app) and not pulled via `npm install` (supply-chain surface).
6. **Nothing installed directly from a git branch/commit URL, ever.** Only versioned releases from PyPI, hash-pinned.

### Initial allowlist (backend)

`django`, `djangorestframework`, `django-filter`, `psycopg[binary]`, `django-simple-history`, `django-cryptography`, `django-axes`, `drf-spectacular`, `gunicorn`, `whitenoise`, `redis`, `celery` (week-2, only if scheduled), `python-decouple`, `pip-audit`, `pytest`, `pytest-django`, `factory-boy`.

Anything beyond this list requires a one-line addition to `ALLOWED_PACKAGES.md` with owner sign-off before use.

## 6. Offline-first design (the pattern every agent should implement, not invent)

Two distinct offline stories, don't conflate them:

1. **No internet on the server side** (clinic has no ISP link at all): solved by the **local Docker Compose fallback** (§2) — the whole stack runs on a laptop/local server, no cloud dependency. This is what you demo if the venue Wi-Fi fails.
2. **Intermittent client connectivity** (a nurse's tablet drops signal mid-shift, server is otherwise reachable): solved by:
   - A vanilla **service worker** caching the app shell (layout, CSS, JS) so the UI still loads with no network.
   - **IndexedDB** (via the tiny `idb` helper, ~1KB, vendored not npm-installed) as a local outbox: HTMX form submissions that fail due to no network get queued here instead of erroring.
   - On reconnect, a background sync event replays queued submissions against `syncapi` endpoints, which are idempotent (client-generated UUID per submission prevents duplicate patient records/encounters on replay).
   - **Conflict rule**: last-write-wins is not acceptable for clinical data. Any replayed write that conflicts with a newer server-side record for the same patient is flagged into a `SyncConflict` model for a human (not silently merged, not silently dropped) — this is a patient-safety requirement, not a nice-to-have.

Do not build a generic client-side state-sync framework. Build exactly this queue-and-replay pattern, scoped to the specific forms in the MVP list.

## 7. Security baseline (applies to every module, no exceptions)

- All PHI/PII fields (National ID, phone, address, next-of-kin contact) use the encrypted field type from `django-cryptography`.
- Every model touching clinical or identifying data is registered with `django-simple-history`.
- Every view is behind `@login_required` / DRF permission classes by default — **default-deny**, explicitly allow, never the reverse.
- RBAC groups (minimum): `Nurse`, `Clinician`, `Pharmacist`, `LabTech`, `Radiographer`, `BillingOfficer`, `Admin`, `ICT`. Permissions assigned per-group in a fixtures file, not hardcoded in views.
- All forms use Django `ModelForm`/`Form` validation server-side — never trust client-side validation alone.
- `django-axes` locks an account after 5 failed logins for 15 minutes.
- Session timeout: 15 minutes idle for clinical roles (configurable per role via `SESSION_COOKIE_AGE` + a lightweight Alpine idle-timer that warns at 13 minutes).
- HTTPS-only in any deployed environment (`SECURE_SSL_REDIRECT`, HSTS) — the local Docker fallback is the one place plain HTTP is acceptable, and only because it's not traversing a public network.
- Every write to a clinical/PHI record must resolve to an authenticated `User` — no anonymous or shared-account writes anywhere in the system, including seed/demo scripts.
- Standard Django protections (parameterized ORM queries, template auto-escaping, CSRF middleware) are **never bypassed** — no raw SQL string interpolation, no `|safe` filter on user-supplied content, no `mark_safe()` on anything not generated server-side by us.

## 8. Interoperability posture (bonus points, don't over-build)

Section 7.5/8.1.18/9.5 of the brief ask for FHIR/HL7/DICOM/LOINC "readiness," not a real integration engine — nobody is building a HAPI FHIR server in two weeks. The correct scope:

- Data model field names and codes chosen to be **FHIR-shape-compatible** where cheap (e.g. `Patient.gender` uses FHIR's value set, lab results carry a `loinc_code` nullable field even if unpopulated for MVP).
- One read-only `interop` DRF endpoint that serializes a Patient + recent encounters into a FHIR-Bundle-shaped JSON document. This is the "FHIR-aware data model" bonus point (§22) satisfied honestly, without pretending to be a certified FHIR server.
- Do not attempt real DICOM file handling — the Imaging module stores request/report **metadata only** (§8.2.1's "image-link concept"), not actual image files or PACS integration.

## 9. Definition of done (every PR, every module)

A PR is not done until:
1. Migrations included, reversible, run cleanly on a fresh DB.
2. RBAC checked — verified which groups can/can't access the new view.
3. `django-simple-history` covers any new PHI/clinical model.
4. Sensitive fields use encrypted field types where applicable.
5. `pytest` tests cover at least: one happy path, one permission-denied path, one validation-failure path.
6. `pip-audit` clean.
7. Traceable back to a brief section number in the PR description (e.g. "implements §8.1.10 Laboratory Information Management: order + result entry").

## 10. Judging-criteria cross-check (keep this in view, not just the code)

| Criterion | Weight | What actually earns this in our repo |
|---|---|---|
| Clinical Relevance | 20% | The MVP chain works end-to-end with realistic Malawi-context fields (Traditional Authority, village, guardian/next-of-kin) |
| Patient Safety | 20% | Allergy/interaction alerts, duplicate patient detection, critical-result alerts, audit trail, time-stamped notes — all real, not decorative |
| Innovation | 15% | Offline-first sync design, dialysis module, FHIR-lite export |
| Technical Design | 15% | Clean module boundaries, OpenAPI docs, dependency audit trail, local + cloud dual deployment |
| Malawi Context Fit | 15% | Offline/local fallback demoed live, low-bandwidth-optimized frontend, mobile money billing field |
| Sustainability | 15% | Free-tier-first hosting, near-zero external dependency footprint, open-source-first stack an in-house team can maintain post-competition |

Every engineer should be able to point at their module and say which row it earns points on. If a feature doesn't map to a row above and isn't in the MVP list, it's scope creep — cut it.
