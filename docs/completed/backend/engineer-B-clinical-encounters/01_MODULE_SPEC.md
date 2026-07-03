# Engineer B - Module Spec: Clinical Encounters & Vital Signs

**Django apps owned:** `encounters`, `vitals`.

**Depends on (frozen by end of Day 2):** `patients.Patient`, `accounts.Profile`/RBAC helpers from Engineer A.

**Brief traceability:** §8.1.3 (Outpatient Clinical Documentation), §8.1.7 (Vital Signs/Observations), §8.1.8 (Provider Documentation), §9.2 (Patient Safety Framework - abnormal vital triggers), §12 MVP ("clinical encounter documentation", "vital signs entry").

## 1. Data model

### `encounters` app

```
Encounter
  - patient          FK(patients.Patient)
  - clinician         FK(User)
  - encounter_type    CharField choices: outpatient/emergency/follow_up
  - status             CharField choices: open/closed
  - presenting_complaint  TextField
  - history_of_presenting_complaint  TextField, blank=True
  - past_medical_history  TextField, blank=True
  - past_surgical_history TextField, blank=True
  - medication_history     TextField, blank=True
  - allergy_history         TextField, blank=True   # structured AllergyRecord below is the real safety data; this is free-text context
  - social_history           TextField, blank=True
  - family_history            TextField, blank=True
  - examination_findings       TextField, blank=True
  - diagnosis                    CharField, blank=True
  - differential_diagnosis        TextField, blank=True
  - clinical_plan                  TextField, blank=True
  - signed_by  FK(User, null=True)   # explicit "clinician signature" per §8.1.3
  - signed_at  DateTimeField null=True
  - created_at / updated_at (history via django-simple-history)

AllergyRecord
  - patient  FK(patients.Patient, related_name="allergies")
  - allergen  CharField
  - reaction  CharField, blank=True
  - severity  CharField choices: mild/moderate/severe
  - recorded_by FK(User)
  - recorded_at DateTimeField auto_now_add=True
  # THIS is the model Pharmacy (Engineer D) queries for allergy-alert checks
  # at prescribing time. Patient-level, not encounter-level, because an
  # allergy known from one encounter must alert on every future prescription.

ClinicalTemplate
  - name        CharField      # "structured templates for common clinics" §8.1.3
  - specialty    CharField, blank=True
  - fields_json   JSONField    # simple structured field definitions for MVP
```

### `vitals` app

```
VitalSignSet
  - encounter          FK(encounters.Encounter, related_name="vitals")
  - patient              FK(patients.Patient)  # denormalized for fast history queries independent of encounter
  - recorded_by            FK(User)
  - temperature_c            DecimalField null=True
  - blood_pressure_systolic   IntegerField null=True
  - blood_pressure_diastolic   IntegerField null=True
  - pulse_rate                  IntegerField null=True
  - respiratory_rate             IntegerField null=True
  - oxygen_saturation             IntegerField null=True
  - weight_kg                      DecimalField null=True
  - height_cm                       DecimalField null=True
  - bmi                              DecimalField null=True, auto-calculated on save
  - pain_score                        IntegerField null=True  # 0-10
  - blood_glucose                      DecimalField null=True
  - glasgow_coma_scale                   IntegerField null=True
  - pregnancy_status                      CharField choices: n/a/pregnant/not_pregnant/unknown
  - recorded_at  DateTimeField auto_now_add=True

EarlyWarningScore
  - vital_sign_set  OneToOneField(VitalSignSet)
  - score             IntegerField     # computed, see §2
  - risk_level          CharField choices: low/medium/high/critical
  - computed_at
```

## 2. Early Warning Score (patient safety - this is a real judged feature, build it for real)

Implement a simplified adult EWS in `vitals/scoring.py` as a pure function `compute_ews(vital_sign_set) -> (score, risk_level)`, based on standard published banding (temp, BP, pulse, resp rate, SpO2, GCS each contribute 0–3 points, summed). Keep the thresholds in a single constants dict at the top of the file so they're easy to defend/adjust to judges' questions, and add a `# TODO: pediatric-adjusted variant, Phase 2` note - the brief explicitly calls out §8.1.7 "pediatric age-adjusted vital sign alerts" as future scope, don't silently claim you built pediatric EWS if you built adult-only.

**Abnormal value alert**: any vital outside a hard safety threshold (e.g. SpO2 < 90%, temp > 39.5°C) fires a same-page HTMX banner/toast immediately on save, and creates an `AlertEvent` (owned by Engineer E's `reporting` app - call `reporting.services.raise_alert(...)`, don't build a second alerting system here).

## 3. Public interface other engineers use

`encounters/services.py`:
```python
def get_open_encounter(patient) -> Encounter | None
def create_encounter(patient, clinician, data) -> Encounter
def get_patient_allergies(patient) -> QuerySet[AllergyRecord]   # <- Pharmacy calls this
```

`vitals/services.py`:
```python
def latest_vitals(patient) -> VitalSignSet | None
def vitals_trend(patient, limit=10) -> QuerySet[VitalSignSet]   # for trend charts
```

## 4. Views/pages

- `/encounters/patient/<id>/new/` - new encounter form (structured sections matching §8.1.3 fields).
- `/encounters/<id>/` - encounter detail/edit, sign-off action (locks the record once signed - further edits create an addendum, they don't silently rewrite signed clinical documentation, which would be a governance red flag to judges).
- `/vitals/patient/<id>/entry/` - vitals entry form, HTMX partial that returns the EWS badge + trend sparkline immediately on submit.
- Patient-profile "Encounters" and "Vitals" tabs (HTMX partials, plug into Engineer A's patient profile template blocks).
- Dashboard widget: "patients with abnormal vitals in the last 4 hours" (register via Engineer A's `dashboard_widgets.py`).

## 5. Acceptance criteria

- [ ] A clinician can open an encounter, complete all §8.1.3 structured fields, and sign it.
- [ ] Once signed, the encounter is read-only in the UI; edits require an addendum flow, both are visible in the audit trail.
- [ ] Vitals entry auto-computes BMI and EWS on save.
- [ ] An out-of-range vital fires a visible alert within the same request/response cycle (no polling delay).
- [ ] `get_patient_allergies()` returns correct data when called from a throwaway Pharmacy test - this is the cross-module safety contract, test it explicitly.
- [ ] Vitals trend chart renders on the patient profile with at least 3 data points from seed data.
