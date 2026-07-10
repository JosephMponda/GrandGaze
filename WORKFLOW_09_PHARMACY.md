# Pharmacy Prescribing and Dispensing Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

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
