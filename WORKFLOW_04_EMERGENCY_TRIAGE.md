# Emergency and Triage Flow

<p align="left">
  <img src="static/img/must-logo.png" alt="MUST logo" width="72">
  <img src="static/img/logos/GSL-Official-Logo.png" alt="GSL logo" width="72">
</p>

```mermaid
flowchart TD
    A[Rapid register unstable patient] --> B[Record triage category]
    B --> C[Capture vital signs and emergency notes]
    C --> D{Needs escalation?}
    D -- Yes --> E[Refer to ward / lab / imaging / theatre]
    D -- No --> F[Discharge or observe]
```

Implemented in:
- `emergency`
- `emergency/templates/emergency/*`
