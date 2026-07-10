# Laboratory Ordering and Result Review

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Place lab order] --> B[Collect sample]
    B --> C[Process test]
    C --> D[Record result]
    D --> E{Critical / abnormal?}
    E -- Yes --> F[Alert clinician]
    E -- No --> G[Make result available]
    F --> G
```

Implemented in:
- `laboratory`
- `templates/laboratory/*`
