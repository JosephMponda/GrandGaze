# Phase 2 — Inpatient Admission & Ward Management

**Brief traceability:** §8.1.4 (Inpatient and Ward Management)
**Dependencies:** `patients.Patient`, `encounters.Encounter`, `accounts` RBAC (all built)
**Django app:** `inpatient` (new)

## 1. Data Model

```
Admission
  - patient            FK(patients.Patient)
  - admitting_clinician  FK(User)
  - admission_diagnosis  CharField
  - encounter              FK(encounters.Encounter, null=True)  # source encounter
  - status                  CharField choices: active/transferred/
                              discharged/dead
  - admitted_at             DateTimeField auto_now_add=True
  - discharged_at             DateTimeField null=True
  - discharge_disposition       CharField, blank=True  # home/transfer/abscond/death
  - discharge_summary             TextField, blank=True

Ward
  - name          CharField
  - department       CharField, blank=True
  - bed_count          IntegerField

Bed
  - ward         FK(Ward, related_name="beds")
  - label           CharField   # "A-01", "B-12", etc.
  - is_occupied       BooleanField default=False
  - current_admission   FK(Admission, null=True, unique=True)

WardRoundNote
  - admission   FK(Admission, related_name="ward_rounds")
  - clinician     FK(User)
  - note             TextField
  - diagnosis_update  TextField, blank=True
  - plan_update          TextField, blank=True
  - created_at
  - signed_by            FK(User, null=True)
  - signed_at
```

## 2. Services Interface

```python
def admit_patient(patient, clinician, diagnosis, encounter=None) -> Admission
def assign_bed(admission, ward, bed_label) -> Bed
def transfer_patient(admission, target_ward, reason) -> Admission
def discharge(admission, clinician, summary, disposition) -> Admission
def ward_occupancy(ward) -> dict  # {total_beds, occupied_beds, occupancy_rate}
def active_admissions() -> QuerySet[Admission]
```

## 3. Views

- `/inpatient/admit/<patient_id>/` — admission form with bed picker
- `/inpatient/ward/<ward_id>/` — ward dashboard (bed board)
- `/inpatient/admission/<id>/` — admission detail (transfer/discharge actions)
- `/inpatient/admission/<id>/ward-round/` — ward round note entry
- `/inpatient/dashboard/` — bed occupancy summary (dashboard widget)

## 4. Patient Profile Tab

HTMX partial at `/inpatient/patient/<id>/tab/` showing active admission + recent ward rounds.

## 5. Acceptance Criteria

- [ ] A patient can be admitted from an encounter with a diagnosis
- [ ] A bed can be assigned and marked occupied
- [ ] Bed occupancy dashboard shows real counts (total/occupied/free)
- [ ] Transfer creates a new record and frees the previous bed
- [ ] Discharge frees the bed and timestamp is recorded
- [ ] Ward round note can be added to an active admission
- [ ] `django-simple-history` covers all clinical models
- [ ] Tests: admit happy path, transfer, discharge, permission-denied for non-clinician roles
