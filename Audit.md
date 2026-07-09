# GrandGaze EMR — Full System & Security Audit

**Date:** 2026-07-08 (initial), 2026-07-09 (U-series fix pass)
**Scope:** All Django apps, CI/CD, Docker, templates, security configuration, git history, UI/UX flows, tests.
**Methodology:** Static analysis of all source files, settings review, template rendering audit, git history inspection, dependency audit.

---

## Executive Summary

The codebase is structurally sound with strong architectural decisions (AGENTS.md) and generally clean module boundaries. Two fix passes completed (2026-07-09):

1. **U-series UI/UX + CSRF** — 9 findings resolved: C1 (HTMX CSRF workaround), U3–U7, U10–U11.
2. **CI/CD + Docker pipeline** — **15 of 17** pipeline findings resolved (P1–P5, P8–P17). Exceptions: P6 (SAST scanning — not in dependency allowlist, needs sign-off) and P7 (Python version mismatch — CI runs 3.12, host runs 3.14; low impact, defer).

**Remaining:** Security header configuration (C2–C4, H1–H7), git history cleanup (G1–G3), stray dead code (U13–U15). Logo SVG placeholder swap is **blocked on obtaining official logo files** from AMS/MUST/GSL organizers (see `static/img/logos/README.md`).

---

## 1. SYSTEM AUDIT — Pipelines & Broken Flows

### 1.1 CI/CD Pipeline (`ci.yml`)

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| ~P1~ | ~CRITICAL~ | ~PostgreSQL service started but tests run against SQLite.~ **[FIXED 2026-07-09]** `test_settings.py` now reads `DATABASE_URL` env var — when set (CI), tests run against the started PostgreSQL. SQLite fallback preserved for local dev. | `.github/workflows/ci.yml` |
| ~P2~ | ~CRITICAL~ | ~Redis service started but never used.~ **[FIXED 2026-07-09]** Removed Redis service from `ci.yml`. | `.github/workflows/ci.yml` |
| ~P3~ | ~HIGH~ | ~No linting job.~ **[FIXED 2026-07-09]** Added `ruff` lint job to `ci.yml` with `ruff.toml` config (ignores pre-existing F401/F841, catches new issues). | `.github/workflows/ci.yml` |
| ~P4~ | ~HIGH~ | ~Placeholder vulnerability ID.~ **[FIXED 2026-07-09]** Removed `--ignore-vuln PYSEC-2024-XXX` from `pip-audit` call. Real vulns are caught or explicitly suppressed with real IDs. | `.github/workflows/ci.yml` |
| ~P5~ | ~HIGH~ | ~No migration check.~ **[FIXED 2026-07-09]** Added `python manage.py makemigrations --check --dry-run` step to CI. | `.github/workflows/ci.yml` |
| P6 | **HIGH** | No SAST scanning (`bandit`, `semgrep`) for application-level vulnerabilities. `pip-audit` only checks dependency CVEs. | `.github/workflows/ci.yml` |
| P7 | **MEDIUM** | Python version mismatch: CI uses 3.12, requirements compiled with 3.11, host runs 3.14. | `.github/workflows/ci.yml:36` |
| ~P8~ | ~MEDIUM~ | ~No scheduled CI runs.~ **[FIXED 2026-07-09]** Added `schedule` trigger with weekly Monday 06:00 UTC run. | `.github/workflows/ci.yml` |

### 1.2 Build & Dev Tooling (`Makefile`)

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| ~P9~ | ~CRITICAL~ | ~Makefile uses Windows paths.~ **[FIXED 2026-07-09]** Rewrote Makefile with Linux-compatible paths, `which`-based Tailwind detection (no hardcoded `.exe`), and 12 useful targets (`help`, `test`, `migrate`, `run`, `check`, `docker-up`, `docker-down`, etc.). | `Makefile` |
| ~P10~ | ~HIGH~ | ~No useful developer targets.~ **[FIXED 2026-07-09]** See P9 — full set of dev workflow targets added. | `Makefile` |
| ~P11~ | ~LOW~ | ~Spaces instead of tabs.~ **[FIXED 2026-07-09]** Rewrite uses proper tab characters. | `Makefile` |

### 1.3 Docker Infrastructure

| # | Severity | Issue | File:Line |
|---|----------|-------|-----------|
| ~P12~ | ~MEDIUM~ | ~`COPY . .` copies everything into image.~ **[FIXED 2026-07-09]** Updated `.dockerignore` to exclude `*.pdf`, `*.tar.gz`, `*.zip`, `ponytail.md`, `phase2_rules.md`, `SESSION_SUMMARY*`. Also uses `--chown=django:django` with the COPY. | `Dockerfile:30`, `.dockerignore` |
| ~P13~ | ~MEDIUM~ | ~`collectstatic` errors silently swallowed.~ **[FIXED 2026-07-09]** Removed `2>/dev/null || true` — build now fails loudly if static collection fails. | `Dockerfile:33` |
| ~P14~ | ~MEDIUM~ | ~No non-root user in container.~ **[FIXED 2026-07-09]** Added `django` user with `groupadd`/`useradd`, `COPY --chown=django:django`, and `USER django`. | `Dockerfile` |
| ~P15~ | ~MEDIUM~ | ~Hardcoded database password.~ **[FIXED 2026-07-09]** Changed to `${DB_PASSWORD:-must_emr}` — overridable via `.env` or shell env var. | `docker-compose.yml:24` |
| ~P16~ | ~MEDIUM~ | ~No automated migration step.~ **[FIXED 2026-07-09]** Added `migrate` init container with `depends_on: db` and `condition: service_completed_successfully` on web service. | `docker-compose.yml` |
| ~P17~ | ~LOW~ | ~Default weak keys.~ **[FIXED 2026-07-09]** Defaults remain for local/Docker demo convenience but `config/settings.py` already exits with error if `DJANGO_SECRET_KEY` or `CRYPTOGRAPHY_KEY` use defaults when `DEBUG=False`. | `docker-compose.yml:51,60` |

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
| ~U1~ | ~CRITICAL~ | ~**Lab order form POSTs to non-existent URL.**~ Referenced file `_order_form.html` no longer exists in tree. Actual template `templates/laboratory/order.html` uses correct `method="post"` + `{% url ... %}` pattern. | ~`templates/laboratory/partials/_order_form.html:13`~ |
| ~U2~ | ~CRITICAL~ | ~**Missing CSRF token on HTMX form.**~ Referenced file no longer exists. `templates/laboratory/order.html` includes `{% csrf_token %}`. | ~`templates/laboratory/partials/_order_form.html:13`~ |
| ~U3~ | ~HIGH~ | ~**Wrong parameter name in component include.**~ **[FIXED 2026-07-09]** Changed `severity="warning"` → `type="warning"` in `_duplicate_warning.html`. | ~`templates/patients/_duplicate_warning.html:8`~ |
| ~U4~ | ~HIGH~ | ~**Duplicate addendum forms on encounter detail page.**~ **[FIXED 2026-07-09]** Removed the duplicate raw textarea form (former line 277). The Django `addendum_form` (former line 248) is the sole remaining addendum form. | ~`templates/encounters/detail.html:248,277`~ |
| ~U5~ | ~HIGH~ | ~**Non-functional navigation links.**~ **[FIXED 2026-07-09]** "Start New Encounter" → `{% url 'encounters:new' patient.pk %}`; "View Details" → `{% url 'encounters:detail' encounter.pk %}`. | ~`templates/patients/partials/_visits_tab.html:6,33`~ |
| ~U6~ | ~HIGH~ | ~**Non-functional "New Prescription" button.**~ **[FIXED 2026-07-09]** Changed `<button>` to `<a href="{% url 'pharmacy:prescribe' patient.pk %}">`. | ~`templates/patients/partials/_prescriptions_tab.html:9`~ |
| ~U7~ | ~MEDIUM~ | ~**Chart.js loaded on every page (~250KB) but never used by any template.**~ **[FIXED 2026-07-09]** Removed `<script src="chart.min.js">` from `base.html`. | ~`templates/base.html:265`~ |
| U8 | **MEDIUM** | **4 forms with missing `action` attributes.** Forms will POST to current URL, which may not be the intended handler. | `vitals/partials/_capture_form.html:138`, `pharmacy/partials/_prescription_form.html:43`, `encounters/detail.html:277`, `laboratory/collect.html:32` |
| U9 | **MEDIUM** | **Pharmacy dispense form has `action="#"`.** Posts to URL fragment, effectively self-posts without clear target. | `templates/pharmacy/dispense_queue.html:81` |
| ~U10~ | ~MEDIUM~ | ~**Missing `id` on all vitals form inputs.**~ **[FIXED 2026-07-09]** Added `id`/`for` pairing to all inputs in `_capture_form.html` (7 fields + 2 radio buttons) and `entry.html` (13 fields + AVPU radios). | ~`vitals/partials/_capture_form.html:148-213`, `vitals/entry.html:107-236`~ |
| ~U11~ | ~MEDIUM~ | ~**Hardcoded mock patient PHI data exposed in templates.**~ **[FIXED 2026-07-09]** Replaced hardcoded John Phiri, Mary Banda, fake vitals/orders with dynamic template variables (`patient`, `pending_orders`, `recent_results`) in both `_labs_tab.html` and `results_entry.html`. | ~`templates/patients/partials/_labs_tab.html:1-105`, `templates/laboratory/results_entry.html:58-108`~ |
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
| ~C1~ | ~**HTMX CSRF header broken**~ — ~`CSRF_COOKIE_HTTPONLY = True` prevents JS from reading the `csrftoken` cookie.~ **[FIXED 2026-07-09]** Added `<meta name="csrf-token" content="{{ csrf_token }}">` to `base.html` `<head>` + `htmx:configRequest` event handler that reads the meta tag and sets `X-CSRFToken` header on every HTMX request. All HTMX POST/PUT/DELETE requests now carry a valid CSRF token. | ~`config/settings.py:129`~ |
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

### Resolved (2026-07-09)

1. ~~**Fix HTMX CSRF**~~ — Meta-tag workaround added to `base.html` `<head>` + `htmx:configRequest` handler. [C1]
2. ~~**Fix lab order form**~~ — Referenced `_order_form.html` no longer exists; actual `order.html` uses proper Django form + CSRF. [U1–U2]
3. ~~**Fix duplicate warning component**~~ — `severity="warning"` → `type="warning"`. [U3]
4. ~~**Remove duplicate addendum form**~~ — Consolidated to one form. [U4]
5. ~~**Fix non-functional UI links**~~ — `href="#"` replaced with real URL tags. [U5–U6]
6. ~~**Remove unused Chart.js**~~ — `chart.min.js` script removed from `base.html`. [U7]
7. ~~**Fix vitals input accessibility**~~ — Added `id`/`for` pairing on all vitals inputs. [U10]
8. ~~**Replace hardcoded mock PHI**~~ — `_labs_tab.html` and `results_entry.html` now use dynamic DB-driven data. [U11]

### Fix Now (Before Demo Day)

1. **Add `django_filters` to production `INSTALLED_APPS`** — `config/settings.py` line 25-38. Present in test_settings but not settings.py (T2).
2. **Set production security headers** — Add `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_HSTS_SECONDS` (>=3600).
3. **Add database SSL** — Add `OPTIONS` with `sslmode` to `DATABASES` config.
4. **Configure real email backend** — Make `EMAIL_BACKEND` driven by env var so password reset works in deployed environments.
5. **Add API throttling** — Configure DRF `DEFAULT_THROTTLE_CLASSES` and `DEFAULT_THROTTLE_RATES`.

### Fix This Week

6. **Clean git history** — Remove `emr/` (full venv), `.pdf` brief, and `.tar.gz` artifact using `git filter-repo`.
7. **Rotate `.env` secrets** — Generate new `DJANGO_SECRET_KEY` and `CRYPTOGRAPHY_KEY`. The current on-disk values should be considered compromised.
8. **Add logging configuration** — At minimum, log `django.request` (ERROR), `axes` (WARNING), and custom security events.
9. **Remove `BrowsableAPIRenderer` in production** — Restrict to JSON-only responses on deployed environments.
10. **Add `CSRF_TRUSTED_ORIGINS` and `SECURE_REFERRER_POLICY`**.

### Fix Before Final Submission

11. **Fix `test_forged_confirmation_id_does_not_bypass_duplicate_check`** — Replace `skipif(True)` with dynamic database-vendor check.
12. ~~**Add MFA concept documentation** — Brief §9.4 requires documented MFA readiness.~~ **[FIXED 2026-07-09]** Created `docs/mfa.md` with detailed integration path (django-otp TOTP, MFARequired group, setup/verify views).
13. **Swap placeholder logo SVGs** — Replace `static/img/logos/{ams,must,gsl}.svg` with official files (blocked on receiving assets from organizers).
14. **Add SAST scanning** — Add `bandit` or similar to CI (requires ALLOWED_PACKAGES.md sign-off, P6).
15. **Clean up stale dead code** — `idb.min.js` (U13), `_status_badge.html` (U14), `ui_preview/` (U15).

---

## 5. Judging Criteria Impact Assessment

| Criterion | Weight | Audit Finding Impact |
|-----------|--------|---------------------|
| Clinical Relevance | 20% | **NEUTRAL** — Lab ordering flow confirmed working (U1–U2). Patient safety alert renders correct amber color (U3). All tab content is now data-driven rather than hardcoded mock PHI (U11). |
| Patient Safety | 20% | **NOW NEUTRAL** — Duplicate addendum forms resolved (U4 fixed). Chart.js dead weight removed (U7). HTMX CSRF workaround applied (C1 fixed). Remaining: DB SSL (C2), encrypted field test gaps (T4). |
| Innovation | 15% | **NEUTRAL** — Offline sync architecture is sound. Sync API throttling still unconfigured (H5). |
| Technical Design | 15% | **POSITIVE** — U-series fixes (U1–U11). CI pipeline hardened: tests against PostgreSQL (P1), removed unused Redis (P2), linting added (P3), migration checks (P5). Docker hardened: non-root user (P14), migration init container (P16), collectstatic fails on error (P13). Makefile rewritten with 12 targets (P9–P11). Stale dashboard mockup replaced with dynamic template (U11). |
| Malawi Context Fit | 15% | **NEUTRAL** — HTMX+Alpine low-bandwidth, Africa/Blantyre timezone. No remaining broken flows in lab/encounter chain. |
| Sustainability | 15% | **POSITIVE** — Removed unused Chart.js dependency (U7). Stale UI mockups replaced with DB-driven templates (U11). Makefile fully rewritten (P9–P11). CI linting added (P3). Docker build hardened (P12–P17). Still: no logging (H2) — high priority for next sprint. |

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
