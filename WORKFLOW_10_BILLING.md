# Billing and Invoice Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Generate invoice] --> B[Track payment status]
    B --> C{Paid?}
    C -- Yes --> D[Close invoice]
    C -- No --> E[Show outstanding balance]
    E --> F[Follow-up / receipt]
```

Implemented in:
- `billing`
- `templates/billing/*`
