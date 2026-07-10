# Outpatient Encounter Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Open patient profile] --> B[Start encounter]
    B --> C[Document complaint and history]
    C --> D[Record exam and diagnosis]
    D --> E[Add plan, orders, and prescriptions]
    E --> F[Save encounter and schedule follow-up]
```

Implemented in:
- `encounters`
- `templates/encounters/*`
