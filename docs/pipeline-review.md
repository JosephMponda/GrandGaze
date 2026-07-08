# Pipeline & Workflow Review - Jul 4, 2026

Found by manual trace of the end-to-end patient journey through every view, model, form, template, URL, and service function. Ordered by severity.

---

## CRITICAL (crash / silent data loss / unreachable feature)

### C1. `form.notes` referenced in template but does not exist on form
- **File:** `templates/pharmacy/prescribe.html:77`
- **What:** `{% include "components/_field.html" with field=form.notes %}`
- **Why it's broken:** `PrescriptionForm.Meta.fields` is `["encounter", "drug", "dose", "route", "frequency", "duration_days", "safety_override_reason"]`. No `notes` field exists. Template renders invisible empty element - the user sees a blank section where a textarea should be, and any notes they might type are silently discarded.
- **Fix:** Add `notes` to the form's Meta fields, or remove the template reference.

### C2. `form.notes` in dispense template - field is actually `stock_note`
- **File:** `templates/pharmacy/dispense.html:71`
- **What:** `{% include "components/_field.html" with field=form.notes %}`
- **Why it's broken:** `DispensingRecordForm.Meta.fields` is `["quantity_dispensed", "stock_note"]`. The template uses `form.notes` but the actual field is `form.stock_note`. Dispensing staff can never add notes to a dispensing record.

### C3. `patient` not passed to `encounter_detail` template context
- **File:** `encounters/views.py:51-59`
- **What:** View renders with `{"encounter": encounter, "edit_form": edit_form, "addendum_form": EncounterAddendumForm()}` - no `patient` key.
- **Why it's broken:** Template references `patient.full_name`, `patient.patient_number`, `patient.pk|default:0` (for "Back to Patient" URL). All resolve to empty/falsy values. "Back to Patient" link goes to `/patients/0/` (404). Patient identity section shows hardcoded dummy defaults from `|default` filters instead of real data.
- **Fix:** Add `"patient": encounter.patient` to the render context.

### C4. `encounter.date` does not exist on Encounter model
- **File:** `templates/encounters/detail.html:19`
- **What:** `{{ encounter.date|date:"F j, Y"|default:"Today" }}`
- **Why it's broken:** `Encounter` model has `created_at` and `updated_at`, not `date`. The template always shows "Today" regardless of the actual encounter date.
- **Fix:** Change `encounter.date` to `encounter.created_at`.

### C5. "Sign & Complete" button cannot trigger the sign action
- **File:** `templates/encounters/detail.html:28-31`
- **What:** `<button form="encounter-form" type="submit">Sign & Complete</button>`
- **Why it's broken:** View checks `"sign" in request.POST` (encounters/views.py:31). Button has no `name="sign"` attribute, so `sign` is never in POST data. The signing code path is unreachable.
- **Fix:** Add `name="sign"` to the submit button.

### C6. `safety_override_reason` field never rendered in prescribe template
- **File:** `templates/pharmacy/prescribe.html`
- **What:** `PrescriptionForm` includes `safety_override_reason` in its Meta fields, but the template doesn't render `form.safety_override_reason`.
- **Why it's broken:** When drug safety warnings are present, the view (pharmacy/views.py:35-36) requires the user to fill in `safety_override_reason`. Since the field isn't rendered, the user can never see or fill it in. The form re-renders with an invisible validation error - a UX dead end.

### C7. `edit_form` and `addendum_form` passed in context but never rendered
- **File:** `templates/encounters/detail.html`
- **What:** View passes `edit_form` and `addendum_form` (encounters/views.py:51-59). Template ignores both.
- **Why it's broken:** The encounter detail view (lines 31, 39) checks for `"sign"` and `"add_addendum"` in POST data. Neither is reachable through the current template. The "Add Addendum" feature and encounter editing are completely disconnected from the HTML.

---

## HIGH (wrong status checks / unreachable validation / missing GET handler)

### H1. `edit_encounter` has no GET handler - visiting via browser silently redirects
- **File:** `encounters/views.py:63-73`
- **What:** `edit_encounter` immediately binds `request.POST` to `EncounterForm`. No `else` branch for GET.
- **Why it's broken:** Navigating to `/encounters/<pk>/edit/` via GET binds empty POST data → `form.is_valid()` is always False → silent redirect to detail page with no feedback. No edit form is ever displayed.

### H2. Lab result template checks wrong status string `'collected'`
- **File:** `templates/laboratory/result_detail.html:30`
- **What:** `{% elif result.order.status == 'collected' %}`
- **Why it's broken:** `LabOrderStatus` choices define `SPECIMEN_COLLECTED = "specimen_collected"`, not `"collected"`. The condition never matches, so the yellow background styling for collected specimens is dead code.

### H3. `prescription.get_route_display()` called on CharField without choices
- **File:** `templates/pharmacy/dispense.html:28`
- **What:** `{{ prescription.get_route_display|default:"-" }}`
- **Why it's broken:** `Prescription.route` is `CharField(max_length=40)` with no `choices` argument. Django does not generate `get_route_display()` for fields without choices. Template engine catches the `AttributeError` silently and renders "-" regardless of the actual route value. Also affects `get_frequency_display()` if used elsewhere.

### H4. `proceed_with_warnings` uses HiddenInput widget - no visible checkbox
- **File:** `pharmacy/forms.py:7`
- **What:** `proceed_with_warnings = forms.BooleanField(required=False, widget=forms.HiddenInput)`
- **Why it's broken:** The template says "Checking this box confirms you have documented a clinical reason" but the field renders as `<input type="hidden">`. No checkbox exists. The hidden value resets on every form render, so the safety override flow for non-critical warnings cannot be completed by the user.

### H5. `edit_encounter` lacks permission check on who can edit
- **File:** `encounters/views.py:63-73`
- **What:** View only checks `@login_required` and whether the encounter is signed.
- **Why it's broken:** Any authenticated user can POST to `/encounters/<pk>/edit/` and edit any open encounter's clinical documentation, regardless of whether they are the encounter's clinician or have an appropriate role. Violates RBAC (AGENTS.md §7).

### H6. `encounter` form field not rendered in prescribe template
- **File:** `templates/pharmacy/prescribe.html`
- **What:** `PrescriptionForm` includes `encounter` in Meta fields. View sets `form.fields["encounter"].queryset = patient.encounters.all()` (pharmacy/views.py:22).
- **Why it's broken:** The template never renders `form.encounter`. The queryset filtering in the view is wasted effort. Prescriptions cannot be associated with a specific encounter through this form.

### H7. `beds_for_ward` view returns unescaped HTML
- **File:** `inpatient/views.py:85`
- **What:** `return HttpResponse(f'<select ...>{options}</select>')` where `options` is built from `bed.label`
- **Why it's broken:** If a bed label contains HTML special characters (`<`, `>`, `&`), they are not escaped. Low risk (bed labels are alphanumeric from DB), but violates the rule against raw HTML string construction.

---

## MEDIUM (edge-case crashes / missing validation / fragile patterns)

### M1. `RelatedObjectDoesNotExist` risk on `v.ews` access
- **File:** `templates/vitals/_patient_tab.html:12`
- **What:** `{{ v.ews.score|default:"-" }}`
- **Why it's broken:** `v.ews` traverses a OneToOneField to `EarlyWarningScore`. If no EWS exists (edge case: failed computation), Django template engine catches `RelatedObjectDoesNotExist` silently, but the score is lost.

### M2. Sync dispatch uses `get()` without `DoesNotExist` handling
- **File:** `syncapi/dispatch.py:21,30`
- **What:** `Patient.objects.get(pk=payload["patient_id"])`, `Encounter.objects.get(pk=payload["encounter_id"])`
- **Why it's broken:** If a sync payload references a non-existent patient/encounter, `get()` raises `DoesNotExist`. Caught by generic `except Exception` on line 34, but the error message returned to the client is the raw Django ORM message, not a clinical error description. Also, `payload["patient_id"]` could raise `KeyError` if the key is missing.

### M3. Dialysis `record_session` accepts raw POST data without form validation
- **File:** `dialysis/views.py:30-43`
- **What:** `request.POST.get("pre_weight_kg")`, `request.POST.get("post_weight_kg")` - no Django Form.
- **Why it's broken:** No type validation, no bounds checking. Non-numeric input raises `ValidationError` in the model layer → 500 error. No CSRF token validation through forms (though the template includes `{% csrf_token %}` directly).

### M4. Billing invoice creation lacks transaction atomicity
- **File:** `billing/views.py:42-56`
- **What:** Creates an invoice, then adds line items in separate operations. Neither wrapped in `@transaction.atomic`.
- **Why it's broken:** If the second line item creation fails, the invoice and first line item are already committed. Partial invoice with no recovery.

### M5. `pharmacy/queue.html` references dynamically-added `prescription.stock`
- **File:** `templates/pharmacy/queue.html:18`
- **What:** `{% with stock=prescription.stock %}`
- **Why it's broken:** View attaches `p.stock = stock_map.get(p.drug_id)` as a dynamic attribute. If a drug has no `StockLevel`, this is `None`. Template's `{% if stock %}` handles None gracefully, but the pattern is fragile - any future model field named `stock` would silently shadow the dynamic attribute.

### M6. Root URL double-redirects unauthenticated users
- **File:** `config/urls.py:40`
- **What:** `path("", RedirectView.as_view(pattern_name="accounts:dashboard", permanent=False))`
- **Why it's broken:** Unauthenticated user visits `/` → redirect to dashboard → dashboard requires login → redirect to login. Two sequential redirects instead of one. Not a crash, but perceptible delay for users.

### M7. `recent_results_for` fetches all recent results without pruning
- **File:** `laboratory/services.py:35-40`
- **What:** `LabResult.objects.filter(...).order_by("-entered_at")` - no limit
- **Why it's broken:** On a busy lab with thousands of results per patient, this returns all of them. The patient tab only displays a few, so the rest are fetched, serialized, and discarded. Memory waste.

### M8. `verify_result` redirects on GET with no feedback
- **File:** `laboratory/views.py:62-71`
- **What:** Only handles POST. GET silently redirects to `result_detail`.
- **Why it's broken:** Not a crash, but a user navigating to the verify URL via browser gets no feedback - just a redirect with no message.

### M9. `_check_pregnancy_renal_breastfeeding` keyword matching is too broad
- **File:** `pharmacy/safety.py:86`
- **What:** `"renal" in renal_text` - matches any substring
- **Why it's broken:** Matches words like "adrenal" or "renal" in any context, regardless of clinical significance. False positives are acceptable for safety (extra caution), but the approach lacks clinical precision.

### M10. `billing/dashboard` accessible to any authenticated user
- **File:** `billing/views.py:12`
- **What:** `@login_required` only on billing dashboard
- **Why it's broken:** The navbar restricts billing nav links to BillingOfficer/Admin/ICT, but any authenticated user who knows the URL `/billing/` can access the billing dashboard directly. Minor violation of least-privilege.

---

## LOW (dead code / maintenance hazards)

### L1. `dispense_queue.html` is unused, references non-existent fields
- **File:** `templates/pharmacy/dispense_queue.html`
- **What:** References `order.drug_name`, `order.dose_value`, `order.get_route_display`, `order.duration`, `order.instructions` - none exist on `Prescription` model.
- **Why it's a hazard:** If someone wires this template to a view in the future, it will silently show empty values for all fields. Dead code that looks like it should work.

### L2. Encounter detail "Add Prescription" / "Order Labs" buttons are decorative
- **File:** `templates/encounters/detail.html:170-179`
- **What:** `<button type="button" class="btn-secondary ...">` - no HTMX, no JS, no links.
- **Why it's broken:** These buttons do nothing when clicked. They look like action buttons but have no behavior.

### L3. `_generate_patient_number` partial race condition
- **File:** `patients/services.py:66-77`
- **What:** Initial `filter(...).order_by("-patient_number").first()` runs outside the lock.
- **Why it's a risk:** Between the unlocked query and `select_for_update().get_or_create()`, another concurrent request could register with the same prefix. The `max()` on line 74 mitigates this, but the unlocked query is still technically stale.

### L4. Duplicate `max_length` validation in form `clean_*` methods
- **File:** `patients/forms.py:53-63`
- **What:** `clean_national_id`, `clean_phone_number` re-check `max_length` already enforced by model field.
- **Why it's harmless:** Redundant but not harmful. The model field provides a safety net if the form validation is bypassed.

### L5. Dual 403 handlers (middleware + handler403)
- **File:** `config/middleware.py` + `config/urls.py`
- **What:** `PermissionDeniedMiddleware` catches exceptions before Django's WSGI handler, AND `handler403` is set in urls.py for when `DEBUG=False`.
- **Why it's confusing:** Two independent paths to the same outcome. The middleware is active always; `handler403` is a fallback for exceptions that escape the middleware.

### L6. Key rotation breaks hash-based duplicate detection
- **File:** `core/encrypted_fields.py:41-46`
- **What:** `hash_lookup_value()` uses HMAC-SHA256 keyed from `CRYPTOGRAPHY_KEY`/`SECRET_KEY`.
- **Why it's a problem:** After key rotation, existing hashes no longer match, so duplicate detection on national_id/phone_number silently misses matches. Same key derived for both encryption and hashing, so the encrypted values are also lost (handled gracefully via `InvalidToken` fallback).

---

## SUMMARY

| Severity | Count | What |
|---|---|---|
| CRITICAL | 7 | Broken template references, unreachable features, missing context variables |
| HIGH | 7 | Wrong status strings, missing permission checks, invisible form fields |
| MEDIUM | 10 | Edge-case crashes, missing transaction atomicity, fragile patterns |
| LOW | 6 | Dead code, decorative buttons, maintenance hazards |
| **Total** | **34** | |

Next step: user provides instructions on which to fix and priority order.
