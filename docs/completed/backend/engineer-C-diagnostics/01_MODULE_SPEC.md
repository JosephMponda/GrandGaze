# Engineer C - Module Spec: Laboratory & Imaging (Diagnostics)

**Django apps owned:** `laboratory`, `imaging`.

**Depends on (frozen by end of Day 2/3):** `patients.Patient`, `encounters.Encounter` (order originates from an encounter), `accounts` RBAC.

**Brief traceability:** §8.1.10 (Laboratory Information Management), §8.2.1 (Imaging - future module, lightweight MVP stub), §9.2 (critical result alerts), §12 MVP ("laboratory order and result entry", "medical imaging request and report concept").

## 1. Data model

### `laboratory` app

```
LabTest  # catalog, seed ~20 common tests
  - name              CharField (e.g. "Full Blood Count", "Malaria RDT", "Creatinine")
  - loinc_code          CharField, blank=True   # §8.1.10 future LOINC mapping - populate where known, leave blank otherwise, never fake a code
  - specimen_type          CharField (blood/urine/stool/swab/other)
  - normal_range_low        DecimalField null=True
  - normal_range_high         DecimalField null=True
  - unit                        CharField, blank=True
  - is_critical_if_outside_range  BooleanField default=False

LabOrder
  - patient        FK(patients.Patient)
  - encounter        FK(encounters.Encounter, null=True)
  - ordered_by          FK(User)
  - test                  FK(LabTest)
  - status                  CharField choices: ordered/specimen_collected/
                              in_progress/resulted/verified/cancelled
  - specimen_barcode          CharField, blank=True   # "barcode-ready" per §8.1.10, MVP = generated string + rendered as a barcode image, no scanner hardware integration needed
  - collected_at                DateTimeField null=True
  - collected_by                  FK(User, null=True, related_name="+")
  - created_at (history via django-simple-history)

LabResult
  - order  OneToOneField(LabOrder)
  - value_numeric      DecimalField null=True
  - value_text            CharField, blank=True   # for qualitative results e.g. "Positive"/"Negative"
  - is_abnormal              BooleanField default=False, auto-set on save against LabTest range
  - is_critical                BooleanField default=False, auto-set against is_critical_if_outside_range
  - entered_by                    FK(User)
  - verified_by                     FK(User, null=True)   # result approval workflow §8.1.10
  - verified_at
  - notes                             TextField, blank=True
```

### `imaging` app

```
ImagingModality  # catalog: X-ray, Ultrasound, CT, MRI, Echocardiography - seed all, MVP fully supports X-ray/Ultrasound only

ImagingRequest
  - patient          FK(patients.Patient)
  - encounter          FK(encounters.Encounter, null=True)
  - requested_by          FK(User)
  - modality                FK(ImagingModality)
  - clinical_indication      TextField
  - pregnancy_status_checked   BooleanField default=False   # safety checklist item §8.2.1
  - status                       CharField choices: requested/scheduled/
                                    completed/reported
  - scheduled_at

ImagingReport
  - request  OneToOneField(ImagingRequest)
  - findings   TextField
  - impression  TextField
  - is_critical_finding  BooleanField default=False
  - reported_by  FK(User)
  - reported_at
  - image_reference  CharField, blank=True   # "image-link concept" per brief - a filename/URL placeholder, MVP does not implement real PACS storage
```

## 2. Critical result alerting (patient safety - real feature, judged)

On `LabResult.save()`, if `is_critical` is set, call `reporting.services.raise_alert(patient, severity="critical", source="lab", message=...)` (same alerting entry point Engineer B uses - one alert system, not two). Same pattern for `ImagingReport.is_critical_finding`. This is the §9.2 "critical laboratory result alerts" / "critical imaging result alerts" requirement - build it for real, it's an easy, high-visibility demo moment.

## 3. Public interface other engineers use

`laboratory/services.py`:
```python
def create_order(patient, test, ordered_by, encounter=None) -> LabOrder
def enter_result(order, data, entered_by) -> LabResult
def pending_orders_for(patient) -> QuerySet[LabOrder]
def recent_results_for(patient, limit=10) -> QuerySet[LabResult]
```

`imaging/services.py`: mirrors the same shape (`create_request`, `enter_report`, `pending_requests_for`).

## 4. Views/pages

- `/labs/patient/<id>/order/` - order form (test picker from `LabTest` catalog).
- `/labs/order/<id>/collect/` - mark specimen collected, renders barcode.
- `/labs/order/<id>/result/` - result entry, auto-flags abnormal/critical on save; separate "verify" action for a second user (result approval workflow - don't let the same user who entered the result also verify it, that's a real governance control, enforce it in the view not just by convention).
- `/labs/workload/` - lab workload dashboard: pending vs resulted counts, turnaround time (time from `created_at` to `resulted`), per §8.1.10 "workload dashboard and turnaround time tracking."
- `/imaging/patient/<id>/request/` - imaging request form with the pregnancy-status safety checkbox required before submission for applicable modalities.
- `/imaging/request/<id>/report/` - report entry.
- Patient-profile "Labs" and "Imaging" tabs (HTMX partials into Engineer A's template blocks).

## 5. Acceptance criteria

- [ ] A clinician can order a lab test from an encounter; it appears as "pending" on the patient profile and the lab workload dashboard.
- [ ] Entering a result outside the normal range auto-flags `is_abnormal`; outside a critical-flagged test's range auto-flags `is_critical` and fires an alert.
- [ ] Result verification requires a different user than the one who entered the result.
- [ ] Imaging request blocks submission if the pregnancy-status checklist item is required and unchecked, for modalities where that applies.
- [ ] Lab workload dashboard shows a real turnaround-time number computed from seed data, not a placeholder.
- [ ] Barcode renders for a collected specimen (visual only - no scanner integration required for MVP).
