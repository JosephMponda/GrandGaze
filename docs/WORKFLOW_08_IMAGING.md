# Imaging Request and Report Flow

![MUST logo](static/img/must-logo.png) ![GSL logo](static/img/logos/GSL-Official-Logo.png)

Grand Gaze

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
