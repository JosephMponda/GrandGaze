# Pharmacy Prescribing and Dispensing Flow

![MUST logo](static/img/must-logo.png) ![GSL logo](static/img/logos/GSL-Official-Logo.png)

Grand Gaze

```mermaid
flowchart TD
    A[Create prescription] --> B[Run safety checks]
    B --> C{Issue found?}
    C -- Yes --> D[Resolve / review]
    C -- No --> E[Queue for dispensing]
    D --> E
    E --> F[Dispense medication]
```

Implemented in:
- `pharmacy`
- `templates/pharmacy/*`
