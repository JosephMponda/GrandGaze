# Vital Signs and Abnormal Alerts

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

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
