# Dialysis Session Recording Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Open dialysis dashboard] --> B[Select active prescription]
    B --> C[Record session]
    C --> D[Capture access and completion]
    D --> E[Update counts and status]
```

Implemented in:
- `dialysis`
- `dialysis/templates/dialysis/*`
