# Engineer D — Module Spec: Pharmacy, Prescribing & Medication Safety

**Django apps owned:** `pharmacy`.

**Depends on (frozen by end of Day 2/3):** `patients.Patient`, `encounters.Encounter` + `encounters.services.get_patient_allergies()` (Engineer B — hard blocker for the safety-check feature, not just a nice-to-have), `accounts` RBAC.

**Brief traceability:** §8.1.11 (Pharmacy, Prescribing, Medication Safety), §9.2 (allergy alerts, duplicate order prevention, pediatric dosing safeguards), §12 MVP ("prescription entry and dispensing status").

## 1. Data model

```
Drug  # catalog, seed ~30 common drugs relevant to Malawi primary/secondary care
  - name              CharField
  - generic_name         CharField
  - formulation             CharField (tablet/syrup/injection/etc.)
  - is_controlled              BooleanField default=False
  - pediatric_max_dose_mg        DecimalField null=True   # simple safeguard basis, see §2
  - contraindicated_in_pregnancy   BooleanField default=False
  - contraindicated_in_renal          BooleanField default=False

DrugAllergyMap
  - drug     FK(Drug)
  - allergen_keyword  CharField   # simple keyword match against AllergyRecord.allergen
                                    # (e.g. Drug="Amoxicillin", allergen_keyword="penicillin")
  # MVP-honest note: this is a keyword-based safety net, not a clinical
  # allergy ontology. Document this limitation explicitly, don't oversell it.

Prescription
  - patient       FK(patients.Patient)
  - encounter       FK(encounters.Encounter, null=True)
  - prescribed_by     FK(User)
  - drug                 FK(Drug)
  - dose                   CharField
  - route                    CharField (oral/IV/IM/topical/etc.)
  - frequency                  CharField
  - duration_days                IntegerField null=True
  - status                          CharField choices: prescribed/approved/
                                      dispensed/cancelled
  - safety_override_reason            TextField, blank=True   # if a clinician
                                      overrides an alert, they must state why —
                                      logged, never silently bypassed
  - created_at (history via django-simple-history)

DispensingRecord
  - prescription  OneToOneField(Prescription)
  - dispensed_by    FK(User)
  - dispensed_at
  - quantity_dispensed  CharField
  - stock_note            CharField, blank=True   # "stock availability indicator" §8.1.11, MVP = free-text/simple flag, not a full inventory system (that's Engineer E's stretch scope if time allows)
```

## 2. Medication safety checks (the highest-value patient-safety feature in the whole system — build this properly)

Implement `pharmacy/safety.py`:

```python
def check_prescription_safety(patient, drug, dose=None) -> list[SafetyWarning]
```

Checks performed, each returning a structured `SafetyWarning(level, message)`:
1. **Allergy check** — cross-reference `encounters.services.get_patient_allergies(patient)` against `DrugAllergyMap` keyword matches. Level: `critical`.
2. **Duplicate therapy** — an active (`status in [prescribed, approved, dispensed]`) prescription for the same `drug` or same `generic_name` in the last N days. Level: `warning`.
3. **Pregnancy/renal contraindication concept** — if `Patient` has a known pregnancy status (from latest `VitalSignSet.pregnancy_status`, call `vitals.services`) or a flagged renal condition (MVP: a simple boolean/diagnosis-text check against recent `Encounter.diagnosis`), and the drug is contraindicated, warn. Level: `warning`. Document clearly that this is a **concept-level check**, not a real renal-dose-calculator — the brief itself calls these "warning concepts," don't overbuild or overclaim clinical accuracy here.
4. **Pediatric dosing safeguard** — if patient age (computed from `date_of_birth`) is under 12 and `dose` numeric value (parsed conservatively) exceeds `pediatric_max_dose_mg`, warn. Level: `critical`.

**Alert fatigue control** (§9.2 explicitly requires this): warnings are prioritized — only `critical` warnings block submission by default; `warning`-level items are shown but can be acknowledged and proceeded past with a single click, logged in `safety_override_reason`. Don't make every warning a hard stop — that's the alert-fatigue failure mode the brief is warning you against, and it's also a real named judging consideration.

## 3. Public interface other engineers use

```python
def prescribe(patient, drug, prescribed_by, data) -> tuple[Prescription, list[SafetyWarning]]
def approve(prescription, approved_by) -> Prescription
def dispense(prescription, dispensed_by, data) -> DispensingRecord
def active_prescriptions_for(patient) -> QuerySet[Prescription]
```

## 4. Views/pages

- `/pharmacy/patient/<id>/prescribe/` — prescribing form; on submit, safety checks run and render inline before allowing final confirm (HTMX: submit → server runs checks → returns either success or a warnings panel with "acknowledge and proceed" / "cancel").
- `/pharmacy/queue/` — pending prescriptions queue for pharmacist approval/dispensing.
- `/pharmacy/prescription/<id>/dispense/` — dispensing action.
- `/pharmacy/dashboard/` — workload widget (pending vs dispensed counts).
- Patient-profile "Medications" tab.

## 5. Acceptance criteria

- [ ] Prescribing a drug the patient has a recorded allergy to blocks submission with a critical warning, requires override + reason to proceed, and the override is logged.
- [ ] Prescribing a duplicate active therapy shows a warning that can be acknowledged and proceeded past.
- [ ] Pediatric dose safeguard fires correctly for a seeded under-12 patient and an over-limit dose.
- [ ] Dispensing changes status and is auditable (who dispensed, when, what quantity).
- [ ] `check_prescription_safety()` has direct unit tests independent of the view layer (pure function, easy to test exhaustively — do this).
