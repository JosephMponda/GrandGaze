# Reference Alignment — MUST–GSL EMR vs Industry Standards

> Per brief §27, judges were told to study OpenMRS [11], FHIR [7], 
> LOINC [9], DICOM [8], and ICD-11 [10] for "inspiration." This document
> records where our system aligns, where it deliberately differs, and why.

---

## [11] OpenMRS — Reference EMR Platform

### Shared Design Patterns

| OpenMRS 3.x Feature | Our Equivalent | Notes |
|---|---|---|
| Patient banner (demographics at top of chart) | `patients/profile.html` — patient info card at top | Similar layout; we use Tailwind not Carbon |
| Tabbed patient chart (Summary, Results, Orders, Encounters, Conditions, Programs, Allergies, Appointments) | 6-tab patient profile (Encounters, Vitals, Labs, Imaging, Medications, Billing) — HTMX-loaded | Fewer tabs but same pattern; we combine Summary + Results into the tab content |
| Search-as-you-type patient search | HTMX live search with `hx-trigger="keyup changed delay:300ms"` | Same UX; server-side rendering instead of JS client-side filter |
| Status badges (severity colors) | `_status_badge.html` — success/warning/critical/info tailwind pills | Same visual semantics |
| Role-based dashboard | Widget registry per role (dashboard loops `widgets_for_user()`) | OpenMRS uses config-driven dashboards; we use a simpler registry pattern |
| Offline mode | Service worker + IndexedDB + `syncapi` endpoint | OpenMRS 3 has a similar offline strategy with IndexedDB + sync |
| Duplicate patient warning | Blocking interstitial with accordion-style candidate list + "confirm different person" per candidate | Directly inspired by OpenMRS pattern (see OpenMRS Talk thread 46046) |
| Audit trail | `django-simple-history` viewer for Admin/ICT | OpenMRS uses a similar concept with their "Audit Log" module |

### Deliberate Differences

| OpenMRS Approach | Our Approach | Rationale |
|---|---|---|
| Microfrontend SPA (React + Carbon Design) | Server-rendered Django templates + HTMX + Alpine + Tailwind | Per brief: "loads fast, feels responsive" on low bandwidth. Our approach wins on first paint and CDN-free offline operation. |
| Carbon Design System (IBM) | Custom Tailwind theme (ink/brand/success/warning/critical) | Zero external CSS framework dependency; smaller payload. |
| FHIR as primary data API | Django ORM + FHIR as read-only export | AGENTS.md §3: "not building a full parallel API for a server-rendered app." FHIR export exists as a bonus, not the primary interface. |
| REST API for all CRUD | Django views for CRUD; DRF only for sync + FHIR export | CORS-less, auth-less, simpler — one stack does everything. |
| JWT-based auth | Django sessions | Built-in, secure, no token management. |

### Visual Alignment Check

| Dimension | OpenMRS 3 | Our System |
|---|---|---|
| Navigation | Top bar + left sidebar | Top bar with role-gated dropdown + mobile hamburger |
| Patient header | Card with name, age, sex, ID, status badge | Card with name, patient_number, DOB, sex, category |
| Tab interface | Horizontal tabs under header | Horizontal tabs under patient info, HTMX-powered |
| Form fields | Carbon-styled inputs with inline validation | Tailwind-styled fields via `_field.html` reusable partial |
| Tables | Zebra-striped with sortable headers | Tailwind tables with status badges |
| Alerts/modals | Modal overlay for critical actions | HTMX-rendered warning panels + banners |
| Mobile | Responsive down to 360px | Responsive via Tailwind breakpoints |

**Conclusion**: Our UI conventions follow the same clinical-information hierarchy as OpenMRS 3.x but rendered via server-side HTML. The tabbed patient chart, search-as-you-type, duplicate warning flow, and role-based dashboard are all directly comparable to OpenMRS patterns.

---

## [7] HL7 FHIR — Health Data Exchange Standard

### FHIR Compatibility

| FHIR Resource | Our Equivalent | Interop Readiness |
|---|---|---|
| Patient | `patients.Patient` | FHIR-Bundle serializer maps fields: `name.given` = first_name, `name.family` = last_name, `gender` = sex, `birthDate` = date_of_birth, `identifier` = patient_number + national_id |
| Encounter | `encounters.Encounter` | Included in `/api/interop/patient/<id>/bundle/` with `period`, `type`, `status` mapped |
| Observation | `vitals.VitalSignSet` + `laboratory.LabResult` | Vital signs mapped as FHIR `Observation` with `category= vital-signs`; labs as `category= laboratory` |
| MedicationRequest | `pharmacy.Prescription` | Mapped in bundle with `medicationCodeableConcept`, `dosageInstruction` |
| AllergyIntolerance | `encounters.AllergyRecord` | Available for inclusion but not yet in interop bundle |
| DiagnosticReport | `laboratory.LabResult` + `imaging.ImagingReport` | Lab and imaging results serialized as DiagnosticReport resources |

### FHIR Design Decisions

- **Read-only export**: We serve FHIR-shaped JSON but don't accept FHIR writes. This matches brief §7.5's "FHIR readiness" without overbuilding a HAPI FHIR server.
- **No full conformance claim**: OpenAPI docs preface states this is "FHIR-inspired export for interoperability readiness" — per AGENTS.md §8.
- **Client UUID approach**: Our sync API uses `client_uuid` for idempotency instead of FHIR's `id` mechanism — simpler for intermittent connectivity scenario.

---

## [9] LOINC — Laboratory Coding Standard

- `LabTest.loinc_code` nullable CharField on every test in the catalog
- 6 seeded tests carry real LOINC codes: 
  - Full Blood Count (loinc: 58410-2)
  - Malaria RDT (loinc: 87591-4)
  - Creatinine (loinc: 2160-0)
  - HIV Rapid Test (loinc: 75622-1)
  - Blood Glucose (loinc: 2345-7)
  - Urinalysis (loinc: 24356-8)
- Non-populated tests left blank — never faked (per AGENTS.md §8)
- Future: full LOINC mapping on all ~30 seed tests

---

## [8] DICOM — Medical Imaging Standard

- **Metadata-only**: Our imaging module stores request + report metadata, not image files
- `image_reference` CharField on `ImagingReport` stores a file path / URL placeholder — "image-link concept" per brief §8.2.1
- No PACS/RIS integration attempted — noted as future scope (§8.2.1: "Integration-ready design for PACS/RIS")
- Pregnancy-status safety gate on imaging requests for applicable modalities (X-ray, CT, fluoroscopy) — aligned with DICOM safety recommendations

---

## [10] ICD-11 — Diagnosis Coding

- `Encounter.diagnosis` is currently a free-text CharField
- No structured ICD-11 code field yet — noted as future scope
- Field naming convention in `Encounter` is ICD-shape-compatible (`diagnosis` field can store code | text)
- Future: add `diagnosis_code` CharField + picker widget

---

## [2] WHO Global Strategy on Digital Health 2020–2025

Our system aligns with WHO recommendations through:
- **Interoperability-first data model**: FHIR-shape-compatible fields, LOINC-ready lab catalog
- **Security by design**: Role-based access, field-level encryption, audit trails
- **Offline-first**: Sync queue + service worker for intermittent connectivity
- **Low-resource optimization**: Server-rendered HTML, no JS framework overhead, 150KB page budget
- **Sustainability**: Free-tier infrastructure (Render + Neon), open-source stack

## [3]/[4] Malawi Digital Health Strategy / Governance Framework

- Patient identification uses village + Traditional Authority + district + region — directly from Malawi health system structure
- Mobile money billing field for the dominant payment method in Malawi
- Age-estimated workflow for patients without known DOB — common in rural Malawi
- Local server Docker fallback for clinics without internet (brief §10 explicit requirement)

---

## Summary: Where We Score vs References

| Criterion | OpenMRS [11] | Our System | Advantage |
|---|---|---|---|
| Online-first UX | SPA with offline support | Server-rendered + HTMX + offline sync | **Us** — faster first paint |
| FHIR support | Full FHIR server module | FHIR read-only export | **Both** — we claim "readiness" not full conformance |
| Design system | Carbon Design (IBM) | Custom Tailwind theme | **Both** — neither is wrong |
| Offline sync | IndexedDB + REST | IndexedDB + syncapi DRF | **Both** — same approach |
| Dependency footprint | Large (npm, React, Carbon) | Minimal (pip + vendored JS) | **Us** — per brief sustainability criteria |
| Deploy complexity | Java + Tomcat + MySQL | Python + Postgres + Docker | **Us** — simpler stack for local maintenance |
