# Billing and Invoice Flow

![MUST logo](static/img/must-logo.png) ![GSL logo](static/img/logos/GSL-Official-Logo.png)

Grand Gaze

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
