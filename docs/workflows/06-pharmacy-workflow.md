# Workflow 11.6 — Pharmacy Workflow

```mermaid
flowchart TD
    A([Prescription Submitted]) --> B[Pharmacy Queue]
    B --> C[Verify Prescription]
    C --> D{Complete & Legible?}
    D -->|No| E[Flag for Clarification]
    E --> F[Contact Prescriber]
    F --> G[Clarified]
    G --> C
    D -->|Yes| H[Allergy Check]
    H --> I{Allergy on Record?}
    I -->|Yes & Conflict| J[Flag Interaction]
    J --> K[Contact Prescriber]
    K --> L[Alternative / Documented Reason]
    L --> M[Clinical Check]
    I -->|No| M
    M --> N{Stock Available?}
    N -->|No| O[Mark Out of Stock]
    O --> P[Advise Patient / Order Stock]
    N -->|Yes| Q[Dispense Medication]
    Q --> R[Label & Package]
    R --> S[Counsel Patient]
    S --> T[Record Dispensing]
    T --> U[Update Stock Level]
    U --> V[Patient Receives Medication]
```