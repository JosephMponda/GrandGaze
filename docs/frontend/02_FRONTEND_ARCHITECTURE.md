# Frontend 02 — Architecture

How the frontend is actually built, wired to Django, and made offline-capable. Read root `AGENTS.md` §3 and §6 first — this file is the implementation detail underneath those decisions.

## 1. The pattern: Django Templates + HTMX + Alpine.js + Tailwind

- **Django views render full pages** on direct navigation (GET `/patients/42/`) and **render small HTML fragments** on HTMX-triggered requests (`GET /patients/42/labs-tab/` returns just the labs tab content, no `<html>`/`<head>`, no nav).
- **The same Django view function can often serve both**, branching on the `HX-Request` header — if HTMX-triggered, return just the inner template block; otherwise return the full page wrapping it. Django's `{% block %}` + a small `if request.htmx:` check (via `django-htmx`, request this be allowlisted — it's tiny, well-maintained, exactly this one job) is the standard, low-code way to do this. Don't hand-roll HTMX header detection in every view.
- **Alpine.js handles purely client-side, no-server-round-trip interactivity**: toggling a mobile nav, a live character counter, the idle-session-timeout warning banner, client-side BMI preview before server-authoritative save. If it needs to touch the database, it's an HTMX request to Django, not an Alpine `fetch()` call — don't build a second, informal API surface through ad-hoc `fetch()` calls scattered in Alpine components.
- **Tailwind CSS** compiled via the standalone CLI binary (no Node/npm build step, no `node_modules`) into one `static/css/app.css`, purged to only the classes actually used. Rebuild step is a single command (`tailwindcss -i input.css -o static/css/app.css --minify`) wired into a pre-commit hook or a Makefile target — every engineer runs the same command, no snowflake local setups.

## 2. Directory structure

```
templates/
  base.html                 # shell: <head>, nav, block content
  components/
    _field.html              # form field partial (design system §5)
    _status_badge.html
    _alert_banner.html
    _table.html               # optional generic table wrapper
    _empty_state.html
  patients/
    profile.html               # full page, includes tab shell
    _tab_encounters.html         # HTMX-loaded fragment
    _tab_vitals.html
    _tab_labs.html
    _tab_imaging.html
    _tab_medications.html
    _tab_billing.html
    register.html
    _search_results.html          # HTMX live-search fragment
  dashboard/
    index.html
    _widget_*.html                  # one partial per registered dashboard widget
  <app>/...                          # each backend app's own templates live under its own namespace, owned by the backend engineer who owns that app — frontend engineers pair with them, not replace them
static/
  css/app.css                        # Tailwind build output, committed
  css/input.css                       # Tailwind source with @tailwind directives + custom component classes
  js/htmx.min.js                       # vendored, version pinned in a comment header
  js/alpinejs.min.js                    # vendored, version pinned
  js/idb.min.js                          # vendored, ~1KB, for the offline outbox
  js/app.js                               # our own small glue code: service worker registration, sync-queue logic
  js/sw.js                                 # service worker
  chart.min.js                              # vendored Chart.js for trend/dashboard charts
```

**Vendoring rule** (ties to root `AGENTS.md` §5): HTMX, Alpine, idb, Chart.js are downloaded once from their official release pages, checked into `static/js/` with a version comment at the top of each file, and never pulled from a CDN at request time or installed via `npm`. Update = manually swap the file and bump the version comment, reviewed like any other dependency change.

## 3. Who owns what template

Backend engineers own the templates for their own app's pages/fragments (they know the data shape best and are writing the views anyway) — frontend engineers **pair with them** to apply the design system correctly, build the trickier interactive pieces (HTMX/Alpine wiring, the offline queue, chart rendering), and hold the line on the component inventory so five different backend engineers' pages don't visually drift apart. Concretely: a backend engineer should never invent a new button style or a new table layout — they use `components/_field.html` etc. If a component is missing, that's a conversation with the frontend team, not a one-off template.

## 4. Offline-first implementation detail

Implements the pattern from root `AGENTS.md` §6, backend half in `syncapi` (Engineer E). Frontend half:

1. **Service worker** (`static/js/sw.js`): on install, caches `base.html`'s static assets (CSS/JS/fonts) and a small set of "app shell" routes (login page, dashboard shell). On fetch, network-first with cache fallback for GET requests; for HTMX form POSTs, see step 2.
2. **Outbox queue**: forms marked with a `data-offline-capable="true"` attribute (only the specific MVP forms named in root `AGENTS.md` §6 — vitals entry, encounter note, patient registration — not every form in the app) are intercepted by `app.js`. On submit:
   - Generate a `client_uuid` (crypto.randomUUID()).
   - Try the HTMX request normally.
   - If it fails due to network error (not a validation error — a 4xx from the server is a real error and must surface to the user normally, not get queued), store `{client_uuid, form_type, payload, timestamp}` in IndexedDB via `idb`, show a clear "saved offline, will sync when connected" confirmation (not a silent failure, not a generic error).
3. **Sync replay**: on `online` event (or a manual "sync now" button, always available since auto-detection isn't perfectly reliable), `app.js` reads the IndexedDB outbox and POSTs each queued item to `/api/sync/submit/` in order, using the stored `client_uuid`. On success, remove from the local outbox and show a toast. On a `conflict` status in the response, keep it in a visible "needs attention" list rather than silently discarding it — a human (the clinician who submitted it, or an admin) needs to see and resolve it.
4. **Visual indicator, always present**: a small persistent connection-status indicator (online/offline/syncing/N pending) in the nav shell — this is a real judged feature (offline-first architecture is explicitly a bonus recognition area, §22) and needs to be visible and demonstrable, not just working invisibly under the hood.

## 5. Performance checklist (ties to design system §6's 150KB budget)

- No render-blocking third-party scripts, ever.
- Images (if any — mostly this app is text/data-dense, not image-heavy) served via `whitenoise` with cache headers, compressed, correctly sized — no full-resolution image dumped into a small UI slot.
- Tailwind build is purged (unused classes stripped) — verify the final `app.css` size, not just that the build "worked."
- Charts (Chart.js) only loaded on pages that actually render one — don't include it in the global `base.html` script list.
- Test actual load time on a throttled connection (Chrome DevTools "Slow 3G" preset) before calling a page done — this is the honest way to verify the "loads fast on intermittent connectivity" claim rather than assuming it from a fast office Wi-Fi test.

## 6. What NOT to build here

- No client-side router, no SPA navigation — full page loads for primary navigation, HTMX only for in-page fragment swaps (tabs, search results, form responses).
- No client-side state management library (Redux, Zustand, etc.) — Alpine's small per-component `x-data` state is sufficient for what this app needs, and anything needing more than that almost certainly needed a server round-trip anyway.
- No client-side form validation library — Django's server-side `ModelForm` validation is authoritative; Alpine can add lightweight instant feedback (e.g. "passwords don't match" before submit) but it is never the only validation, per root `AGENTS.md` §7.
