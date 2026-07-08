# GrandGaze EMR — Full System & Security Audit

**Date:** 2026-07-08
**Scope:** All Django apps, CI/CD, Docker, templates, security configuration, git history, UI/UX flows, tests.
**Methodology:** Static analysis of all source files, settings review, template rendering audit, git history inspection, dependency audit.

---

## Executive Summary

The codebase is structurally sound with strong architectural decisions (AGENTS.md) and generally clean module boundaries. However, this audit found **4 CRITICAL security issues**, **7 HIGH security issues**, and **6 CRITICAL pipeline/broken-flow issues** that directly impact patient safety, demo-day functionality, and judging criteria scores.

**Most urgent:** The app will silently fail on all HTMX POST submissions (broken CSRF), the lab ordering flow is completely non-functional (hardcoded URL), and the production settings diverge from test settings (missing `django_filters`). Additionally, the git history contains a full Python virtual environment (~50+ MB) and a competition brief PDF.

---

## 1. SYSTEM AUDIT — Pipelines & Broken Flows

### 1.1 CI/CD Pipeline (`ci.yml`)

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| P1 | **CRITICAL** | PostgreSQL service started (lines 11-24) but tests run against SQLite in-memory via `DJANGO_SETTINGS_MODULE: config.test_settings`. The `DATABASE_URL` env var (line 49) is never read by test settings. PostgreSQL-specific code paths (TrigramSimilarity duplicate detection) are never tested in CI. | `.github/workflows/ci.yml:49` |
| P2 | **CRITICAL** | Redis service started (lines 25-28) but never used by any test. Wastes ~30s CI minutes per run. | `.github/workflows/ci.yml:25-28` |
| P3 | **HIGH** | No linting job — no `ruff`, `flake8`, `black`, `mypy`, or `pyright`. Code style and type inconsistencies are never caught. | `.github/workflows/ci.yml` |
| P4 | **HIGH** | Placeholder vulnerability ID `PYSEC-2024-XXX` (line 44). If replaced with a real ID to suppress warnings, unpatched vulnerabilities could ship. | `.github/workflows/ci.yml:44` |
| P5 | **HIGH** | No migration check (`makemigrations --check`). Model changes without corresponding migrations could pass CI. | `.github/workflows/ci.yml` |
| P6 | **HIGH** | No SAST scanning (`bandit`, `semgrep`) for application-level vulnerabilities. `pip-audit` only checks dependency CVEs. | `.github/workflows/ci.yml` |
| P7 | **MEDIUM** | Python version mismatch: CI uses 3.12, requirements compiled with 3.11, host runs 3.14. | `.github/workflows/ci.yml:36` |
| P8 | **MEDIUM** | No scheduled (nightly/weekly) CI runs. Dependency drift undetected between pushes. | `.github/workflows/ci.yml` |

### 1.2 Build & Dev Tooling (`Makefile`)

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| P9 | **CRITICAL** | Makefile uses Windows paths (`.\tailwindcss.exe`) and `.exe` extension on Linux. Both targets are completely broken on Linux/macOS. | `Makefile:3,5` |
| P10 | **HIGH** | No useful developer targets (`make test`, `make migrate`, `make run`, `make docker-up`). Only two broken Tailwind targets exist. | `Makefile` |
| P11 | **LOW** | Makefile uses spaces instead of tabs for recipe lines. Non-GNU `make` versions will reject it. | `Makefile:3,5` |

### 1.3 Docker Infrastructure

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| P12 | **MEDIUM** | `COPY . .` copies everything into image. If `.dockerignore` is incomplete, sensitive files get baked in. | `Dockerfile:30` |
| P13 | **MEDIUM** | `collectstatic` errors silently swallowed: `2>/dev/null || true`. A broken static build produces a working image with no static files. | `Dockerfile:33` |
| P14 | **MEDIUM** | No non-root user in container. App runs as root. | `Dockerfile` |
| P15 | **MEDIUM** | Hardcoded database password `must_emr` in docker-compose.yml, with no env-var override pattern used. | `docker-compose.yml:24` |
| P16 | **MEDIUM** | No automated migration step in docker-compose startup. Manual step required after `up`. | `docker-compose.yml` |
| P17 | **LOW** | Default `DJANGO_SECRET_KEY` in compose (`dev-insecure-change-me`) and `CRYPTOGRAPHY_KEY` (`dev-insecure-crypto-key`) — known weak keys that boot without warning. | `docker-compose.yml:51,60` |

### 1.4 Git History Issues

| # | Severity | Issue | Details |
|---|----------|-------|---------|
| G1 | **CRITICAL** | Full Python virtual environment committed (`emr/lib/python3.13/`) — ~50+ MB of unnecessary bloat including vendored packages, `.pyc` files, and pip distribution. | Commit `a247bf6` |
| G2 | **CRITICAL** | Competition brief PDF committed (`MUST_GSL EMR Innovation Challenge Brief v31'05'2026.pdf`) — ~577KB, potentially containing confidential competition details. | Commit `b914229` (inferred) |
| G3 | **HIGH** | `.tar.gz` binary artifact committed (`must-emr-changed-files.tar.gz`) — ~577KB of unknown content permanently in history. | Commit `0ff0859` |
| G4 | **HIGH** | `.env` file with production-looking `DJANGO_SECRET_KEY` and `CRYPTOGRAPHY_KEY` on disk. While `.gitignore`-ed, any clone or filesystem share exposes them. | `/root/EMR/GrandGaze/.env` |

### 1.5 Broken UI/UX Flows

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| U1 | **CRITICAL** | **Lab order form POSTs to non-existent URL.** `hx-post="/labs/order/"` does not match any URL pattern (actual route is `patient/<int:patient_id>/order/`). Also missing `patient_id`. | `templates/laboratory/partials/_order_form.html:13` |
| U2 | **CRITICAL** | **Missing CSRF token on HTMX form.** The lab order form has `hx-post` but no `{% csrf_token %}`. Django's CSRF middleware will reject with 403. | `templates/laboratory/partials/_order_form.html:13` |
| U3 | **HIGH** | **Wrong parameter name in component include.** `_duplicate_warning.html` passes `severity="warning"` but `_alert_banner.html` expects `type="warning"`. Warning renders as info (blue instead of amber). | `templates/patients/_duplicate_warning.html:8` |
| U4 | **HIGH** | **Duplicate addendum forms on encounter detail page.** Two addendum forms (line 248 Django form, line 277 raw textarea) render simultaneously on the page, allowing duplicate notes. | `templates/encounters/detail.html:248,277` |
| U5 | **HIGH** | **Non-functional navigation links.** "Start New Encounter" and "View Details" links on patient visits tab use `href="#"` — they lead nowhere. | `templates/patients/partials/_visits_tab.html:6,33` |
| U6 | **HIGH** | **Non-functional "New Prescription" button.** Button element with no hx-get, @click, or onclick binding. Clicking does nothing. | `templates/patients/partials/_prescriptions_tab.html:9` |
| U7 | **MEDIUM** | **Chart.js loaded on every page (~250KB) but never used by any template.** Adds unnecessary page weight. | `templates/base.html:265` |
| U8 | **MEDIUM** | **4 forms with missing `action` attributes.** Forms will POST to current URL, which may not be the intended handler. | `vitals/partials/_capture_form.html:138`, `pharmacy/partials/_prescription_form.html:43`, `encounters/detail.html:277`, `laboratory/collect.html:32` |
| U9 | **MEDIUM** | **Pharmacy dispense form has `action="#"`.** Posts to URL fragment, effectively self-posts without clear target. | `templates/pharmacy/dispense_queue.html:81` |
| U10 | **MEDIUM** | **Missing `id` on all vitals form inputs.** Labels use `for` attributes but no matching `id` on inputs. Breaks screen reader accessibility. | `vitals/partials/_capture_form.html:148-213`, `vitals/entry.html:107-236` |
| U11 | **MEDIUM** | **Hardcoded mock patient PHI data exposed in templates.** Realistic patient names (John Phiri, Mary Banda), IDs, vitals, and lab values hardcoded in template files — NOT served from database. | `templates/patients/partials/_labs_tab.html:1-105`, `templates/laboratory/results_entry.html:58-108` |
| U12 | **MEDIUM** | **Inconsistent branding colors.** Lab and imaging templates use raw Tailwind `teal-600` instead of project brand tokens (`--color-brand: #0f766e`). | `laboratory/results_entry.html`, `laboratory/partials/_order_form.html`, `patients/partials/_labs_tab.html` |
| U13 | **LOW** | **`idb.min.js` vendored but never loaded in any template.** 1KB dead code in static directory. | `static/js/idb.min.js` |
| U14 | **LOW** | **`_status_badge.html` component exists but is never included by any template.** Dead code. | `templates/components/_status_badge.html` |
| U15 | **LOW** | **UI preview prototype template** (`ui_preview/labs.html`) present in production templates directory. | `templates/ui_preview/labs.html` |

### 1.6 Stale/Untested Code Paths

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| T1 | **HIGH** | **Always-skipped test.** `test_forged_confirmation_id_does_not_bypass_duplicate_check` uses `@pytest.mark.skipif(True, ...)` — condition is literally `True`, never runs anywhere. | `patients/tests.py:70-72` |
| T2 | **HIGH** | **Missing `django_filters` in production INSTALLED_APPS.** Present in test_settings.py (line 23) but absent from settings.py — tests pass with a different app configuration than production. | `config/settings.py:19-47` vs `config/test_settings.py:12-39` |
| T3 | **MEDIUM** | PostgreSQL-only tests (`syncapi/tests.py:49,107,133`) gated on `@requires_postgres` but CI runs SQLite. Critical patient-safety sync regression tests never execute. | `syncapi/tests.py` |
| T4 | **MEDIUM** | **No test coverage for:** `core/encrypted_fields.py`, session timeout, password reset flow, demo seed command, health endpoint, CSRF protection on forms, RBAC group permissions, encrypted field edge cases (key rotation, ciphertext corruption). | Across codebase |

---

## 2. SECURITY AUDIT

### 2.1 CRITICAL Vulnerabilities

| # | Vulnerability | Impact | File:Line |
|---|--------------|--------|-----------|
| C1 | **HTMX CSRF header broken** — `CSRF_COOKIE_HTTPONLY = True` prevents JS from reading the `csrftoken` cookie. HTMX uses JS to read this cookie and set the `X-CSRFToken` header. All HTMX POST/PUT/DELETE requests will fail with 403 Forbidden unless a meta-tag workaround exists in every template. No such workaround found in base.html or any form template. | App non-functional for all write operations. | `config/settings.py:129` |
| C2 | **No database SSL/TLS** — `DATABASES` dict has no `OPTIONS` with `sslmode`. All PHI/PII data in transit between app server and PostgreSQL is unencrypted. On any network (cloud VPC, local network, Neon public endpoint), traffic is interceptable. | Violates Malawi Data Protection Act 2024 and brief §9.4. | `config/settings.py:86-95` |
| C3 | **Session & CSRF cookies not marked Secure** — `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` not set (default `False`). Cookies transmitted over unencrypted HTTP. Attacker on same network can capture cookies via passive packet capture for session hijacking. | Session hijacking, account takeover. | `config/settings.py:126-131` |
| C4 | **`SECURE_SSL_REDIRECT` defaults to `False`** — no env override means all traffic is HTTP. In production, credentials and PHI flow in cleartext. | Full MITM of all user traffic and data. | `config/settings.py:130` |

### 2.2 HIGH Vulnerabilities

| # | Vulnerability | Impact | File:Line |
|---|--------------|--------|-----------|
| H1 | **No `SECURE_PROXY_SSL_HEADER` configured** — deployed behind TLS-terminating proxy (Render, Nginx), Django won't know original request was HTTPS. `SECURE_SSL_REDIRECT` causes infinite redirect loops; `request.is_secure()` always returns `False`. | Broken deployments, incorrect security decisions in code. | `config/settings.py` |
| H2 | **No logging configuration** — auth failures, 500 errors, CSRF failures, security events are invisible to ops. No forensic capability. | Blind to attacks, impossible incident response. | `config/settings.py` |
| H3 | **`SECURE_HSTS_SECONDS` defaults to `0`** — HSTS disabled. No automatic HTTP→HTTPS upgrade. Users vulnerable to SSL-strip attacks. | Man-in-the-middle downgrade attacks. | `config/settings.py:131` |
| H4 | **Hardcoded default database password `must_emr`** — if production deployment omits `DB_PASSWORD` env var, database uses trivially guessable password from source code. | Database compromise. | `config/settings.py:91` |
| H5 | **No API rate limiting (DRF throttling)** — offline-sync, FHIR-lite, and dashboard API endpoints (`/api/*`) have no request throttling. Enables brute-force auth, data scraping, DB flooding via sync endpoints. | Data exfiltration, DoS, credential brute-force. | `config/settings.py:157-165` |
| H6 | **Potential XSS via template string interpolation into Alpine handler** — `@click="activeTab = '{{ tab.id }}'"` interpolates user-controlled value into JS string without `escapejs` filter. Single quote in `tab.id` breaks string boundary. | Cross-site scripting. | `templates/patients/profile.html:105` |
| H7 | **`CRYPTOGRAPHY_KEY` falls back to `SECRET_KEY`** — if `CRYPTOGRAPHY_KEY` env var not set, encryption key = Django SECRET_KEY. No key separation. If SECRET_KEY is compromised, all encrypted PHI is decryptable. | Wrapped PHI encryption key compromise. | `config/settings.py:140`, `core/encrypted_fields.py:34` |

### 2.3 MEDIUM Vulnerabilities

| # | Vulnerability | Impact | File:Line |
|---|--------------|--------|-----------|
| M1 | **DRF BrowsableAPIRenderer enabled in production** — browsable API exposes interactive HTML forms, model schemas, and available actions. Increases attack surface and information disclosure. | Information disclosure, increased XSS surface. | `config/settings.py:157-165` |
| M2 | **`AXES_RESET_ON_SUCCESS` not set** (defaults to `False`) — failed login counter not reset after successful login. User 4 failed attempts away from lockout after successful login. | Account lockout denial-of-service. | `config/settings.py:134-136` |
| M3 | **`EMAIL_BACKEND` hardcoded to console** — password reset emails (core security feature) only printed to console. Non-functional in any deployed environment. | Broken password reset flow. | `config/settings.py:153` |
| M4 | **No `CSRF_TRUSTED_ORIGINS` configured** — when deployed behind proxy or custom domain, CSRF origin checking may reject legitimate requests or behave unexpectedly. | Broken form submissions in production. | `config/settings.py` |
| M5 | **No `SECURE_REFERRER_POLICY`** — browser sends full URL (including /patients/12345/) in `Referer` header to external sites. PHI path leakage. | Patient privacy violation. | `config/settings.py` |
| M6 | **`SECURE_CONTENT_TYPE_NOSNIFF` not set** — while Django 5.x defaults to `True`, not explicit. Risk of MIME-sniffing XSS if overridden. | XSS via MIME-sniffing. | `config/settings.py` |
| M7 | **`SECURE_HSTS_INCLUDE_SUBDOMAINS` and `SECURE_HSTS_PRELOAD` not set** — subdomains not protected by HSTS. | Reduced HSTS effectiveness. | `config/settings.py` |
| M8 | **Username enumeration via Axes** — `AXES_ONLY_USER_FAILURES` not set. Attackers can distinguish between existing and non-existing usernames by response difference. | User enumeration. | `config/settings.py:134-136` |
| M9 | **Missing `CSRF_TRUSTED_ORIGINS`** — not set anywhere. Production deployments with custom domains may fail CSRF checks. | CSRF failures in production. | `config/settings.py` |
| M10 | **Hardcoded API URL in JavaScript** — `/api/sync/submit/` hardcoded in `app.js` instead of using Django `{% url %}`. Will break if URL config changes. | Broken offline sync. | `static/js/app.js:159` |

### 2.4 LOW Vulnerabilities / Observations

| # | Issue | Details |
|---|-------|---------|
| L1 | Debug context processor enabled in templates (`django.template.context_processors.debug`) — if `DEBUG=True` in production, leaks all SQL queries on every page. | `config/settings.py:72` |
| L2 | `ALLOWED_HOSTS` includes `0.0.0.0` — not a valid HTTP Host header. Won't match anything but indicates confusion. | `.env:4` |
| L3 | Deprecated `STATICFILES_STORAGE` setting — use `STORAGES` dict in Django 5.2+. | `config/settings.py:117` |
| L4 | `SESSION_COOKIE_HTTPONLY` and `SESSION_COOKIE_SAMESITE` not explicitly set. Django defaults are secure but not documented. | `config/settings.py` |
| L5 | Console.log statements in production JS (`app.js`, `sw.js`) — leak operational details in browser console. | `static/js/app.js`, `static/js/sw.js` |
| L6 | Unprofessional comment in committed code: "cant believe i missed this part .. but we are past that" | `config/settings.py:116` |
| L7 | `PermissionDeniedMiddleware` suppresses Django's debug error pages for 403 even in DEBUG mode — makes debugging permission logic harder. | `config/middleware.py:16` |
| L8 | `core` app has no `apps.py` — signals in `core` may not auto-discover. | `core/` |
| L9 | `AXES_ENABLED = False` in tests — lockout flow never tested. A regression in account lockout goes undetected. | `config/test_settings.py:94` |
| L10 | Test `AUTH_PASSWORD_VALIDATORS = []` — test users created with weak/no passwords. | `config/test_settings.py:76` |

---

## 3. TEST COVERAGE GAPS

| Area | Coverage | Risk |
|------|----------|------|
| Core encrypted fields (`core/encrypted_fields.py`) | **0%** — no tests for `EncryptedCharField` | Field-level encryption may silently fail |
| CSRF protection on form submissions | **0%** — no test verifies CSRF token presence/rejection | Broken HTMX CSRF may ship undetected |
| Session timeout (15-min idle) | **0%** — no test that session expires after inactivity | Patient safety requirement not verified |
| Password reset workflow | **0%** — no end-to-end test of reset flow | Core auth flow untested |
| Demo seed management command | **0%** — no test for seed data generation | Demo-day demo data may fail to generate |
| Health endpoint (`/health/`) | **0%** — no test that endpoint returns 200 | Monitoring/load balancer health checks unverified |
| RBAC group-based permissions | **Partial** — basic role checks exist, but no test for each group's specific permissions | Privilege escalation may go undetected |
| PostgreSQL-specific duplicate detection | **0% in CI** — tests gated on `@requires_postgres` but CI runs SQLite | Patient duplicate detection may fail in production |
| Encrypted field edge cases | **0%** — no key rotation, corrupted ciphertext, or migration tests | Data loss on key rotation |
| Billing: invoice void, refund, line item edit | **0%** — only basic access control tested | Financial logic untested |

---

## 4. RECOMMENDATIONS (Priority Order)

### Fix Now (Before Demo Day)

1. **Fix HTMX CSRF** — Either set `CSRF_COOKIE_HTTPONLY = False` or implement a meta-tag CSRF workaround in `base.html` and verify every HTMX form submits correctly.
2. **Fix lab order form** — Replace hardcoded `/labs/order/` with correct URL pattern `{% url 'laboratory:order' patient_id=patient.id %}`, add `{% csrf_token %}`.
3. **Add `django_filters` to production `INSTALLED_APPS`** — `config/settings.py` line 25-38.
4. **Set production security headers** — Add `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_HSTS_SECONDS` (>=3600).
5. **Add database SSL** — Add `OPTIONS` with `sslmode` to `DATABASES` config.
6. **Fix Makefile** — Replace Windows paths with platform-agnostic commands or update for Linux.

### Fix This Week

7. **Clean git history** — Remove `emr/` (full venv), `.pdf` brief, and `.tar.gz` artifact using `git filter-repo`.
8. **Rotate `.env` secrets** — Generate new `DJANGO_SECRET_KEY` and `CRYPTOGRAPHY_KEY`. The current on-disk values should be considered compromised.
9. **Add API throttling** — Configure DRF `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES`.
10. **Fix duplicate warning component** — Change `severity="warning"` to `type="warning"` in `_duplicate_warning.html`.
11. **Remove duplicate addendum form** — Consolidate to one form in `encounters/detail.html`.

### Fix Before Final Submission

12. **Add logging configuration** — At minimum, log `django.request` (ERROR), `axes` (WARNING), and custom security events.
13. **Add CI linting** — Add `ruff` check to CI workflow.
14. **Fix CI postgres/redis waste** — Either remove unused service containers or switch CI to use PostgreSQL for true end-to-end testing.
15. **Fix `test_forged_confirmation_id_does_not_bypass_duplicate_check`** — Replace `skipif(True)` with dynamic database-vendor check.
16. **Fix non-functional UI links** — Replace `href="#"` with real URLs, wire up "New Prescription" button.
17. **Configure real email backend** — Make `EMAIL_BACKEND` driven by env var so password reset works in deployed environments.
18. **Add non-root user to Dockerfile** — Hardening best practice.
19. **Remove `BrowsableAPIRenderer` in production** — Restrict to JSON-only responses on deployed environments.
20. **Add `CSRF_TRUSTED_ORIGINS` and `SECURE_REFERRER_POLICY`**.

---

## 5. Judging Criteria Impact Assessment

| Criterion | Weight | Audit Finding Impact |
|-----------|--------|---------------------|
| Clinical Relevance | 20% | **NEGATIVE** — Lab ordering flow is completely broken (U1, U2). Patient safety alerts render wrong color (U3). |
| Patient Safety | 20% | **NEGATIVE** — Duplicate addendum forms (U4) could cause duplicated clinical entries. No DB SSL (C2) exposes PHI in transit. Encrypted field edge cases untested (T4). |
| Innovation | 15% | **NEUTRAL** — Offline sync architecture is sound but sync API has no throttling (H5). |
| Technical Design | 15% | **NEGATIVE** — CI tests SQLite instead of PostgreSQL (P1), production/test settings diverge (T2), full venv in git history (G1), unprofessional comment in code (L6). |
| Malawi Context Fit | 15% | **NEUTRAL** — Timezone set to Africa/Blantyre (good). HTMX+Alpine is low-bandwidth friendly but lab form broken (U1). |
| Sustainability | 15% | **NEGATIVE** — Broken Makefile (P9), no CI linting (P3), no logging (H2), large git history (G1-G3). Hard to maintain for future teams. |

---

## Appendix: Files Referenced

| File | Purpose |
|------|---------|
| `config/settings.py` | Production and development Django settings |
| `config/test_settings.py` | Test-only settings (SQLite in-memory) |
| `config/middleware.py` | Custom PermissionDeniedMiddleware |
| `.github/workflows/ci.yml` | GitHub Actions CI workflow |
| `Dockerfile` | Multi-stage production Docker image |
| `docker-compose.yml` | Local fallback / demo deployment |
| `Makefile` | Build automation (broken on Linux) |
| `nginx.conf` | Nginx reverse proxy for Docker |
| `.env` | Local environment secrets (on disk, not tracked) |
| `core/encrypted_fields.py` | Custom Fernet-based field encryption |
| `templates/base.html` | Base template (loads all JS/CSS) |
| `templates/laboratory/partials/_order_form.html` | Lab order form (broken) |
| `templates/patients/_duplicate_warning.html` | Duplicate patient warning (wrong params) |
| `templates/encounters/detail.html` | Encounter detail (duplicate forms) |
| `templates/patients/partials/_visits_tab.html` | Visits tab (dead links) |
| `templates/patients/partials/_prescriptions_tab.html` | Prescriptions tab (dead button) |
| `templates/patients/profile.html` | Patient profile (potential XSS) |
| `templates/patients/partials/_labs_tab.html` | Labs tab (hardcoded mock PHI) |
| `templates/laboratory/results_entry.html` | Lab results (hardcoded mock PHI) |
| `static/js/app.js` | Frontend app JS (hardcoded API URL) |
| `static/js/sw.js` | Service worker |
| `patients/tests.py` | Patient tests (always-skipped test) |
| `syncapi/tests.py` | Sync API tests (PostgreSQL-only, never run in CI) |
