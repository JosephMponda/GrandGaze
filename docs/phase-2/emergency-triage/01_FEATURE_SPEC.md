# Phase 2 — Emergency & Triage Module

**Brief traceability:** §8.1.5 (Emergency and Triage Module)
**Dependencies:** `patients.Patient`, `vitals.VitalSignSet`, `accounts` RBAC (all built)
**Django app:** `emergency` (new)

## 1. Data Model

```
TriageEncounter
  - patient             FK(patients.Patient)
  - triaged_by             FK(User)
  - triage_category          CharField choices: immediate/emergency/
                               urgent/standard/non_urgent
  - presenting_condition       TextField
  - rapid_registration             BooleanField default=False  # §8.1.5 minimal data for unstable patients
  - outcome                           CharField choices: discharged/admitted/
                                        referred/dead
  - disposition_note                  TextField, blank=True
  - created_at
  - resolved_at                       DateTimeField null=True

EmergencyVitalSet
  - triage         FK(TriageEncounter, related_name="emergency_vitals")
  - recorded_by       FK(User)
  - vital_sign_set       FK(VitalsSignSet, null=True)  # reference to full vitals if taken
  - time_critical         BooleanField default=False  # §8.1.5 "time-critical event recording"
  - time_critical_note      TextField, blank=True
  - recorded_at

ResuscitationNote
  - triage       FK(TriageEncounter)
  - recorded_by     FK(User)
  - note               TextField
  - recorded_at
```

## 2. Services

```python
def triage_patient(patient, triaged_by, category, condition) -> TriageEncounter
def rapid_register(patient_data, triaged_by) -> tuple[Patient, TriageEncounter]
def record_resuscitation(triage, clinician, note) -> ResuscitationNote
def triage_queue() -> QuerySet[TriageEncounter]
```

## 3. Views

- `/emergency/triage/<patient_id>/` — triage assessment form
- `/emergency/queue/` — triage queue (sorted by category severity)
- `/emergency/rapid-register/` — minimal data registration for unstable patients

## 4. Acceptance Criteria

- [ ] A patient can be triaged with category and presenting condition
- [ ] Rapid registration works with minimal fields (name + sex + age estimate only)
- [ ] Triage queue sorts by severity (immediate first)
- [ ] Outcome links to admission (if admitted) or discharge
- [ ] Tests: triage happy path, rapid registration, queue ordering
