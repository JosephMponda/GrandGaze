# Engineer A - Module Spec: Core Platform, Identity & Patient Registration (MPI)

**Django apps owned:** `accounts`, `patients`, plus repo-wide `django-simple-history`/`django-axes`/`django-cryptography` configuration.

**Why this module ships first:** every other engineer's models FK into `Patient` and `User`. This is the critical path. If this slips, everyone slips.

**Brief traceability:** §8.1.1 (Patient Registration/MPI), §9.1 (Clinical Governance Structure - RBAC), §9.3/§9.4 (Legal/Cybersecurity), §12 (User login, role-based dashboard, patient registration/search/profile, audit trail concept).

## 1. Data model

### `accounts` app

```
User (Django's built-in auth.User - do not replace it)
Profile
  - user            OneToOneField(User)
  - role             CharField, choices: NURSE, CLINICIAN, PHARMACIST, LAB_TECH,
                      RADIOGRAPHER, BILLING_OFFICER, ADMIN, ICT
  - department       CharField (free text for MVP; FK to Department in Phase 2)
  - phone_number     EncryptedCharField (django-cryptography)
  - is_active_staff  BooleanField default=True
  - created_at / updated_at
```

Roles map 1:1 to Django `Group` objects (`Nurse`, `Clinician`, `Pharmacist`, `LabTech`, `Radiographer`, `BillingOfficer`, `Admin`, `ICT`). A fixture (`accounts/fixtures/groups_permissions.json`) defines group→permission assignments. **Do not hardcode role checks as `if request.user.profile.role == "NURSE"` scattered through views** - use `@permission_required('app.codename')` or `user.groups.filter(name=...)` via a single `has_role()` helper in `accounts/permissions.py` that every app imports.

### `patients` app

```
Patient
  - patient_number       CharField, unique, auto-generated (format: MUST-YYYYMM-XXXXX)
  - national_id           EncryptedCharField, blank=True (not everyone has one)
  - first_name, last_name, other_names
  - sex                   CharField choices FHIR-aligned: male/female/other/unknown
  - date_of_birth          DateField, null=True
  - age_estimated          BooleanField (Malawi context: DOB often unknown, age estimated)
  - phone_number           EncryptedCharField, blank=True
  - address_line           CharField, blank=True
  - village                CharField, blank=True
  - traditional_authority  CharField, blank=True
  - district               CharField, blank=True
  - region                 CharField choices: Northern/Central/Southern
  - occupation_or_school   CharField, blank=True
  - patient_category       CharField choices: outpatient/inpatient/student/staff/
                            private/referred/emergency/research
  - consent_care            BooleanField default=True
  - consent_teaching         BooleanField default=False
  - consent_research          BooleanField default=False
  - registered_by           FK(User)
  - created_at / updated_at (history via django-simple-history)

NextOfKin
  - patient  FK(Patient, related_name="next_of_kin")
  - name, relationship, phone_number (EncryptedCharField)

PatientMergeRecord
  - primary_patient  FK(Patient, related_name="merged_from")
  - duplicate_patient FK(Patient, related_name="merged_into")
  - merged_by  FK(User)
  - reason  TextField
  - merged_at  DateTimeField auto_now_add=True
  # duplicate_patient stays in DB (never delete clinical history) but is
  # flagged inactive and all views redirect to primary_patient.

ReferralRecord
  - patient  FK(Patient)
  - source        CharField (facility/department name, free text for MVP)
  - destination   CharField
  - reason        TextField
  - created_at
```

## 2. Duplicate detection (patient safety requirement §8.1.1)

On registration, run a fuzzy match against existing patients on: `(first_name, last_name, date_of_birth)` trigram similarity (Postgres `pg_trgm` extension - allowlisted, it's a Postgres extension not a Python package) OR exact `national_id` match OR exact `phone_number` match. If a candidate scores above threshold, block silent creation - show the registering user a "possible duplicate" screen requiring explicit "this is a different person" confirmation before the new record is created. Log that confirmation (who, when, why) - this is a safety-relevant audit event, not optional telemetry.

## 3. Public interface other engineers use

Do not let other apps reach into `Patient` internals beyond what's declared here. Expose in `patients/services.py`:

```python
def get_patient_or_404(patient_id) -> Patient
def search_patients(query: str) -> QuerySet[Patient]
def register_patient(data: dict, registered_by: User) -> Patient
def check_possible_duplicate(data: dict) -> QuerySet[Patient]
```

Every other app's models should `FK(patients.Patient)` for patient linkage - never duplicate patient identity fields into another app's models.

## 4. Views/pages (server-rendered, HTMX partials for search-as-you-type)

- `/login/`, `/logout/` - Django's built-in `LoginView`/`LogoutView`, styled, not rebuilt.
- `/dashboard/` - role-aware landing page: each group sees a different set of quick-links/widgets (this is the "role-based dashboard" MVP requirement). Widget content pulled from each engineer's app via a simple `dashboard_widgets.py` registry pattern - Engineer A defines the registry interface, other engineers register their own widget.
- `/patients/register/` - registration form, duplicate-check HTMX partial fires on blur of name+DOB fields.
- `/patients/search/` - HTMX live search (search-as-you-type against `patient_number`, name, phone).
- `/patients/<id>/` - patient profile: demographics + tabbed HTMX partials for "Visits", "Encounters", "Labs", "Prescriptions", "Billing" - **each tab's content is rendered by the owning engineer's app, included here as an HTMX-loaded partial, not duplicated**.
- `/admin/audit/` - read-only audit trail viewer (wraps `django-simple-history` records) for Admin/ICT roles only. This satisfies §19.4 "audit trail approach" as a visible feature, not just a database table nobody can see.

## 5. Acceptance criteria

- [ ] A user in each of the 8 roles can log in and see a role-appropriate dashboard.
- [ ] A new patient can be registered with all Malawi-context fields (village/TA/district) and gets a unique `patient_number`.
- [ ] Registering a near-duplicate (same name+DOB) blocks silent creation and requires explicit confirmation, logged.
- [ ] Patient search returns results in under 300ms on the seed dataset (500 synthetic patients).
- [ ] Every create/update to `Patient` is visible in the audit trail viewer with actor + timestamp.
- [ ] `phone_number` and `national_id` are stored encrypted at rest (verify by inspecting raw DB column - should not be human-readable).
- [ ] 5 failed logins locks the account for 15 minutes (django-axes).
