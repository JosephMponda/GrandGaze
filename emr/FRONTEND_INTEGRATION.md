# Frontend Integration Guide

For the frontend engineer moving from the patient registration page to the
dashboard. Read this before touching templates — the goal is your markup
and my Django views never fight each other.

## The one thing to understand first

Per `AGENTS.md` §3, this is **server-rendered Django templates + HTMX +
Tailwind**, not a separate frontend app talking to an API. There is no
build step, no separate frontend repo, and no REST calls for page content.
Your HTML **is** the Django template — you're not building a static mockup
that later gets "connected", you're editing the actual `.html` files in
`templates/`, keeping the Django template tags (`{{ }}`, `{% %}`) intact and
just changing the surrounding markup/classes.

**If you already built a standalone patient registration page** (plain
HTML/CSS, maybe with placeholder JS): that's fine as a design reference, but
it needs to be merged into `templates/patients/register.html`, not dropped
in beside it. See "How to merge your markup" below.

## Where things live

```
templates/
  base.html                  <- layout shell, nav, messages. Edit this for header/sidebar/nav styling.
  accounts/
    login.html
    dashboard.html            <- YOU ARE HERE NEXT
    audit_trail.html
  patients/
    register.html              <- patient registration page
    profile.html                <- patient profile with Encounters/Vitals tabs
    _search_results.html        <- HTMX partial, patient search dropdown
    _duplicate_warning.html     <- HTMX-rendered duplicate-patient warning
  encounters/  vitals/  reporting/   <- Engineer B's pages, same pattern
```

Static assets go in `static/` (create it) — nothing there yet. Per
AGENTS.md §5: **no CDN pulls, no `npm install`**. Tailwind is a standalone
CLI binary (compile `static/css/input.css` → `static/css/output.css`, commit
the version-pinned binary invocation in a script, not `node_modules`). HTMX
and Alpine are single vendored `.js` files under `static/vendor/`, not
`<script src="https://unpkg.com/...">`. There are `TODO(frontend team)`
comments marking exactly where these wire in, in `templates/base.html`.

## How to merge your markup into `register.html`

Current `templates/patients/register.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>Register Patient</h1>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Register</button>
</form>
{% endblock %}
```

`{{ form.as_p }}` is a placeholder — it auto-renders every field with no
styling. Replace it with your actual markup, but **every input's `name`
attribute must match the form field name exactly** (these map straight to
`Patient` model fields in `patients/forms.py`):

| Field name | Type | Notes |
|---|---|---|
| `national_id` | text | encrypted at rest, max 64 chars (enforced server-side) |
| `first_name` | text | required |
| `last_name` | text | required |
| `other_names` | text | optional |
| `sex` | select | choices: `male`, `female`, `other`, `unknown` |
| `date_of_birth` | date (`type="date"`) | optional |
| `age_estimated` | checkbox | **required if `date_of_birth` is blank** — form validation fails otherwise, with the error attached to this field |
| `phone_number` | tel/text | encrypted, max 32 chars |
| `address_line` | text | encrypted, max 255 chars |
| `village` | text | optional |
| `traditional_authority` | text | optional |
| `district` | text | optional |
| `region` | select | choices: `northern`, `central`, `southern` |
| `occupation_or_school` | text | optional |
| `patient_category` | select | choices: `outpatient`, `inpatient`, `student`, `staff`, `private`, `referred`, `emergency`, `research`. Defaults to `outpatient` if omitted, so it's safe to preselect that option. |
| `consent_care` | checkbox | defaults on |
| `consent_teaching` | checkbox | defaults off |
| `consent_research` | checkbox | defaults off |

Rules that don't change no matter how you style it:
- `{% csrf_token %}` must stay inside the `<form>`, always.
- Keep `method="post"` on the form (or `hx-post` — see below).
- **Do not** rename any `name="..."` attribute — the Django form maps by
  name, not by label/id.
- Server-side validation is the source of truth (AGENTS.md §7 — never trust
  client-side validation alone). Add client-side validation for UX, but the
  page will always re-render with `{{ field.errors }}` if something's wrong
  — style `.errorlist` however you like, don't remove it from the template.

### The duplicate-patient warning flow — don't break this

This is a patient-safety feature, not cosmetic. When a submission looks like
a possible duplicate, the server re-renders
`templates/patients/_duplicate_warning.html` **instead of** redirecting.
That template must keep:
- A visible list of candidate matches (name, patient number, DOB) with a
  "this is a different person" button per candidate.
- Each button POSTs the *original* form data plus a hidden
  `confirmed_not_duplicate_of=<candidate_pk>` field. If you restyle this
  page, keep every original field re-submitted as a hidden input — the
  current template loops `{% for field in form %}` to do this, style around
  that loop, don't remove it.
- A link to open the existing candidate record instead (`patients:profile`
  URL, candidate pk).

If your version of this page doesn't resubmit the full form + the
confirmation field, duplicate-detection silently breaks and patients can get
registered twice — this exact bug existed in an earlier version of this
codebase and was only caught by testing the real HTTP flow. See
`CHANGES_SUMMARY.md` #6.

## Dashboard — what you're building next

`templates/accounts/dashboard.html` currently:

```html
<input type="search" name="q" placeholder="Name, patient number, or phone"
       hx-get="{% url 'patients:search' %}" hx-trigger="keyup changed delay:300ms"
       hx-target="#search-results">
<div id="search-results"></div>
```

This is live-search-as-you-type via HTMX: typing fires a GET to
`/patients/search/?q=...` and swaps the response into `#search-results`.
Keep the `hx-get`, `hx-trigger`, `hx-target` attributes — restyle the input
and results container freely, but don't switch this to a JS fetch() call;
HTMX is the whole point of the stack (AGENTS.md §3, no client-side router,
no separate API auth story).

Below that, role-based quick-links:

```html
{% for w in widgets %}
    <li><a href="{% url w.url_name %}">{{ w.title }}</a></li>
{% endfor %}
```

`widgets` is a list of `{title, url_name, icon}` dicts, already filtered
server-side to the logged-in user's role — you don't need to know or check
roles in the template, just render what's given. Currently one widget is
registered ("Patients with abnormal vitals (last 4h)" → `reporting:recent_alerts`,
visible to Nurse/Clinician/Admin). More will appear automatically as
Engineers C/D/E register theirs via the same `accounts.dashboard_widgets`
registry — you don't need to hardcode links to their pages, the loop
picks them up.

If you want an icon per widget, `icon` is already passed through (currently
just a string like `"alert-triangle"` — map it to whatever icon set you're
using; nothing server-side depends on its value).

## Running it locally against a real backend

You need Postgres running (see root `README.md` "Running locally" section)
— the duplicate-detection fuzzy matching genuinely requires Postgres's
`pg_trgm` extension and will error on sqlite. Fastest path:

```bash
pip install -r requirements.in --break-system-packages
cp .env.example .env   # edit DB_* to point at your local Postgres
python manage.py migrate
python manage.py loaddata accounts/fixtures/groups_permissions.json
python manage.py createsuperuser
python manage.py runserver
```

Then log in and hit `/patients/register/` and `/accounts/dashboard/`
directly — no separate frontend dev server, no proxy config needed.

## Questions to raise, not guess on

If something needs a field that doesn't exist yet on `Patient` (e.g. a photo
upload, biometric placeholder), or a dashboard widget layout that doesn't
fit the simple list-of-links pattern above — flag it rather than adding a
new model field or route yourself. Per `AGENTS.md` §4, `patients`/`accounts`
are Engineer A's frozen contract; changes go through a 1-line PR everyone's
tagged on, not a silent frontend-driven schema change.
