# Inpatient Admission and Ward Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Initiate admission] --> B[Assign ward / bed]
    B --> C[Record ward round note]
    C --> D[Nursing care / MAR / fluids]
    D --> E[Procedure or transfer]
    E --> F[Discharge planning]
    F --> G[Discharge summary / death documentation]
```

Implemented in:
- `inpatient`
- `inpatient/templates/inpatient/*`
