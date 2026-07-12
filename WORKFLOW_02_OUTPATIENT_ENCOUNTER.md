# Outpatient Encounter Flow

![MUST logo](static/img/must-logo.png) ![GSL logo](static/img/logos/GSL-Official-Logo.png)

Grand Gaze

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
