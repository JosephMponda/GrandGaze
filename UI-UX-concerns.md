# UI/UX Concerns

**Date:** 2026-07-09  
**Audit method:** Manual inspection of every template file against WCAG 2.1 AA, clinical workflow usability, mobile responsiveness, and brief §7.2 (Simplicity and Usability) requirements.

---

## Critical (Must Fix Before Demo)

### C1 — Form field errors are not announced by screen readers

**File:** `templates/components/_field.html`  
**Issue:** When a form field has a validation error, the error `<div>` has `role="alert"` but the `<input>`/`<select>`/`<textarea>` does not have `aria-describedby` pointing to the error element's ID. Screen readers will not automatically announce the error when the field receives focus.  
**Fix:** Add dynamic `aria-describedby` to the input element when errors exist.

### C2 — Clinical Notes textarea has broken label association

**File:** `templates/vitals/entry.html` (lines 258–261)  
**Issue:** The `<label>` reads "Clinical Notes / Comments" but has no `for` attribute. The `<textarea>` element has no `id` attribute. These two elements are siblings, not nested — the implicit association is broken.  
**Fix:** Give the `<textarea>` an `id` and update the `<label>` with a matching `for`.

### C3 — Connection status dot is color-only with no text alternative

**File:** `templates/base.html` (lines 66–69)  
**Issue:** The online/offline connection indicator uses a green dot (online) or red dot (offline) with `animate-pulse`. No `aria-label`, `sr-only` text, or `title` attribute communicates the status to screen readers.  
**Fix:** Add `<span class="sr-only">Online</span>` / `<span class="sr-only">Offline</span>` conditionally.

### C4 — Idle timer warning not announced to screen readers

**File:** `templates/base.html` (lines 73–78)  
**Issue:** The session idle warning toast has no `role="alert"` or `aria-live="polite"`. A visually-impaired user will not know the session is about to expire.  
**Fix:** Add `role="alert"` to the idle warning container.

---

## High (Should Fix Before Demo)

### H1 — Tab system has no ARIA roles

**File:** `templates/patients/profile.html` (tab navigation, lines ~99–169)  
**Issue:** The 9-tab navigation uses `<button>` elements (correct) and `x-show` for panel visibility (correct), but none of the following ARIA attributes are present:
- `role="tablist"` on the tab container  
- `role="tab"` on each tab button  
- `role="tabpanel"` on each content panel  
- `aria-selected` on the active tab  
- `aria-controls` on tabs pointing to panel IDs  
- `aria-labelledby` on panels pointing to tab IDs  

**Fix:** Add all six ARIA attributes. This is the single largest accessibility gap in the application.

### H2 — Login form missing autocomplete attributes

**File:** `templates/accounts/login.html`  
**Issue:** Neither username nor password fields have `autocomplete="username"` / `autocomplete="current-password"`. Users relying on password managers will not get automatic fill.  
**Fix:** Add `autocomplete` attributes to the login form fields. Django renders them via `_field.html` which doesn't pass autocomplete. Either modify `_field.html` to accept `widget_attrs` or add them in the form class.

### H3 — AVPU radio buttons not in a `<fieldset>`

**File:** `templates/vitals/entry.html` (lines ~186–198)  
**Issue:** The AVPU consciousness selector uses radio buttons styled as cards with `sr-only peer` pattern. The radio group is not wrapped in `<fieldset>` with `<legend>`. Screen readers will not group the options together semantically.  
**Fix:** Wrap the AVPU radio group in `<fieldset>` with `<legend>Level of Consciousness</legend>`.

### H4 — Billing formset line items not in `<fieldset>`

**File:** `templates/billing/create_invoice.html` (lines ~53–59)  
**Issue:** Each line item in the formset should be wrapped in `<fieldset>` with a `<legend>` identifying the line item number. Currently they are plain `<div>` elements.  
**Fix:** Wrap each line item card in `<fieldset><legend>Item #N</legend>...</fieldset>`.

### H5 — Partial clearance checkbox label in _field.html

**File:** `templates/components/_field.html`  
**Issue:** The `<label>` element has no CSS styling classes. Every form label in the application renders as unstyled text (`block text-sm font-medium text-gray-700` expected). This is a visual consistency issue across all forms.  
**Fix:** Add `class="block text-sm font-medium text-gray-700"` to the label in `_field.html`.

### H6 — Search results not in an ARIA live region

**File:** `templates/accounts/dashboard.html` (line 39, `#search-results`)  
**Issue:** The HTMX-powered patient search populates results into a `<div>` without `role="status"` or `aria-live="polite"`. Screen readers won't announce when search results appear.  
**Fix:** Add `role="status" aria-live="polite"` to `#search-results`.

---

## Medium (Fix When Convenient)

### M1 — Navigation links not in `<ul><li>` lists

**File:** `templates/base.html` (lines 27–40)  
**Issue:** Both desktop and mobile nav use `<div>` and `<a>` elements directly, not `<ul><li>` for list semantics.  

### M2 — "Clear" button in vitals capture does nothing

**File:** `templates/vitals/partials/_capture_form.html` (line ~213)  
**Issue:** The "Clear" button is `<button type="button">` with no Alpine `@click` handler. Clicking it has zero effect. Likely a bug.

### M3 — Alert banner missing `role="alert"`

**File:** `templates/components/_alert_banner.html`  
**Issue:** The alert banner container does not have `role="alert"`. Visually it's prominent but screen readers won't be notified.

### M4 — HTMX script blocks rendering

**File:** `templates/base.html` (line ~286)  
**Issue:** HTMX is loaded without the `defer` attribute. It blocks HTML parsing while downloading. Alpine.js correctly uses `defer`.  

### M5 — Encounter detail clinical plan uses raw textarea

**File:** `templates/encounters/detail.html` (line ~193)  
**Issue:** The clinical plan field is a raw `<textarea name="clinical_plan">` not rendered through Django's form framework. Server-side validation of this field depends on the edit view's form — but this raw textarea bypasses the form's validation and CSRF protection.  

### M6 — Tab system URL hash conflict

**File:** `templates/patients/profile.html`  
**Issue:** The Alpine tab system uses `window.location.hash` for deep-linking but does not handle the case where the hash matches a tab that hasn't loaded its HTMX content yet. On initial load, the content panel is empty because HTMX trigger fires after the tab switch.

---

## Low (Nice-to-Have)

### L1 — Stat cards use `<div>` not `<article>`

**File:** `templates/reporting/analytics_dashboard.html`  
**Issue:** Analytics stat cards use `<div>` elements rather than `<article>` or `<section>` for document structure semantics.

### L2 — Mobile menu not `<nav>` with `aria-label`

**File:** `templates/base.html`  
**Issue:** The mobile navigation panel is not wrapped in a `<nav>` element with `aria-label="Main navigation"`. The desktop nav also lacks this.

### L3 — Missing empty states on tab panels

**File:** `templates/patients/profile.html` (all tab panels)  
**Issue:** Tab panels are lazy-loaded via HTMX. If the backend returns empty data, the template for each tab (e.g., `_visits_tab.html`) should handle the empty state gracefully. Some tabs may not have empty-state handling.

### L4 — No loading indicator on form submissions

**File:** Multiple (vitals/entry, lab/order, etc.)  
**Issue:** Many HTMX form submissions have no loading state on the submit button. HTMX provides `htmx-request` class but it's not styled or used for spinner feedback.

### L5 — No inline validation feedback

**File:** Multiple  
**Issue:** All form validation is server-side. No client-side validation with real-time feedback (though Alpine live NEWS2 scoring is an exception). Django's browser-side form validation (required/min/max attributes) partially mitigates this.

---

## Positive Highlights

The following UI/UX elements are well-executed and should be preserved:

1. **Consistent design system** — Four shared partials (`_field.html`, `_alert_banner.html`, `_empty_state.html`, `_status_badge.html`) create a unified look across all 76 templates.

2. **Live NEWS2 scoring** — Both `vitals/entry.html` and `vitals/partials/_capture_form.html` implement real-time clinical risk calculation with color-coded risk badges. This is a standout innovation feature.

3. **Three-state prescribing safety** — Blocked/Warning/Clear safety states in `pharmacy/prescribe.html` with context-aware CTA buttons ("Proceed with documented reason") — excellent patient safety UX.

4. **Responsive mobile behaviour** — Every template uses consistent responsive patterns: `flex-col sm:flex-row` for buttons, `grid-cols-1 sm:grid-cols-2 md:grid-cols-3` for fields, `p-4 sm:p-6 sm:p-8` for padding.

5. **Immersive clinical workspace** — `encounters/detail.html` removes the nav bar for a full-width split-pane layout appropriate for focused clinical work.

6. **Deep-linkable patient tabs** — URL hash routing (`window.location.hash`) in profile tab system enables direct links to specific patient data sections.

7. **Malawi-context fields** — Traditional Authority, village, mobile money payment options in registration and billing forms.

8. **Offline awareness** — Connection dot with pulse animation, offline indicator banner, `data-offline-capable` attributes on forms — all signal system resilience awareness to users.

9. **Session idle timer** — 13-minute warning with live countdown, auto-logout at 15 minutes, resets on any user interaction.

---

## Summary

| Severity | Count | Action |
|----------|-------|--------|
| Critical | 4 | Fix before demo (C1–C4) |
| High | 6 | Fix before demo (H1–H6) |
| Medium | 6 | Fix this week (M1–M6) |
| Low | 5 | Nice-to-have (L1–L5) |

**Estimated effort to resolve all critical + high items:** 3–4 hours of template editing.
