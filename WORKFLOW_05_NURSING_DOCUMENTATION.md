# Nursing Documentation Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Open nursing form] --> B[Record assessment]
    B --> C[Capture problems and care plan]
    C --> D[Record progress notes]
    D --> E{Abnormal finding?}
    E -- Yes --> F[Escalate to clinician]
    E -- No --> G[Continue care]
```

Implemented in:
- `inpatient`
- `templates/inpatient/nursing_assessment_*`
