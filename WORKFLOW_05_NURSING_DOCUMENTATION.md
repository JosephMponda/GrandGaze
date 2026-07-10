# Nursing Documentation Flow

![MUST logo](static/img/must-logo.png) ![GSL logo](static/img/logos/GSL-Official-Logo.png)

Grand Gaze

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
