# Patient Registration and MPI

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Open registration] --> B[Capture demographics and identifiers]
    B --> C[Capture contacts and consent]
    C --> D{Duplicate detected?}
    D -- Yes --> E[Review / merge record]
    D -- No --> F[Create master patient record]
    E --> G[Open patient profile]
    F --> G
```

Implemented in:
- `patients`
- `templates/patients/register.html`
- `templates/patients/profile.html`
