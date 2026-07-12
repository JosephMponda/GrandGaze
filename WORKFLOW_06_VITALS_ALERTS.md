# Vital Signs and Abnormal Alerts

![MUST logo](static/img/must-logo.png) ![GSL logo](static/img/logos/GSL-Official-Logo.png)

Grand Gaze

```mermaid
flowchart TD
    A[Capture observation] --> B[Store vital sign]
    B --> C[Evaluate thresholds]
    C --> D{Abnormal?}
    D -- Yes --> E[Create alert]
    D -- No --> F[Update trends]
    E --> F
    F --> G[Surface in dashboard / profile]
```

Implemented in:
- `vitals`
- `reporting`
- `templates/vitals/*`
- `templates/reporting/*`
