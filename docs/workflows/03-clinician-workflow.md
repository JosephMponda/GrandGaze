# Workflow 11.3 — Clinician Workflow

```mermaid
flowchart TD
    A([Patient context]) --> B[Review triage, vitals, labs, imaging, alerts]
    B --> C[History and physical exam]
    C --> D[Assessment and differential]
    D --> E{Investigations needed?}
    E -->|Lab| F[Create lab order]
    E -->|Imaging| G[Create imaging request]
    E -->|Both| H[Create lab and imaging orders]
    E -->|None| I[Proceed to diagnosis]
    F --> J[Review results]
    G --> J
    H --> J
    J --> I
    I --> K[Treatment plan]
    K --> L{Medication required?}
    L -->|Yes| M[Prescribe with pharmacy safety checks]
    L -->|No| N[Document plan only]
    M --> N
    N --> O{Disposition}
    O -->|Discharge| P[Discharge summary + follow-up]
    O -->|Admit| Q[Admission order + ward handover]
    O -->|Refer| R[Referral record]
    O -->|Death| S[Death documentation]
```
