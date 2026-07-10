# Imaging Request and Report Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Request imaging] --> B[Assign modality / worklist]
    B --> C[Perform study]
    C --> D[Create report]
    D --> E[Review result]
    E --> F[Close request]
```

Implemented in:
- `imaging`
- `templates/imaging/*`
